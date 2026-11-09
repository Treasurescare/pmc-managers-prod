"""v61b — Marketplace photos, spec sheets and AI catalogue import (brochure/PDF -> product drafts with photos)."""
import asyncio
import base64
import hashlib
import io
import json
import os
import re
import secrets
import tempfile
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from db import db
from models.base import now_iso
from routers.vendor_auth import current_vendor
from security import require_csrf

router = APIRouter(prefix="/api/v1/market", tags=["marketplace-media"])
IMG = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
DOC = {"pdf": "application/pdf"}
MAX_PHOTO, MAX_DOC, MAX_CATALOGUE = 8 * 1024 * 1024, 10 * 1024 * 1024, 25 * 1024 * 1024
MAX_PAGES, MAX_PRODUCTS, MAX_EMBEDDED = 30, 60, 80
_TASKS: set = set()


async def _seller(request: Request) -> dict:
    v = await current_vendor(request)
    await require_csrf(request)
    return v


def _ext(name: str) -> str:
    return (name or "").rsplit(".", 1)[-1].lower() if "." in (name or "") else ""


def _jpeg(data: bytes, max_side: int = 1600) -> bytes:
    from PIL import Image
    im = Image.open(io.BytesIO(data))
    im.thumbnail((max_side, max_side))
    if im.mode not in ("RGB", "L"):
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, mask=im.convert("RGBA").split()[-1])
        im = bg
    out = io.BytesIO()
    im.convert("RGB").save(out, "JPEG", quality=85)
    return out.getvalue()


CARD_W, CARD_H = 1200, 900


def _card(data: bytes) -> bytes:
    """Marketplace photo standard: centre-cropped to 4:3 and resized to 1200x900 JPEG."""
    from PIL import Image, ImageOps
    im = Image.open(io.BytesIO(_jpeg(data, 4000)))
    im = ImageOps.fit(im.convert("RGB"), (CARD_W, CARD_H), Image.LANCZOS)
    out = io.BytesIO()
    im.save(out, "JPEG", quality=86)
    return out.getvalue()


async def _store(owner: str, kind: str, name: str, mime: str, data: bytes, **extra) -> dict:
    mid = secrets.token_urlsafe(18)
    await db.mkt_media.insert_one({"_id": mid, "owner": owner, "kind": kind, "name": name[:160], "mime": mime,
                                   "size": len(data), "data_b64": base64.b64encode(data).decode(), "created_at": now_iso(), **extra})
    return {"id": mid, "kind": kind, "name": name[:160], **extra}


async def check_media(owner: str, photos: list, documents: list) -> None:
    for kind, ids in (("photo", list(photos)), ("document", [d.get("id") for d in documents])):
        if ids and await db.mkt_media.count_documents({"_id": {"$in": ids}, "owner": owner, "kind": kind}) != len(set(ids)):
            raise HTTPException(status_code=400, detail="One of the photos or documents could not be found — please upload it again")


@router.post("/media")
async def upload_media(file: UploadFile = File(...), kind: str = Form("photo"), v=Depends(_seller)):
    ext, body = _ext(file.filename), await file.read()
    if kind == "photo":
        if ext not in IMG:
            raise HTTPException(status_code=400, detail="Photos must be JPG, PNG or WEBP")
        if len(body) > MAX_PHOTO:
            raise HTTPException(status_code=413, detail="Photo too large (max 8 MB)")
        try:
            body = _card(body)
        except Exception:
            raise HTTPException(status_code=400, detail="This image could not be opened — please try another file")
        return await _store(v["id"], "photo", file.filename, "image/jpeg", body)
    if kind == "document":
        if ext not in DOC or not body.lstrip()[:5].startswith(b"%PDF"):
            raise HTTPException(status_code=400, detail="Spec sheets must be PDF files")
        if len(body) > MAX_DOC:
            raise HTTPException(status_code=413, detail="Spec sheet too large (max 10 MB)")
        return await _store(v["id"], "document", file.filename, "application/pdf", body)
    raise HTTPException(status_code=400, detail="Unknown upload type")


