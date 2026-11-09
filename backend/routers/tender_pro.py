"""v45 — Tender Pro: DPR-driven auto-generation, AI-fill-all, masters, filters.

Adds four capability bundles on top of tender_templates:
  Phase C — DPR upload → structured extract → prefilled draft
            + one-shot AI fill-all across every section
  Phase A — Auto tender-reference generator (COUNTRY-IND-KIND-YY-SEQ)
            per-section save endpoint
  Phase B — EMD/fee master (country + industry + slabs)
            "Save as master" promotion of a draft
  Phase D — Vendor rating criteria master + multi-rater aggregate scoring
"""
import secrets
import base64
import re
import os
from typing import List, Optional, Literal
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from pydantic import BaseModel, Field
from bson import ObjectId

from db import db, next_sequence
from models.base import BaseDocument, now_iso
from security import require_role
from audit import audit_log
from routers._fees import assert_fees_paid, assert_start_allowed, country_q, get_fee_type, validate_rule_against_type
from routers._tender_access import (
    tender_principal, write_principal, is_vendor, actor as _actor,
    assert_can_edit_doc,
)

router = APIRouter(prefix="/api/v1/tender-pro", tags=["tender-pro"])


async def _vendor_scope_template(principal: dict, doc: dict) -> None:
    """A vendor may only mutate their OWN non-master draft template, and not once
    it has been submitted/approved. Delegates to the shared edit guard so the
    lock is enforced identically across every write path."""
    assert_can_edit_doc(principal, doc)


def _out(doc: dict) -> dict:
    return BaseDocument.out(doc)


# =============================================================================
# PHASE C — DPR upload + AI fill-all
# =============================================================================

class DprAnalyzeJsonIn(BaseModel):
    filename: str
    content_b64: str  # base64-encoded file bytes


class DprAnalyzeResult(BaseModel):
    header: dict
    section_bodies: dict  # {section_code: html_body}
    warnings: List[str]


def _extract_text_from_upload(name: str, body: bytes) -> str:
    """Best-effort text extraction. PDF via pypdf, DOCX via python-docx.
    Falls back to raw utf-8 decode for txt."""
    name_lower = (name or "").lower()
    if name_lower.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            from io import BytesIO
            reader = PdfReader(BytesIO(body))
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"PDF parse failed: {type(e).__name__}")
    if name_lower.endswith(".docx"):
        try:
            from docx import Document as _Doc
            from io import BytesIO
            d = _Doc(BytesIO(body))
            return "\n".join(p.text for p in d.paragraphs)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"DOCX parse failed: {type(e).__name__}")
    try:
        return body.decode("utf-8", errors="ignore")
    except Exception:
        raise HTTPException(status_code=400, detail="Unsupported file type — upload PDF, DOCX or TXT")


