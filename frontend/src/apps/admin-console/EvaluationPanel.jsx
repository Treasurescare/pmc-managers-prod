import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { evalApi, bidApi, adminApi, formatApiError, showApiError} from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import RubricEditor from "./evaluation/RubricEditor";
import BidScoreList from "./evaluation/BidScoreList";
import AwardReport from "./evaluation/AwardReport";
import { InfoDot } from "@/components/InfoDot";
import CreatorDateFilterBar, { matchCreatorDate, creatorDateParams } from "@/components/CreatorDateFilterBar";

const DEFAULT_CRITERIA = [
  { code: "experience", label: "Relevant Experience", weight: 0.30, max_score: 100 },
  { code: "methodology", label: "Methodology & Approach", weight: 0.30, max_score: 100 },
  { code: "team", label: "Team & Key Personnel", weight: 0.20, max_score: 100 },
  { code: "financial_health", label: "Financial Health", weight: 0.20, max_score: 100 },
];

export default function EvaluationPanel() {
  const { t } = useI18n();
  // #43 — persist the picked notice in the URL so a page refresh reloads the
  // same tender and its saved rubric (previously plain state reset to the
  // default criteria on refresh, so admins thought their weights were lost).
  const [searchParams, setSearchParams] = useSearchParams();
  const [noticeRef, setNoticeRef] = useState(() => searchParams.get("notice") || "");
  useEffect(() => {
    setSearchParams(noticeRef ? { notice: noticeRef } : {}, { replace: true });
  }, [noticeRef]);  // eslint-disable-line react-hooks/exhaustive-deps
  // v52cb — bug: typing a partial tender number like "18" did not surface
  // the matching tender (the field was a free-text input, not a picker).
  // Load every notice so the admin can type any fragment of the ref or
  // title and get the matching tenders in a dropdown.
  const [allNotices, setAllNotices] = useState([]);
  const [noticeQuery, setNoticeQuery] = useState("");
  const [noticeOpen, setNoticeOpen] = useState(false);
  useEffect(() => {
    adminApi.listAllNotices({ limit: 500, _: Date.now() })
      .then((d) => setAllNotices(d.items || []))
      .catch(() => setAllNotices([]));
  }, []);
  const noticeMatches = useMemo(() => {
    const q = noticeQuery.trim().toLowerCase();
    if (!q) return allNotices.slice(0, 20);
    // Case-insensitive substring match on ref AND title so "18" surfaces
    // PMC-NOT-2026-0018 and "pump" surfaces matching titles.
    return allNotices.filter((n) =>
      (n.notice_ref || "").toLowerCase().includes(q)
      || (n.title || "").toLowerCase().includes(q)
    ).slice(0, 50);
  }, [allNotices, noticeQuery]);
  const [rubric, setRubric] = useState({
    technical_criteria: DEFAULT_CRITERIA, commercial_weight: 0.4, minimum_technical: 60,
  });
  const [coiChoice, setCoiChoice] = useState({ has_conflict: false, details: "" });
  const [bids, setBids] = useState([]);
  const [report, setReport] = useState(null);
  const [scoreDraft, setScoreDraft] = useState({});
  // v46m — envelope lock state. When either envelope has been locked we hide
  // the "Lock" button and disable score submission (backend also refuses).
  const [lockState, setLockState] = useState({ technical_locked_at: null, commercial_locked_at: null });
  // Bug-blitz (c) — the RubricEditor writes its current validation errors
  // here so saveRubric() can veto keyboard/programmatic bypass of the
  // disabled Save button.
  const rubricErrorsRef = useRef([]);
  // v52v — Created by / from / to filter the notice picker list AND the loaded bids.
  const [cdf, setCdf] = useState({ createdBy: "", from: "", to: "" });
  const noticeCreators = useMemo(() => allNotices.map((n) => n.created_by_email).filter(Boolean), [allNotices]);
  const bidCreators = useMemo(() => bids.map((b) => b.vendor_email).filter(Boolean), [bids]);
  const visibleBids = useMemo(() => bids.filter(matchCreatorDate(cdf)), [bids, cdf]);

  const loadBids = useCallback(async () => {
    if (!noticeRef) return;
    try {
      // v52w — created-by/from/to pushed to the API (bids endpoint supports
      // them since v52v); client-side match stays as instant fallback.
      const list = await bidApi.list({ notice_ref: noticeRef, ...creatorDateParams(cdf) });
      setBids(list || []);
    } catch (e) { showApiError(e); }
  }, [noticeRef, cdf]);
  const loadLockState = useCallback(async () => {
    if (!noticeRef) { setLockState({ technical_locked_at: null, commercial_locked_at: null }); return; }
    try {
      const s = await evalApi.lockState(noticeRef);
      setLockState(s);
    } catch { /* notice may not exist yet — leave defaults */ }
  }, [noticeRef]);
  // v52bz — bug #43: load persisted rubric when the admin picks a notice,
  // so saved weights survive page refresh. Previously the editor always
  // showed DEFAULT_CRITERIA until the admin re-saved.
  const loadRubric = useCallback(async () => {
    if (!noticeRef) return;
    try {
      const r = await evalApi.getRubric(noticeRef);
      if (r && (r.technical_criteria || r.commercial_weight !== undefined)) {
        setRubric({
          technical_criteria: r.technical_criteria?.length ? r.technical_criteria : DEFAULT_CRITERIA,
          commercial_weight: r.commercial_weight ?? 0.4,
          minimum_technical: r.minimum_technical ?? 60,
        });
      }
    } catch { /* no rubric yet — keep defaults */ }
  }, [noticeRef]);
  useEffect(() => { loadBids(); loadLockState(); loadRubric(); }, [loadBids, loadLockState, loadRubric]);
  const techLocked = !!lockState?.technical_locked_at;
  const commLocked = !!lockState?.commercial_locked_at;
  const fullyLocked = techLocked && commLocked;

  // Bug-blitz (d) — Locked-eval reopen. When both envelopes are sealed for
  // the entered notice_ref, silently pull the saved award report so the
  // user sees the historical decision instead of a blank scoring surface.
  useEffect(() => {
    if (!noticeRef || !fullyLocked) return;
    let cancelled = false;
    (async () => {
      try {
        const r = await evalApi.awardReport(noticeRef);
        if (!cancelled) setReport(r);
      } catch { /* silent — panel still usable */ }
    })();
    return () => { cancelled = true; };
  }, [noticeRef, fullyLocked]);

  const saveRubric = async () => {
    if (!noticeRef) return toast.error("Enter a tender notice ref first");
    // Bug-blitz (c) — defensive gate: the button is already `disabled` when
    // errors exist, but keyboard/programmatic clicks used to slip through.
    const errs = rubricErrorsRef.current || [];
    if (errs.length > 0) { toast.error(errs[0]); return; }
    try {
      await evalApi.saveRubric({ notice_ref: noticeRef, ...rubric });
      toast.success("Rubric saved");
    } catch (e) { showApiError(e); }
  };

  const declareCOI = async () => {
    if (!noticeRef) return toast.error("Enter notice ref first");
    try {
      await evalApi.declareCOI({ notice_ref: noticeRef, ...coiChoice });
      toast.success("COI recorded");
    } catch (e) { showApiError(e); }
  };

  const submitTechScore = async (bid) => {
    const s = scoreDraft[bid.id] || {};
    try {
      await evalApi.score({ bid_id: bid.id, kind: "technical", scores: s });
      toast.success("Technical score saved");
    } catch (e) {
      // v52bz — bug #44: scores returning 0 was almost always "must declare
      // COI before scoring" — the toast now surfaces that reason clearly and
      // offers a one-click auto-declare for the no-conflict path.
      const msg = e?.response?.data?.detail || "";
      if (msg.includes("Conflict-of-Interest")) {
        try {
          await evalApi.declareCOI({ notice_ref: bid.notice_ref, has_conflict: false, details: "Auto-declared via scoring form" });
          await evalApi.score({ bid_id: bid.id, kind: "technical", scores: s });
          toast.success("Technical score saved (COI auto-declared as 'no conflict')");
        } catch (e2) { showApiError(e2); }
      } else { showApiError(e); }
    }
  };
  const submitCommScore = async (bid) => {
    const v = scoreDraft[`${bid.id}_comm`] || 0;
    try {
      await evalApi.score({ bid_id: bid.id, kind: "commercial", scores: { commercial: Number(v) } });
      toast.success("Commercial score saved");
    } catch (e) { showApiError(e); }
  };

  const generateReport = async () => {
    if (!noticeRef) return toast.error("Enter notice ref first");
    try {
      const r = await evalApi.awardReport(noticeRef);
      setReport(r);
    } catch (e) { showApiError(e); }
  };

  const lock = async (kind) => {
    try {
      await evalApi.lockEnvelope(noticeRef, kind);
      toast.success(`${kind} envelope locked`);
      await loadLockState();
    } catch (e) { showApiError(e); }
  };

  return (
    <div data-testid="admin-evaluation-panel" className="space-y-6">
      <div className="bg-white border border-brand-navy/10 p-4">
        <CreatorDateFilterBar value={cdf} onChange={setCdf} creators={[...new Set([...noticeCreators, ...bidCreators])]} testid="eval-cdf" />
        <div className="flex flex-wrap gap-3 items-end">
          <label className="flex-1 min-w-[280px] text-sm relative">
            <span className="pmc-label">{t("panels.evaluation.notice_ref")}<InfoDot tip="Reference of the tender being evaluated. Type any fragment (e.g. '18', 'pump') to find the tender; pick a row to lock it in." /></span>
            <input
              value={noticeOpen ? noticeQuery : (noticeRef || noticeQuery)}
              onChange={(e) => { setNoticeQuery(e.target.value); setNoticeOpen(true); }}
              onFocus={() => { setNoticeQuery(noticeRef || ""); setNoticeOpen(true); }}
              onBlur={() => setTimeout(() => setNoticeOpen(false), 150)}
              placeholder="Type tender number or title (e.g. 18)"
              className="mt-1 w-full px-3 py-2 border border-brand-navy/20"
              data-testid="eval-notice-ref"
              autoComplete="off" />
            {noticeOpen && noticeMatches.length > 0 && (
              <div className="absolute z-20 left-0 right-0 top-full mt-1 bg-white border border-brand-navy/20 shadow-lg max-h-80 overflow-auto"
                   data-testid="eval-notice-picker">
                {noticeMatches.map((n) => (
                  <button key={n.id || n.notice_ref} type="button"
                          data-testid={`eval-notice-opt-${n.notice_ref}`}
                          onMouseDown={(ev) => {
                            ev.preventDefault();
                            setNoticeRef(n.notice_ref);
                            setNoticeQuery(n.notice_ref);
                            setNoticeOpen(false);
                          }}
                          className="w-full text-left px-3 py-2 text-sm hover:bg-brand-navy/5 border-b border-brand-navy/5 last:border-0">
                    <div className="font-mono text-brand-navy">{n.notice_ref}</div>
                    <div className="text-xs text-brand-navy/60 truncate">{n.title || "—"}</div>
                  </button>
                ))}
              </div>
            )}
            {noticeOpen && noticeMatches.length === 0 && noticeQuery.trim() && (
              <div className="absolute z-20 left-0 right-0 top-full mt-1 bg-white border border-brand-navy/20 shadow-lg px-3 py-2 text-xs text-brand-navy/60"
                   data-testid="eval-notice-nomatch">
                No tenders match "{noticeQuery}" — try a different fragment of the number or title.
              </div>
            )}
          </label>
          <button onClick={() => lock("technical")} data-testid="lock-technical"
            disabled={techLocked}
            title={techLocked ? `Sealed at ${lockState.technical_locked_at}` : ""}
            className="px-3 py-2 text-[11px] uppercase tracking-widest border disabled:opacity-40 disabled:cursor-not-allowed">
            {techLocked ? "Technical · Sealed 🔒" : t("panels.evaluation.lock_tech")}
            <InfoDot tip="Freeze technical envelope — no more technical scores can be added or edited after this action. Auditable." />
          </button>
          <button onClick={() => lock("commercial")} data-testid="lock-commercial"
            disabled={commLocked}
            title={commLocked ? `Sealed at ${lockState.commercial_locked_at}` : ""}
            className="px-3 py-2 text-[11px] uppercase tracking-widest border disabled:opacity-40 disabled:cursor-not-allowed">
            {commLocked ? "Commercial · Sealed 🔒" : t("panels.evaluation.lock_comm")}
            <InfoDot tip="Freeze commercial envelope after tech scoring is complete. Required before Award Report can be generated." />
          </button>
          <button onClick={generateReport} data-testid="award-report-btn"
            className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white">
            {t("panels.evaluation.generate_report")}
            <InfoDot tip="Produce the L1 award report (weighted tech + commercial scoring) — this is the artefact the Committee votes on." />
          </button>
        </div>
      </div>

      <RubricEditor rubric={rubric} setRubric={setRubric} onSave={saveRubric} errorRef={rubricErrorsRef} />

      {fullyLocked && report && (
        <div className="border-l-4 border-brand-navy bg-brand-pale p-4 text-sm text-brand-navy"
             data-testid="locked-eval-notice">
          <div className="font-semibold uppercase tracking-widest text-[11px]">Evaluation sealed</div>
          <div className="mt-1">Both envelopes for <b>{noticeRef}</b> are locked. The saved Award Report is shown below — no further scoring or re-evaluation is permitted.</div>
        </div>
      )}

      {/* v51au — defensive null-guard: AwardReport used to crash the whole
          Evaluation page (docx #14 / xlsx #18) when `report` was partial —
          e.g. no `ranked` or `rubric` arrays. Only render it when a non-null
          report is available. BidScoreList and other sub-components are
          already safe. */}
      {(techLocked || commLocked) && (
        <div className="border-l-4 border-emerald-500 bg-emerald-50 p-4 text-sm text-emerald-900"
             data-testid="envelope-lock-banner">
          <div className="font-semibold uppercase tracking-widest text-[11px]">Envelope status</div>
          <ul className="mt-1 space-y-0.5">
            {techLocked && (
              <li>Technical envelope sealed at <b>{lockState.technical_locked_at}</b>{lockState.technical_locked_by ? ` by ${lockState.technical_locked_by}` : ""}. No further scores accepted.</li>
            )}
            {commLocked && (
              <li>Commercial envelope sealed at <b>{lockState.commercial_locked_at}</b>{lockState.commercial_locked_by ? ` by ${lockState.commercial_locked_by}` : ""}. No further scores accepted.</li>
            )}
          </ul>
        </div>
      )}

      <div className="bg-white border p-4">
        <div className="pmc-label mb-2">{t("panels.evaluation.coi_heading")}</div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={coiChoice.has_conflict}
            onChange={(e) => setCoiChoice({ ...coiChoice, has_conflict: e.target.checked })}
            data-testid="coi-has-conflict" />
          {t("panels.evaluation.coi_checkbox")}
        </label>
        {coiChoice.has_conflict && (
          <input value={coiChoice.details}
            onChange={(e) => setCoiChoice({ ...coiChoice, details: e.target.value })}
            placeholder={t("panels.evaluation.coi_placeholder")}
            className="mt-2 w-full px-3 py-2 border" />
        )}
        <button onClick={declareCOI} data-testid="declare-coi"
          className="mt-2 px-4 py-2 text-[11px] uppercase tracking-widest border">
          {t("panels.evaluation.declare")}
        </button>
      </div>

      <BidScoreList
        bids={visibleBids} rubric={rubric}
        scoreDraft={scoreDraft} setScoreDraft={setScoreDraft}
        onSaveTech={submitTechScore} onSaveComm={submitCommScore}
        readOnly={fullyLocked}
      />

      <AwardReport report={report} />
    </div>
  );
}