@router.get("/media/{mid}")
async def get_media(mid: str, download: bool = False):
    m = await db.mkt_media.find_one({"_id": mid})
    if not m:
        raise HTTPException(status_code=404, detail="File not found")
    disp = "attachment" if download else "inline"
    safe = re.sub(r"[^A-Za-z0-9._ -]", "_", m.get("name") or "file")
    return Response(base64.b64decode(m["data_b64"]), media_type=m["mime"],
                    headers={"Cache-Control": "public, max-age=86400", "Content-Disposition": f'{disp}; filename="{safe}"',
                             "X-Content-Type-Options": "nosniff"})


# ---------------- AI catalogue import ----------------
CAT_SYS = (
    "You read supplier product catalogues, brochures and price lists. List every distinct product offered. Reply with ONLY a "
    "JSON object, no markdown: {\"products\": [{\"title\": short product name, \"description\": 2-4 factual sentences a buyer "
    "would want, \"category\": short category, \"unit\": selling unit (unit, set, lot, tonne, metre...), \"specs\": list of "
    "\"Name: value\" strings, \"page\": 1-based page number where the product appears, \"photo_box\": [ymin, xmin, ymax, xmax] "
    "normalised 0-1000 tightly around the product's photo on that page, or null when there is no photo}]}. "
    f"At most {MAX_PRODUCTS} products. Use only facts in the document; never invent prices, certifications or numbers.")


def _embedded(doc, pages: int) -> list:
    import fitz
    out, seen = [], set()
    for p in range(pages):
        page = doc[p]
        area = page.rect.width * page.rect.height
        for info in page.get_image_info(xrefs=True):
            x, bb = info.get("xref"), fitz.Rect(info["bbox"])
            if not x or x in seen or info.get("width", 0) < 120 or info.get("height", 0) < 120 or bb.get_area() < area * 0.01:
                continue
            seen.add(x)
            try:
                raw = doc.extract_image(x)["image"]
                out.append({"page": p + 1, "bbox": (bb.x0 / page.rect.width, bb.y0 / page.rect.height,
                                                    bb.x1 / page.rect.width, bb.y1 / page.rect.height), "data": _card(raw)})
            except Exception:
                continue
            if len(out) >= MAX_EMBEDDED:
                return out
    return out


def _iou(a, b) -> float:
    ix, iy = max(0, min(a[2], b[2]) - max(a[0], b[0])), max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0


def _crop(page_png: bytes, box) -> Optional[bytes]:
    from PIL import Image
    im = Image.open(io.BytesIO(page_png))
    w, h = im.size
    x0, y0, x1, y1 = int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h)
    if x1 - x0 < 40 or y1 - y0 < 40:
        return None
    out = io.BytesIO()
    im.crop((x0, y0, x1, y1)).convert("RGB").save(out, "JPEG", quality=90)
    return _card(out.getvalue())


async def _ask_ai(path: str, mime: str, pages: int) -> list:
    from pmc_lib.llm.chat import FileContentWithMimeType, LlmChat, UserMessage
    from routers.tender_pro import _llm_key
    chat = LlmChat(api_key=_llm_key(), session_id=f"cat-{secrets.token_hex(6)}", system_message=CAT_SYS) \
        .with_model("gemini", "gemini-3.1-pro-preview")
    reply = await chat.send_message(UserMessage(
        text=f"The attached file is a supplier catalogue with {pages} page(s). Read every page and reply with the JSON object.",
        file_contents=[FileContentWithMimeType(file_path=path, mime_type=mime)]))
    m = re.search(r"\{.*\}", reply or "", re.S)
    data = json.loads(m.group(0)) if m else {}
    return [p for p in (data.get("products") or []) if isinstance(p, dict) and p.get("title")][:MAX_PRODUCTS]