def _parse_json_loose(raw: str) -> dict:
    """Strip code fences and parse. Raise 502 on failure."""
    import json as _json
    s = str(raw).strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?", "", s).rstrip("`").strip()
    try:
        return _json.loads(s)
    except Exception:
        raise HTTPException(status_code=502, detail="LLM returned invalid JSON — retry")


def _chunk_for_section(full_text: str, section: dict, fallback_slice: tuple) -> str:
    """Find the passage of the DPR most relevant to a discovered section.
    Searches for the section title (and the first significant word of the
    title) inside the extracted text; returns ±3500 chars around the first
    hit. Falls back to the given evenly-split slice when no hit."""
    title = (section.get("title") or "").strip()
    if title:
        low = full_text.lower()
        idx = low.find(title.lower())
        if idx < 0:
            # Try first significant word of the title
            for w in re.findall(r"[A-Za-z]{5,}", title):
                idx = low.find(w.lower())
                if idx >= 0:
                    break
        if idx >= 0:
            start = max(0, idx - 500)
            end = min(len(full_text), idx + 3500)
            return full_text[start:end]
    s, e = fallback_slice
    return full_text[max(0, s):max(0, e)]


async def _run_dpr_analyze(name: str, body_bytes: bytes, kind: str, admin: dict,
                            template: Optional[dict] = None,
                            progress_cb=None) -> dict:
    """Shared DPR pipeline used by both the multipart and JSON endpoints.

    Two modes:
      * Template-aware (a master was picked)  — single LLM call, expanded
        excerpt (60k chars) so long DPRs still get proper coverage.
      * Multi-pass deep-dive (no master)      — Pass 1 discovers a full
        header + a DYNAMIC list of chapters/sections from the whole
        document (head + tail excerpt); Pass 2 drafts each section body
        in parallel from its relevant chunk of the DPR. Yields dozens of
        real sections instead of the previous 5 generic ones.

    v46l — optional ``progress_cb`` is called as
        ``await progress_cb(pct: int, phase: str)`` at every material
        milestone (extract → map → reduce → draft → done). Used by the
        async endpoint to write progress into the ``dpr_jobs`` collection
        so the frontend can render a real progress bar for 500+ page PDFs.
    """
    async def _cb(pct: int, phase: str):
        if progress_cb is not None:
            try:
                await progress_cb(pct, phase)
            except Exception:
                pass

    await _cb(0, "reading upload")
    if len(body_bytes) > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="DPR exceeds 100 MB limit")
    text = _extract_text_from_upload(name, body_bytes)
    if len(text.strip()) < 60:
        raise HTTPException(status_code=422, detail="Could not read any text from this DPR. It looks like a scanned/image-only PDF — upload a text-based PDF, DOCX or TXT.")

    total = len(text)
    warnings: list = []
    await _cb(10, f"extracted {total:,} chars")

    # -------------------- Template-aware fast path --------------------
    if template:
        excerpt = text[:60000]
        if total > len(excerpt):
            warnings.append(f"Document is {total:,} chars — analysed the first {len(excerpt):,}")
        header_keys = list((template.get("header") or {}).keys())
        sec_spec = [{"code": s.get("code"), "title": s.get("title"),
                     "hint": (s.get("hint") or "")[:120]}
                    for s in (template.get("sections") or [])]
        system_msg = (
            "You are a public-procurement copilot. Given a Detailed Project Report (DPR) excerpt, "
            f"produce a JSON object suitable for a {kind.upper()} pack with EXACTLY these keys. {kind_style(kind)} Keys: "
            f"{{\"header\": an object with EXACTLY these keys from the chosen template: {header_keys}. "
            f"\"section_bodies\": an object keyed by the EXACT section codes of the chosen template: "
            f"{[s['code'] for s in sec_spec]}. For each code, draft body text that matches its "
            f"title and hint: {sec_spec}. "
            "\"warnings\": [fields you could not confidently extract]}. "
            "section_bodies values MUST be HTML using only <p><br><b><i><ul><ol><li>. "
            "Do NOT invent section codes or header keys beyond the list given. "
            "Return valid JSON only — no prose, no code fences."
        )
        resp = await _llm_complete(system_msg, f"DPR excerpt:\n{excerpt}")
        parsed = _parse_json_loose(resp)
        parsed.setdefault("header", {})
        parsed.setdefault("section_bodies", {})
        parsed.setdefault("warnings", [])
        parsed["warnings"] = warnings + list(parsed.get("warnings") or [])
        parsed["meta"] = {"chars_total": total, "chars_analysed": len(excerpt),
                          "sections_out": len(parsed.get("section_bodies") or {}),
                          "template_aware": True, "passes": 1}
        await audit_log("tender_pro.dpr_analyze", admin, "dpr", name, parsed["meta"])
        return parsed

    # -------------------- Multi-pass deep-dive (no template) --------------------
    # v46j — TRUE MAP-REDUCE. No character ceiling; the ENTIRE extracted
    # document is fed to the LLM in overlapping chunks. Pass 1a summarises
    # each chunk; Pass 1b reduces those summaries into a global blueprint;
    # Pass 2 drafts each section body from the passage most relevant to
    # that section title. If a section body call fails, we ALWAYS fall
    # back to a rich HTML block built from the raw source passage — never
    # a 1-line stub or empty string.
    import asyncio

    CHUNK = 40000        # ~10-12 pages of extracted PDF text per LLM call
    OVERLAP = 3000       # keep context continuity across chunk boundaries
    # v46l — CAP LIFTED. The old 20-chunk / 800 KB ceiling truncated large
    # tenders. Now we ingest the entire extracted text (500-chunk safety net
    # ≈ 20 MB / 5 000 pages), still bounded by the LLM semaphore so we don't
    # melt the proxy. Callers that need ultra-large ingestion (100 MB PDFs)
    # should use /dpr/analyze-async so the request doesn't time out.
    MAX_CHUNKS = int(os.environ.get("DPR_MAX_CHUNKS", "500"))

    chunks: list[tuple[int, str]] = []  # (offset, text)
    if total <= CHUNK:
        chunks.append((0, text))
    else:
        i = 0
        while i < total and len(chunks) < MAX_CHUNKS:
            chunks.append((i, text[i:i + CHUNK]))
            if i + CHUNK >= total:
                break
            i += CHUNK - OVERLAP
        # v51j — the "Document is X chars — deep-dive analysed…" technical note
        # was appended to `warnings` and displayed to admins as if it were an
        # unextracted field on every large DPR. Removed from the UI list; the
        # generation event itself remains on the audit ledger.

    # ---- Pass 1a: per-chunk local blueprints (in parallel, bounded) ----
    await _cb(15, f"mapping {len(chunks)} chunks")
    sem1 = asyncio.Semaphore(4)
    done_map = {"n": 0}
    async def _local_bp(idx: int, offset: int, ctext: str) -> dict:
        sys_local = (
            "You are analysing ONE chunk of a Detailed Project Report (DPR). "
            "Return JSON: {\"header_hints\": {work_title, work_description, tender_value, "
            "budget_currency, period_days, location, product_category, sub_category, "
            "contract_type, eligibility, evaluation_method, bid_validity_days, emd_amount, "
            "emd_type, emd_percentage, tender_fee_amount — fill only fields visible in THIS chunk}, "
            "\"sections\": [{\"title\": \"…\", \"hint\": \"one-line description\", "
            "\"anchor_phrase\": \"6-12 word verbatim phrase from this chunk that appears in the section body\"}, …]}. "
            "List every major chapter/schedule/annexure/form found in this chunk (0 if none). "
            "Return valid JSON only — no prose."
        )
        try:
            async with sem1:
                raw = await _llm_complete(sys_local, f"Chunk {idx+1} of {len(chunks)} (starts at char {offset:,}):\n{ctext}")
            out = _parse_json_loose(raw)
        except Exception:
            out = {"header_hints": {}, "sections": []}
        done_map["n"] += 1
        pct = 15 + int(45 * done_map["n"] / max(1, len(chunks)))
        await _cb(pct, f"mapped {done_map['n']}/{len(chunks)} chunks")
        return out

    local_bps = await asyncio.gather(*[_local_bp(i, off, c) for i, (off, c) in enumerate(chunks)])

    # ---- Pass 1b: reduce local blueprints into ONE global header + section list ----
    merged_header: dict = {}
    for lb in local_bps:
        for k, v in (lb.get("header_hints") or {}).items():
            if v and not merged_header.get(k):
                merged_header[k] = v

    # Deduplicate + globally-order the discovered sections.
    seen_titles: set[str] = set()
    global_sections: list[dict] = []
    for lb in local_bps:
        for s in (lb.get("sections") or []):
            key = (s.get("title") or "").strip().lower()
            if key and key not in seen_titles:
                seen_titles.add(key)
                global_sections.append({
                    "title": s.get("title"),
                    "hint": s.get("hint") or "",
                    "anchor_phrase": s.get("anchor_phrase") or "",
                })

    if not global_sections:
        global_sections = [
            {"title": "Project Overview",           "hint": "Executive summary from the DPR",       "anchor_phrase": ""},
            {"title": "Scope of Work",              "hint": "Detailed scope, deliverables",         "anchor_phrase": ""},
            {"title": "Financial Summary",          "hint": "Budget, EMD, currency, fee",           "anchor_phrase": ""},
            {"title": "Schedule & Milestones",      "hint": "Timeline & milestones",                "anchor_phrase": ""},
            {"title": "Eligibility & Evaluation",   "hint": "Bidder eligibility, evaluation method","anchor_phrase": ""},
        ]
        warnings.append("Chunk pass returned no sections — used generic 5-section fallback")

    discovered = global_sections[:60]
    for i, s in enumerate(discovered):
        s["code"] = f"dpr-{i+1}"
        s["kind"] = "section"
        s["order"] = (i + 1) * 10

    header = merged_header
    await _cb(65, f"drafting {len(discovered)} sections")

    # ---- Pass 2: parallel section-body drafting from BEST passage ----
    n = len(discovered)
    slice_len = max(6000, total // max(1, n))

    def _best_chunk(sec: dict, i: int) -> str:
        # Prefer the LLM-provided anchor phrase (more accurate than title match).
        for probe in (sec.get("anchor_phrase") or "", sec.get("title") or ""):
            probe = (probe or "").strip()
            if not probe:
                continue
            low = text.lower()
            idx = low.find(probe.lower())
            if idx < 0:
                # try first significant token from the probe
                for w in re.findall(r"[A-Za-z]{5,}", probe):
                    idx = low.find(w.lower())
                    if idx >= 0:
                        break
            if idx >= 0:
                start = max(0, idx - 800)
                end = min(len(text), idx + 5500)
                return text[start:end]
        # Even fallback slice — spreads across whole document.
        s = i * slice_len
        return text[max(0, s):min(total, s + slice_len + 500)]

    sem2 = asyncio.Semaphore(6)
    done_draft = {"n": 0}
    async def _draft_body(i: int, sec: dict) -> tuple[str, str]:
        passage = _best_chunk(sec, i)
        prompt = (
            f"You are a public-procurement drafting copilot. Draft the BODY of ONE {kind_label(kind)} "
            f"section using ONLY the DPR passage below as source. {kind_style(kind)} Return valid HTML using only these "
            "tags: <p><br><b><i><ul><ol><li><h3>. Do NOT include the section title. Do NOT invent "
            "numbers or facts absent from the passage. Aim for 280-360 words with real details, "
            "bullets for lists, bold for key figures. If the passage is short, still produce a "
            "substantive paragraph — never a one-liner."
        )
        user = (f"Section title: {sec.get('title')}\n"
                f"Hint: {sec.get('hint') or ''}\n\n"
                f"Relevant DPR passage:\n{passage}")
        try:
            async with sem2:
                body_html = (await _llm_complete(prompt, user)).strip()
            if body_html.startswith("```"):
                body_html = re.sub(r"^```(?:html)?", "", body_html).rstrip("`").strip()
            # Reject stubs — anything under 200 chars is treated as failure
            # so the raw-passage fallback kicks in.
            if len(re.sub(r"<[^>]+>", "", body_html)) < 200:
                raise ValueError("stub")
            out = (sec["code"], body_html)
        except Exception:
            # Fallback — never return an empty body. Wrap the raw passage
            # as safely-escaped paragraphs so the section at least contains
            # the source material.
            import html as _html
            paras = [p.strip() for p in re.split(r"\n{2,}", passage) if p.strip()]
            paras = paras[:8] or [passage.strip()]
            body_html = "\n".join(f"<p>{_html.escape(p[:1200])}</p>" for p in paras)
            out = (sec["code"], body_html)
        done_draft["n"] += 1
        pct = 65 + int(30 * done_draft["n"] / max(1, len(discovered)))
        await _cb(pct, f"drafted {done_draft['n']}/{len(discovered)} sections")
        return out

    results = await asyncio.gather(*[_draft_body(i, s) for i, s in enumerate(discovered)])
    section_bodies = {code: body for code, body in results if body}
    await _cb(98, "finalising")

    parsed = {
        "header": header,
        "section_bodies": section_bodies,
        "warnings": warnings,
        "sections_blueprint": discovered,
        "meta": {
            "chars_total": total,
            "chars_analysed": sum(len(c) for _, c in chunks),
            "chunks": len(chunks),
            "sections_discovered": n,
            "sections_drafted": len(section_bodies),
            "template_aware": False,
            "passes": 3,
        },
    }
    await audit_log("tender_pro.dpr_analyze", admin, "dpr", name, parsed["meta"])
    return parsed


async def _load_template_opt(template_id: Optional[str]) -> Optional[dict]:
    if not template_id:
        return None
    try:
        return await db.tender_templates.find_one({"_id": ObjectId(template_id)})
    except Exception:
        return None


@router.post("/dpr/analyze")
async def analyze_dpr(file: UploadFile = File(...),
                       kind: str = Query("tender", regex="^(tender|rfp|rfq)$"),
                       template_id: Optional[str] = Query(None),
                       principal=Depends(write_principal)):
    """Multipart DPR upload. Prefer /dpr/analyze-json on AWS deployments
    behind a WAF that blocks binary POST bodies."""
    body_bytes = await file.read()
    template = await _load_template_opt(template_id)
    if template:
        await _vendor_scope_template(principal, template)
        await assert_fees_paid(principal, template, "work")
    else:
        await assert_start_allowed(principal)
    return await _run_dpr_analyze(file.filename, body_bytes, kind, _actor(principal), template)


@router.post("/dpr/analyze-json")
async def analyze_dpr_json(payload: DprAnalyzeJsonIn,
                            kind: str = Query("tender", regex="^(tender|rfp|rfq)$"),
                            template_id: Optional[str] = Query(None),
                            principal=Depends(write_principal)):
    """v45c — WAF-safe DPR upload. Frontend base64-encodes the file and
    posts it as JSON so AWS WAF managed rules (which block binary bodies)
    let it through. Payload cap enforced BEFORE base64 decode.
    """
    # v46l — cap lifted from 22 MB to 140 MB (≈ 100 MB decoded). For files
    # anywhere close to this ceiling the client should use
    # /dpr/analyze-async instead, since a synchronous request will exceed
    # nginx/EB idle timeouts even with map-reduce.
    if len(payload.content_b64) > 140 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="DPR exceeds 100 MB limit")
    try:
        body_bytes = base64.b64decode(payload.content_b64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="content_b64 is not valid base64")
    template = await _load_template_opt(template_id)
    if template:
        await _vendor_scope_template(principal, template)
        await assert_fees_paid(principal, template, "work")
    else:
        await assert_start_allowed(principal)
    return await _run_dpr_analyze(payload.filename, body_bytes, kind, _actor(principal), template)