def _box(p: dict):
    b = p.get("photo_box")
    if not (isinstance(b, list) and len(b) == 4 and all(isinstance(x, (int, float)) for x in b)):
        return None
    ymin, xmin, ymax, xmax = [min(max(float(x), 0), 1000) / 1000 for x in b]
    return (xmin, ymin, xmax, ymax) if xmax > xmin and ymax > ymin else None


def _prep(name: str, body: bytes):
    import fitz
    if _ext(name) == "pdf":
        doc = fitz.open(stream=body, filetype="pdf")
        pages = min(len(doc), MAX_PAGES)
        sub = fitz.open()
        sub.insert_pdf(doc, to_page=pages - 1)
        return doc, pages, _embedded(doc, pages), sub.tobytes(garbage=3, deflate=True), "application/pdf"
    return None, 1, [], _jpeg(body, 2400), "image/jpeg"


def _page_crop(doc, send: bytes, page: int, pages: int, box, cache: dict) -> Optional[bytes]:
    if page not in cache:
        cache[page] = doc[page - 1].get_pixmap(dpi=150).tobytes("png") if doc and page <= pages else (None if doc else send)
    return cache[page] and _crop(cache[page], box)


async def _run_import(iid: str, owner: str, name: str, body: bytes, charge_ref: str) -> None:
    try:
        doc, pages, embedded, send, mime = await asyncio.to_thread(_prep, name, body)
        is_pdf = mime == "application/pdf"
        fd, path = tempfile.mkstemp(suffix=".pdf" if is_pdf else ".jpg")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(send)
            products = await _ask_ai(path, mime, pages)
        finally:
            os.remove(path)
        stored = []
        for e in embedded:
            stored.append({**(await _store(owner, "photo", f"catalogue-p{e['page']}.jpg", "image/jpeg", e["data"],
                                           page=e["page"], import_id=iid)), "bbox": e["bbox"]})
        renders: dict = {}
        out = []
        for p in products:
            page, box, photos = int(p.get("page") or 1), _box(p), []
            if box:
                best = max((s for s in stored if s["page"] == page), key=lambda s: _iou(s["bbox"], box), default=None)
                if best and _iou(best["bbox"], box) > 0.25:
                    photos.append(best["id"])
                else:
                    crop = await asyncio.to_thread(_page_crop, doc, send, page, pages, box, renders)
                    if crop:
                        photos.append((await _store(owner, "photo", f"{str(p['title'])[:60]}.jpg", "image/jpeg", crop,
                                                    page=page, import_id=iid))["id"])
            out.append({"title": str(p["title"])[:160], "description": str(p.get("description") or "")[:4000],
                        "category": str(p.get("category") or "")[:120], "unit": str(p.get("unit") or "unit")[:30],
                        "specs": [str(s)[:200] for s in (p.get("specs") or [])][:30], "page": page, "photos": photos})
        await db.mkt_imports.update_one({"_id": iid}, {"$set": {
            "status": "done", "products": out, "pages": pages, "finished_at": now_iso(),
            "images": [{"id": s["id"], "page": s["page"]} for s in stored]}})
    except Exception:
        await db.mkt_media.delete_many({"import_id": iid})
        await db.paid_uses.update_one({"vendor_id": owner, "code": "mkt_catalogue_ai", "ref": charge_ref, "used": True}, {"$set": {"used": False}})
        await db.mkt_imports.update_one({"_id": iid}, {"$set": {
            "status": "failed", "finished_at": now_iso(),
            "error": "We could not read this catalogue. Please try a clearer copy, a smaller file, or add the products by hand."}})