# =============================================================================
# v46l — Async DPR pipeline. Massive PDFs (100 MB / 500+ pages) cannot be
# processed inside a single HTTP request without hitting the nginx idle
# timeout on Elastic Beanstalk. This endpoint accepts the base64 payload,
# stores a job record, and returns a job_id immediately; the map-reduce
# runs in the background and writes progress to Mongo. The frontend polls
# /dpr/jobs/{job_id} and renders a progress bar.
# =============================================================================

async def _dpr_job_worker(job_id: ObjectId, filename: str, body_bytes: bytes,
                           kind: str, admin: dict, template: Optional[dict]):
    from datetime import timedelta
    async def cb(pct: int, phase: str):
        await db.dpr_jobs.update_one(
            {"_id": job_id},
            {"$set": {"progress": int(pct), "phase": phase, "status": "running",
                       "updated_at": now_iso()}},
        )
    try:
        result = await _run_dpr_analyze(filename, body_bytes, kind, admin, template,
                                        progress_cb=cb)
        await db.dpr_jobs.update_one(
            {"_id": job_id},
            {"$set": {"status": "done", "progress": 100, "phase": "complete",
                       "result": result, "updated_at": now_iso(),
                       "expire_at": (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()}},
        )
    except HTTPException as e:
        await db.dpr_jobs.update_one(
            {"_id": job_id},
            {"$set": {"status": "failed", "error": str(e.detail),
                       "updated_at": now_iso()}},
        )
    except Exception as e:  # pragma: no cover — safety net
        await db.dpr_jobs.update_one(
            {"_id": job_id},
            {"$set": {"status": "failed",
                       "error": f"{type(e).__name__}: {str(e)[:400]}",
                       "updated_at": now_iso()}},
        )


@router.post("/dpr/analyze-async")
async def analyze_dpr_async(payload: DprAnalyzeJsonIn,
                             kind: str = Query("tender", regex="^(tender|rfp|rfq)$"),
                             template_id: Optional[str] = Query(None),
                             principal=Depends(write_principal)):
    """Kick off a background DPR analysis and return a job_id. Use this
    for very large DPRs (10 MB+ / 500+ pages) so the HTTP request doesn't
    time out. Poll /dpr/jobs/{job_id} for progress + result.
    """
    import asyncio
    if len(payload.content_b64) > 140 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="DPR exceeds 100 MB limit")
    try:
        body_bytes = base64.b64decode(payload.content_b64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="content_b64 is not valid base64")
    template = await _load_template_opt(template_id)
    if template:
        await _vendor_scope_template(principal, template)
        await assert_fees_paid(principal, template, "work")
    else:
        await assert_start_allowed(principal)
    now = now_iso()
    job_doc = {
        "filename": payload.filename,
        "kind": kind,
        "status": "queued",
        "progress": 0,
        "phase": "queued",
        "result": None,
        "error": None,
        "size_bytes": len(body_bytes),
        "admin_email": (principal or {}).get("email"),
        "owner_id": principal["id"],
        "owner_kind": principal.get("kind"),
        "created_at": now,
        "updated_at": now,
    }
    r = await db.dpr_jobs.insert_one(job_doc)
    asyncio.create_task(_dpr_job_worker(r.inserted_id, payload.filename, body_bytes,
                                          kind, _actor(principal), template))
    return {"job_id": str(r.inserted_id), "status": "queued", "size_bytes": len(body_bytes)}


@router.get("/dpr/jobs/{job_id}")
async def dpr_job_status(job_id: str,
                          principal=Depends(tender_principal)):
    """Poll the status of an async DPR analysis. Returns progress % and,
    once ``status == "done"``, the full analysis payload identical to what
    the synchronous /dpr/analyze-json endpoint returns."""
    try:
        oid = ObjectId(job_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid job_id")
    doc = await db.dpr_jobs.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Job not found")
    if is_vendor(principal) and doc.get("owner_id") != principal["id"]:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job_id,
        "status": doc.get("status"),
        "progress": doc.get("progress", 0),
        "phase": doc.get("phase", ""),
        "result": doc.get("result"),
        "error": doc.get("error"),
        "filename": doc.get("filename"),
        "size_bytes": doc.get("size_bytes"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }


def _llm_key() -> str:
    key = os.environ.get("EMERGENT_LLM_KEY") or os.environ.get("LLM_API_KEY") or os.environ.get("LEGACY_LLM_KEY", "")
    if not key:
        raise HTTPException(status_code=503, detail="AI copilot is not configured (missing EMERGENT_LLM_KEY)")
    return key


_KIND_LABEL = {"tender": "tender-document", "rfq": "Request for Quotation (RFQ)",
               "rfp": "Request for Proposal (RFP)"}
_KIND_STYLE = {
    "tender": ("Write in formal tender style: mandatory 'shall' obligations, eligibility, "
               "EMD/bid security, two-envelope submission and compliance-based evaluation."),
    "rfq": ("Write as a short, price-focused RFQ: precise item specifications, quantities, "
            "delivery and commercial terms, award to the lowest compliant quote. Keep it brief and "
            "tabular where possible; avoid long legal or methodology text."),
    "rfp": ("Write as an outcome-focused RFP: explain the need and objectives, invite proposers "
            "to propose their approach, methodology, team and work plan, and state the scored "
            "evaluation criteria with weights. Ask for solutions rather than prescribing them."),
}


def kind_label(kind: Optional[str]) -> str:
    return _KIND_LABEL.get((kind or "tender").lower(), _KIND_LABEL["tender"])


def kind_style(kind: Optional[str]) -> str:
    return _KIND_STYLE.get((kind or "tender").lower(), _KIND_STYLE["tender"])


async def _llm_complete(system: str, user: str) -> str:
    """Single-shot completion via Claude Sonnet 5.5 (Emergent LLM key).
    Used for DPR analysis, section drafting and Fill-All. Price data is never
    placed in these prompts (two-cover integrity)."""
    from pmc_lib.llm.chat import LlmChat, UserMessage
    key = _llm_key()
    chat = LlmChat(
        api_key=key,
        session_id=f"tenderpro-{secrets.token_hex(8)}",
        system_message=system,
    ).with_model("anthropic", "claude-sonnet-5-5")
    try:
        resp = await chat.send_message(UserMessage(text=user))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {type(e).__name__} {str(e)[:200]}")
    return resp or ""


@router.post("/dpr/analyze-legacy-multipart-removed")
async def _analyze_dpr_removed():
    """This multipart endpoint is superseded by /dpr/analyze-json which
    survives AWS WAF binary-body rules. Do not use."""
    raise HTTPException(status_code=410, detail="Use /dpr/analyze-json instead")


_FILL_WORDS = {"short": 120, "medium": 240, "long": 420}


async def _draft_section(sec: dict, header: dict, words: int, kind: Optional[str] = "tender") -> Optional[str]:
    system_msg = (
        f"You are a public-procurement drafting copilot. Draft the body of ONE {kind_label(kind)} "
        f"section based on the section title, hint and header. {kind_style(kind)} Return valid HTML using "
        "ONLY these tags: <p><br><b><i><ul><ol><li><h3>. Do not include the title. "
        f"Aim for approximately {words} words. Do not invent numbers not present in the context."
    )
    ctx = {"section_title": sec.get("title"), "section_kind": sec.get("kind"),
           "hint": sec.get("hint"),
           "header": {k: header.get(k) for k in
                      ("work_title", "budget_amount", "tender_value", "budget_currency",
                       "period_days", "product_category", "location", "eligibility",
                       "evaluation_method", "emd_amount", "sub_end", "country", "industry")
                      if header.get(k)}}
    try:
        body_html = (await _llm_complete(system_msg, f"Draft the body. Context: {ctx}")).strip()
    except HTTPException:
        return None
    if body_html.startswith("```"):
        body_html = re.sub(r"^```(?:html)?", "", body_html).rstrip("`").strip()
    return body_html or None


class AiFillAllIn(BaseModel):
    tone: Optional[str] = "formal"
    length: Optional[str] = "medium"
    only_empty: bool = True   # skip sections that already have body content


@router.post("/templates/{tid}/ai-fill-all")
async def ai_fill_all_sections(tid: str, payload: AiFillAllIn = AiFillAllIn(),
                                principal=Depends(write_principal)):
    """Draft EVERY section body in one pass. Returns the updated template
    doc so the frontend can replace state atomically. Existing bodies are
    preserved when only_empty=True (default)."""
    doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    await _vendor_scope_template(principal, doc)
    await assert_fees_paid(principal, doc, "work")
    header = doc.get("header") or {}
    updated = 0
    words = _FILL_WORDS.get(payload.length or "medium", 240)

    sections = list(doc.get("sections") or [])
    for i, sec in enumerate(sections):
        if payload.only_empty and (sec.get("body") or "").strip():
            continue
        body_html = await _draft_section(sec, header, words, doc.get("kind"))
        if body_html:
            sections[i] = {**sec, "body": body_html}
            updated += 1

    await db.tender_templates.update_one({"_id": ObjectId(tid)},
                                          {"$set": {"sections": sections,
                                                    "updated_at": now_iso()}})
    await audit_log("tender_pro.ai_fill_all", _actor(principal), "tender_template", tid,
                    {"updated_sections": updated})
    fresh = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    return {"updated": updated, "template": _out(fresh)}


async def _fill_job_set(job_id, **fields):
    await db.ai_fill_jobs.update_one({"_id": job_id},
                                     {"$set": {**fields, "updated_at": now_iso()}})


async def _fill_worker(job_id, tid: str, targets: list, header: dict, words: int, act: dict):
    done = failed = 0
    total = len(targets)
    try:
        await _fill_job_set(job_id, status="running", phase="Starting")
        for n, i in enumerate(targets):
            doc = await db.tender_templates.find_one({"_id": ObjectId(tid)}, {"sections": 1, "kind": 1})
            secs = (doc or {}).get("sections") or []
            if i >= len(secs):
                failed += 1
                continue
            sec = secs[i]
            await _fill_job_set(job_id, phase=f"Drafting section {n + 1} of {total}: {sec.get('title') or sec.get('code')}",
                                current_code=sec.get("code"))
            body = await _draft_section(sec, header, words, (doc or {}).get("kind"))
            if body:
                await db.tender_templates.update_one(
                    {"_id": ObjectId(tid), f"sections.{i}.code": sec.get("code")},
                    {"$set": {f"sections.{i}.body": body, "updated_at": now_iso()}})
                done += 1
            else:
                failed += 1
            await _fill_job_set(job_id, done=done, failed=failed,
                                progress=int(((n + 1) / total) * 100) if total else 100)
        await _fill_job_set(job_id, status="done", progress=100, phase="Complete",
                            done=done, failed=failed)
        await audit_log("tender_pro.ai_fill_all", act, "tender_template", tid,
                        {"updated_sections": done, "failed_sections": failed, "mode": "background"})
    except Exception as e:  # pragma: no cover — safety net
        await _fill_job_set(job_id, status="failed", phase="Failed",
                            error=f"{type(e).__name__}: {str(e)[:300]}", done=done, failed=failed)


_FILL_STALE_SECONDS = 300


@router.post("/templates/{tid}/ai-fill-all-async")
async def ai_fill_all_async(tid: str, payload: AiFillAllIn = AiFillAllIn(),
                            principal=Depends(write_principal)):
    """Background Fill-All: returns a job_id immediately; poll
    /ai-fill-jobs/{job_id}. Each section is saved as soon as it's drafted."""
    import asyncio
    doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    await _vendor_scope_template(principal, doc)
    await assert_fees_paid(principal, doc, "work")
    running = await db.ai_fill_jobs.find_one(
        {"template_id": tid, "status": {"$in": ["queued", "running"]}})
    if running:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(running["updated_at"])).total_seconds()
        if age < _FILL_STALE_SECONDS:
            return {"job_id": str(running["_id"]), "status": running["status"],
                    "total": running.get("total", 0), "resumed": True}
        await _fill_job_set(running["_id"], status="failed", phase="Failed",
                            error="Job stopped responding (server restarted). Start Fill All again.")
    sections = doc.get("sections") or []
    targets = [i for i, s in enumerate(sections)
               if not (payload.only_empty and (s.get("body") or "").strip())]
    now = now_iso()
    job = {"template_id": tid, "status": "queued", "phase": "Queued", "progress": 0,
           "total": len(targets), "done": 0, "failed": 0, "error": None,
           "owner_id": principal["id"], "owner_kind": principal.get("kind"),
           "created_at": now, "updated_at": now}
    if not targets:
        job.update(status="done", phase="Nothing to draft — every section already has content",
                   progress=100)
    r = await db.ai_fill_jobs.insert_one(job)
    if targets:
        words = _FILL_WORDS.get(payload.length or "medium", 240)
        asyncio.create_task(_fill_worker(r.inserted_id, tid, targets, doc.get("header") or {},
                                         words, _actor(principal)))
    return {"job_id": str(r.inserted_id), "status": job["status"], "total": len(targets)}