@router.post("/catalogue/import")
async def start_import(file: UploadFile = File(...), v=Depends(_seller)):
    ext, body = _ext(file.filename), await file.read()
    if ext not in ("pdf", *IMG):
        raise HTTPException(status_code=400, detail="Upload a PDF catalogue or a JPG/PNG photo of a brochure page")
    if len(body) > MAX_CATALOGUE:
        raise HTTPException(status_code=413, detail="Catalogue too large (max 25 MB)")
    if ext == "pdf":
        try:
            import fitz
            if fitz.open(stream=body, filetype="pdf").page_count < 1:
                raise ValueError
        except Exception:
            raise HTTPException(status_code=400, detail="This PDF looks damaged or only partly downloaded. Please try another copy.")
    charge_ref = f"cat-{hashlib.sha256(body).hexdigest()[:24]}"
    from routers.growth import charge_or_pass
    await charge_or_pass(v, "mkt_catalogue_ai", charge_ref, "AI catalogue reading")
    iid = secrets.token_urlsafe(12)
    doc_ref = None
    if ext == "pdf" and len(body) <= MAX_DOC:
        doc_ref = {"id": (await _store(v["id"], "document", file.filename, "application/pdf", body, import_id=iid))["id"],
                   "name": file.filename[:160]}
    await db.mkt_imports.insert_one({"_id": iid, "owner": v["id"], "file_name": file.filename, "status": "reading",
                                     "catalogue_doc": doc_ref, "created_at": now_iso()})
    t = asyncio.create_task(_run_import(iid, v["id"], file.filename, body, charge_ref))
    _TASKS.add(t)
    t.add_done_callback(_TASKS.discard)
    return {"id": iid, "status": "reading"}


@router.get("/catalogue/import/{iid}")
async def get_import(iid: str, v=Depends(current_vendor)):
    d = await db.mkt_imports.find_one({"_id": iid, "owner": v["id"]})
    if not d:
        raise HTTPException(status_code=404, detail="Import not found")
    d["id"] = d.pop("_id")
    return d


class CategoryNew(BaseModel):
    name: str = Field(min_length=2, max_length=120)


@router.post("/categories")
async def add_category(body: CategoryNew, v=Depends(_seller)):
    name = re.sub(r"\s+", " ", body.name).strip()
    found = await db.categories.find_one({"name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}})
    if found:
        if not found.get("is_active", True):
            raise HTTPException(status_code=400, detail="This category has been switched off by PMC. Please choose another one.")
        return {"id": str(found["_id"]), "name": found["name"], "created": False}
    code = "mkt-" + (re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:30] or "cat") + "-" + secrets.token_hex(2)
    r = await db.categories.insert_one({"code": code, "name": name, "source": "supplier", "is_active": True, "needs_review": True,
                                        "created_by_vendor": v["id"], "created_at": now_iso()})
    return {"id": str(r.inserted_id), "name": name, "created": True}


class DraftIn(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(default="", max_length=6000)
    category: str = Field(default="", max_length=120)
    unit: str = Field(default="unit", max_length=30)
    photos: list[str] = Field(default_factory=list, max_length=12)
    documents: list[dict] = Field(default_factory=list, max_length=6)


class BulkIn(BaseModel):
    items: list[DraftIn] = Field(min_length=1, max_length=MAX_PRODUCTS)


@router.post("/listings/bulk")
async def bulk_drafts(body: BulkIn, v=Depends(_seller)):
    rows = []
    for it in body.items:
        docs = [{"id": str(d.get("id")), "name": str(d.get("name") or "Spec sheet")[:160]} for d in it.documents]
        await check_media(v["id"], it.photos, docs)
        rows.append({
            **it.model_dump(), "documents": docs, "quantity": 1, "currency": "USD", "location": "", "image_url": "",
            "sale_modes": ["fixed"], "start_price": None, "reserve_price": None, "min_increment": 1, "buy_now_price": None,
            "closes_at": None, "eligibility": "verified_buyers", "needs_details": True, "source": "catalogue_ai",
            "seller_id": v["id"], "seller_name": v.get("company_name") or v.get("email"),
            "status": "draft", "created_at": now_iso(), "updated_at": now_iso()})
    r = await db.mkt_listings.insert_many(rows)
    return {"created": len(r.inserted_ids), "ids": [str(i) for i in r.inserted_ids]}


async def ensure_indexes():
    await db.mkt_media.create_index("owner")
    await db.mkt_imports.create_index("owner")