@router.get("/ai-fill-jobs/{job_id}")
async def ai_fill_job_status(job_id: str, principal=Depends(tender_principal)):
    try:
        oid = ObjectId(job_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid job_id")
    doc = await db.ai_fill_jobs.find_one({"_id": oid})
    if not doc or (is_vendor(principal) and doc.get("owner_id") != principal["id"]):
        raise HTTPException(status_code=404, detail="Job not found")
    return {k: doc.get(k) for k in ("template_id", "status", "phase", "progress", "total",
                                    "done", "failed", "error", "created_at", "updated_at")} | {"job_id": job_id}


# =============================================================================
# PHASE A — Auto tender-ref + per-section save
# =============================================================================

@router.post("/next-reference")
async def next_tender_reference(country: str = Query(..., min_length=2, max_length=3),
                                 industry: str = Query("GEN"),
                                 kind: str = Query("tender", regex="^(tender|rfp|rfq)$"),
                                 principal=Depends(tender_principal)):
    """v45f — Guaranteed-unique tender reference:
    PMC-{COUNTRY}-{TYPE}-{YYMMDD-HHMMSS}-{RAND4}-{SEQ}
    Combines a Mongo sequence (monotonic per country+kind) with a random
    4-hex suffix and the exact submission timestamp so collisions are
    mathematically impossible even under concurrency."""
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%y%m%d-%H%M%S")
    seq = await next_sequence(f"tref_{country.upper()}_{kind}")
    rand4 = secrets.token_hex(2).upper()
    ref = f"PMC-{country.upper()}-{kind.upper()}-{stamp}-{rand4}-{seq:04d}"
    return {"reference": ref, "sequence": seq, "generated_at": now.isoformat()}


class SectionPatchIn(BaseModel):
    body: Optional[str] = None
    title: Optional[str] = None
    hint: Optional[str] = None
    order: Optional[int] = None


@router.patch("/templates/{tid}/sections/{code}")
async def patch_one_section(tid: str, code: str, payload: SectionPatchIn,
                             principal=Depends(write_principal)):
    """v45 — Save a single section without rewriting the whole document.
    Bypasses the versions-array append that the full PATCH triggers, so users
    can hit "Save section" after every keystroke burst without polluting history."""
    doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    await _vendor_scope_template(principal, doc)
    await assert_fees_paid(principal, doc, "work")
    sections = doc.get("sections") or []
    idx = next((i for i, s in enumerate(sections) if s.get("code") == code), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Section not found")
    patch = {k: v for k, v in payload.model_dump().items() if v is not None}
    sections[idx] = {**sections[idx], **patch}
    await db.tender_templates.update_one({"_id": ObjectId(tid)},
                                          {"$set": {"sections": sections,
                                                    "updated_at": now_iso()}})
    await audit_log("tender_pro.section_save", _actor(principal), "tender_template", tid,
                    {"code": code, "keys": list(patch.keys())})
    return {"ok": True, "section": sections[idx]}


# =============================================================================
# PHASE B — Country field on templates, save-as-master, EMD master
# =============================================================================

class SaveAsMasterIn(BaseModel):
    country: str = Field(min_length=2, max_length=3)
    industry: str = Field(min_length=2, max_length=80)
    name: Optional[str] = None


@router.post("/templates/{tid}/save-as-master")
async def save_as_master(tid: str, payload: SaveAsMasterIn,
                          principal=Depends(write_principal)):
    """Promote a working draft to the master library under a specific
    (country, industry). Staff masters are published immediately; vendor-
    contributed masters stay `moderation_status=pending` and only enter the
    SHARED library once an active reviewer approves them."""
    doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    await _vendor_scope_template(principal, doc)
    await assert_fees_paid(principal, doc, "work")
    clone = {k: v for k, v in doc.items() if k != "_id"}
    clone["is_master"] = True
    clone["seed"] = False
    clone["country"] = payload.country.upper()
    clone["industry"] = payload.industry
    clone["name"] = payload.name or f"{doc.get('name', 'Untitled')} · {payload.country.upper()} master"
    clone["created_at"] = now_iso()
    clone["created_by"] = principal["id"]
    clone.pop("versions", None)
    clone.pop("version", None)
    clone.pop("review_status", None)
    clone.pop("submitted_at", None)
    clone.pop("review_note", None)
    clone.pop("reviewed_by", None)
    clone.pop("reviewed_at", None)
    clone.pop("published_notice_ref", None)
    clone.pop("approved_by", None)
    clone.pop("approved_at", None)
    for sec in clone.get("sections") or []:
        sec.pop("attachment", None)  # masters ship with no per-clone files
    if is_vendor(principal):
        clone["moderation_status"] = "pending"
        clone["owner_vendor_id"] = principal["id"]
        clone["owner_vendor_ref"] = principal.get("vendor_ref")
    else:
        clone["moderation_status"] = "approved"
    res = await db.tender_templates.insert_one(clone)
    await audit_log("tender_pro.save_as_master", _actor(principal), "tender_template", str(res.inserted_id),
                    {"source": tid, "country": clone["country"], "industry": clone["industry"],
                     "moderation_status": clone["moderation_status"]})
    return _out(await db.tender_templates.find_one({"_id": res.inserted_id}))


# ---------- EMD / Fee master ----------

class EmdSlabIn(BaseModel):
    tender_value_min: float = 0.0
    tender_value_max: Optional[float] = None  # null = infinity
    fee_type: Literal["fixed", "percentage"] = "percentage"
    fixed_amount: Optional[float] = None
    percentage: Optional[float] = None
    pct_min: Optional[float] = None
    pct_max: Optional[float] = None


class EmdMasterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    country: str = Field(default="ALL", min_length=2, max_length=5)
    countries: List[str] = Field(default_factory=list)
    bands: List[str] = Field(default_factory=list)
    tier: Optional[str] = Field(default=None, max_length=40)
    nil_below: Optional[float] = Field(default=None, ge=0)
    extend_type: bool = False
    industry: Optional[str] = None
    # v50h — optional procurement category (matches masters.categories.name).
    # When set, the picker auto-selects this master only for notices in the
    # same category + country. Leave null to apply to all categories.
    category: Optional[str] = None
    kind: str = "emd"  # fee_types.code
    categories: List[str] = Field(default_factory=list)
    currency: str = "USD"
    slabs: List[EmdSlabIn] = Field(default_factory=list)
    is_active: bool = True
    progressive: bool = False
    notes: Optional[str] = None


async def _check_fee_type(body: dict) -> Optional[tuple]:
    """Validate the rule; returns (fee_type_id, $addToSet) to apply after the rule is saved."""
    ft = await get_fee_type(body["kind"])
    if not ft:
        raise HTTPException(status_code=422, detail=f"Unknown fee type '{body['kind']}'. Add it under Masters → Fee types.")
    if body.get("category") and not body.get("categories"):
        body["categories"] = [body["category"]]
    bad = [c for c in body.get("countries") or [] if not re.fullmatch(r"[A-Za-z]{2}", str(c))]
    if bad:
        raise HTTPException(status_code=422, detail=f"Invalid country codes: {', '.join(map(str, bad))}")
    add = {}
    body["tier"] = (body.get("tier") or "").strip() or None
    extend = body.pop("extend_type", False)
    if extend and not body.get("bands"):
        ft = dict(ft)
        if ft.get("country_scope") == "selected" and body.get("countries"):
            cs = [c.upper() for c in body["countries"]]
            add["countries"] = {"$each": cs}
            ft["countries"] = list({*(ft.get("countries") or []), *cs})
        if ft.get("category_scope") == "selected" and ft.get("categories") and body.get("categories"):
            add["categories"] = {"$each": list(body["categories"])}
            ft["categories"] = list({*ft["categories"], *body["categories"]})
    validate_rule_against_type(ft, body)
    if body.get("bands"):
        known = {b["code"] async for b in db.pricing_bands.find({"code": {"$in": body["bands"]}}, {"code": 1})}
        if set(body["bands"]) - known:
            raise HTTPException(status_code=422, detail=f"Unknown pricing band: {', '.join(sorted(set(body['bands']) - known))}")
    return (ft["_id"], add) if add else None


async def _apply_type_extend(ext: Optional[tuple]) -> None:
    if ext:
        await db.fee_types.update_one({"_id": ext[0]}, {"$addToSet": ext[1]})


@router.get("/emd-masters")
async def list_emd_masters(country: Optional[str] = None, kind: Optional[str] = None,
                            category: Optional[str] = None,
                            admin=Depends(require_role("admin", "reviewer"))):
    q: dict = {}
    if country: q["$and"] = [country_q(country)]
    if kind:    q["kind"] = kind
    if category:
        # Return masters scoped to this category OR unscoped (apply-to-all).
        q["$or"] = [
            {"category": category},
            {"categories": category},
            {"category": {"$exists": False}},
            {"category": None},
            {"category": ""},
        ]
    return [_out(d) async for d in db.emd_masters.find(q).sort("name", 1)]


@router.post("/emd-masters")
async def create_emd_master(payload: EmdMasterIn,
                             admin=Depends(require_role("admin"))):
    doc = payload.model_dump()
    ext = await _check_fee_type(doc)
    doc["created_at"] = now_iso()
    doc["created_by"] = admin["id"]
    res = await db.emd_masters.insert_one(doc)
    await _apply_type_extend(ext)
    await audit_log("tender_pro.emd_master_create", admin, "emd_master", str(res.inserted_id),
                    {"name": doc["name"], "country": doc["country"], "kind": doc["kind"]})
    return _out(await db.emd_masters.find_one({"_id": res.inserted_id}))


@router.patch("/emd-masters/{eid}")
async def update_emd_master(eid: str, payload: EmdMasterIn,
                             admin=Depends(require_role("admin"))):
    body = payload.model_dump()
    ext = await _check_fee_type(body)
    body["updated_at"] = now_iso()
    r = await db.emd_masters.update_one({"_id": ObjectId(eid)}, {"$set": body})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="EMD master not found")
    await _apply_type_extend(ext)
    return _out(await db.emd_masters.find_one({"_id": ObjectId(eid)}))


@router.delete("/emd-masters/{eid}")
async def delete_emd_master(eid: str, admin=Depends(require_role("admin"))):
    await db.emd_masters.delete_one({"_id": ObjectId(eid)})
    return {"ok": True}


class EmdComputeIn(BaseModel):
    master_id: str
    tender_value: float


@router.post("/emd-masters/compute")
async def compute_emd(payload: EmdComputeIn,
                       admin=Depends(require_role("admin", "reviewer"))):
    """Given a master id + tender value, return the applicable slab + amount."""
    m = await db.emd_masters.find_one({"_id": ObjectId(payload.master_id)})
    if not m:
        raise HTTPException(status_code=404, detail="EMD master not found")
    v = payload.tender_value
    if m.get("progressive"):
        from routers._fees import compute_amount
        return {"amount": compute_amount(m, v), "type": "stepped", "slab": None, "currency": m.get("currency", "USD")}
    for slab in (m.get("slabs") or []):
        lo = slab.get("tender_value_min") or 0
        hi = slab.get("tender_value_max")
        if v >= lo and (hi is None or v < hi):
            if slab["fee_type"] == "fixed":
                amount = float(slab.get("fixed_amount") or 0)
                return {"amount": amount, "type": "fixed", "slab": slab, "currency": m.get("currency", "USD")}
            pct = float(slab.get("percentage") or 0)
            amount = round(v * pct / 100.0, 2)
            return {"amount": amount, "type": "percentage", "percentage": pct, "slab": slab,
                    "currency": m.get("currency", "USD")}
    raise HTTPException(status_code=422, detail="No slab matches this tender value")


# =============================================================================
# PHASE D — Vendor rating criteria master + multi-rater aggregate
# =============================================================================

def _is_super_admin(admin: dict) -> bool:
    """v46y — super admin = admin/owner at hierarchy_level >= 10.
    Only super admins may set the `weight` on a rating criterion; regular
    admins can create/edit criteria labels/scales but the weight is locked."""
    return "admin" in (admin.get("roles") or [admin.get("role")]) and (admin.get("hierarchy_level") or 0) >= 10


class RatingCriterionIn(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    label: str = Field(min_length=2, max_length=120)
    description: Optional[str] = None
    weight: float = 1.0  # relative — super-admin only (see _is_super_admin)
    scale_min: int = 1
    scale_max: int = 10  # v46y — default 1-10 scoring range


class RatingCriteriaSetIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    country: Optional[str] = None
    industry: Optional[str] = None
    criteria: List[RatingCriterionIn]
    is_default: bool = False
    is_active: bool = True


@router.get("/rating-criteria")
async def list_criteria_sets(admin=Depends(require_role("admin", "reviewer"))):
    return [_out(d) async for d in db.rating_criteria_sets.find({}).sort("name", 1)]


@router.post("/rating-criteria")
async def create_criteria_set(payload: RatingCriteriaSetIn,
                                admin=Depends(require_role("admin"))):
    doc = payload.model_dump()
    doc["created_at"] = now_iso()
    doc["created_by"] = admin["id"]
    # v46y — regular admins cannot set weights on new criteria; force 1.0.
    if not _is_super_admin(admin):
        for c in doc.get("criteria") or []:
            c["weight"] = 1.0
    if doc.get("is_default"):
        await db.rating_criteria_sets.update_many({}, {"$set": {"is_default": False}})
    res = await db.rating_criteria_sets.insert_one(doc)
    return _out(await db.rating_criteria_sets.find_one({"_id": res.inserted_id}))


@router.patch("/rating-criteria/{sid}")
async def update_criteria_set(sid: str, payload: RatingCriteriaSetIn,
                                admin=Depends(require_role("admin"))):
    body = payload.model_dump()
    body["updated_at"] = now_iso()
    # v46y — non-super-admins cannot mutate weights: preserve the existing
    # weight for each criterion by its code, ignoring the incoming values.
    if not _is_super_admin(admin):
        existing = await db.rating_criteria_sets.find_one({"_id": ObjectId(sid)})
        old_weights = {c.get("code"): c.get("weight", 1.0)
                       for c in (existing or {}).get("criteria") or []}
        for c in body.get("criteria") or []:
            c["weight"] = old_weights.get(c.get("code"), 1.0)
    if body.get("is_default"):
        await db.rating_criteria_sets.update_many({"_id": {"$ne": ObjectId(sid)}},
                                                    {"$set": {"is_default": False}})
    r = await db.rating_criteria_sets.update_one({"_id": ObjectId(sid)}, {"$set": body})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Criteria set not found")
    return _out(await db.rating_criteria_sets.find_one({"_id": ObjectId(sid)}))


@router.get("/rating-criteria/me")
async def rating_admin_context(admin=Depends(require_role("admin", "reviewer"))):
    """v46y — tell the frontend whether this admin can edit weights."""
    return {"is_super_admin": _is_super_admin(admin),
            "hierarchy_level": admin.get("hierarchy_level") or 0,
            "roles": admin.get("roles") or [admin.get("role")]}


@router.delete("/rating-criteria/{sid}")
async def delete_criteria_set(sid: str, admin=Depends(require_role("admin"))):
    await db.rating_criteria_sets.delete_one({"_id": ObjectId(sid)})
    return {"ok": True}


class MultiRatingIn(BaseModel):
    vendor_ref: str
    criteria_set_id: str
    rater_type: Literal["admin", "vendor", "platform"] = "admin"
    rater_email: Optional[str] = None
    rater_vendor_ref: Optional[str] = None    # if rater_type=vendor (blind)
    scores: dict                              # {criterion_code: int}
    comment: Optional[str] = None


@router.post("/ratings/multi")
async def submit_multi_rating(payload: MultiRatingIn,
                                admin=Depends(require_role("admin", "reviewer"))):
    """Record one rating event with per-criterion scores. Aggregate is
    recomputed on read (see /ratings/aggregate/{vendor_ref})."""
    s = await db.rating_criteria_sets.find_one({"_id": ObjectId(payload.criteria_set_id)})
    if not s:
        raise HTTPException(status_code=404, detail="Criteria set not found")
    doc = payload.model_dump()
    doc["created_at"] = now_iso()
    doc["created_by"] = admin["id"]
    # Normalise: enforce scale bounds
    scale_by_code = {c["code"]: (c["scale_min"], c["scale_max"], float(c.get("weight") or 1))
                      for c in s.get("criteria") or []}
    weighted_total = 0.0
    weight_sum = 0.0
    for code, val in (doc.get("scores") or {}).items():
        if code not in scale_by_code:
            continue
        lo, hi, w = scale_by_code[code]
        v = max(lo, min(hi, float(val)))
        # normalise to 0..1 then weight
        span = max(1, hi - lo)
        weighted_total += ((v - lo) / span) * w
        weight_sum += w
    doc["score_out_of_100"] = round((weighted_total / weight_sum) * 100, 2) if weight_sum else 0
    res = await db.vendor_multi_ratings.insert_one(doc)
    return _out(await db.vendor_multi_ratings.find_one({"_id": res.inserted_id}))


@router.get("/ratings/aggregate/{vendor_ref}")
async def rating_aggregate(vendor_ref: str,
                             admin=Depends(require_role("admin", "reviewer", "auditor"))):
    rows = [r async for r in db.vendor_multi_ratings.find({"vendor_ref": vendor_ref})]
    if not rows:
        return {"vendor_ref": vendor_ref, "count": 0, "average_score": None, "raters": []}
    avg = round(sum(r.get("score_out_of_100") or 0 for r in rows) / len(rows), 2)
    return {"vendor_ref": vendor_ref, "count": len(rows), "average_score": avg,
            "raters": [{"type": r.get("rater_type"),
                         "score": r.get("score_out_of_100"),
                         "created_at": r.get("created_at")} for r in rows]}
