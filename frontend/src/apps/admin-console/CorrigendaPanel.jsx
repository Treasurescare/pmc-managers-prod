import { useCallback, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { corrigendaApi, adminApi, publicApi, formatApiError, showApiError} from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import { InfoDot } from "@/components/InfoDot";
import { useListPager } from "@/components/ListPager";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";

// v52bm — Fields on a notice that a corrigendum can amend. Order drives the
// display order of the "Current → New" rows. `kind` hints the input widget.
const NOTICE_FIELDS = [
  { key: "title",                 label: "Title",                 kind: "text" },
  { key: "description",           label: "Description",           kind: "textarea" },
  { key: "category",              label: "Category",              kind: "text" },
  { key: "document_type",         label: "Document type",         kind: "text" },
  { key: "delivery_country",      label: "Delivery country",      kind: "text" },
  { key: "submission_deadline",   label: "Submission deadline",   kind: "datetime" },
  { key: "budget_currency",       label: "Budget currency",       kind: "text" },
  { key: "budget_amount",         label: "Budget amount",         kind: "number" },
  { key: "tender_fee",            label: "Tender fee",            kind: "number" },
  { key: "form_of_contract",      label: "Form of contract",      kind: "text" },
  { key: "emd_fixed_amount",      label: "EMD fixed amount",      kind: "number",
    read: (n) => n?.emd_config?.fixed_amount },
  { key: "emd_percentage",        label: "EMD % of budget",       kind: "number",
    read: (n) => n?.emd_config?.percentage },
  { key: "pre_bid_meeting_date",  label: "Pre-bid meeting",       kind: "datetime" },
  { key: "clarification_deadline",label: "Clarifications close",  kind: "datetime" },
];

const readField = (notice, f) => {
  if (f.read) return f.read(notice);
  return notice ? notice[f.key] : undefined;
};

const fmtValue = (v, kind) => {
  if (v === undefined || v === null || v === "") return "—";
  if (kind === "datetime") return String(v).slice(0, 16).replace("T", " ");
  if (kind === "number") return typeof v === "number" ? v.toLocaleString() : String(v);
  return String(v);
};

/** Wave 39 + v52bm — Corrigendum publisher. Shows every field of the parent
 *  notice as a Current → New row with a per-change description so the
 *  resulting diff is self-describing on the public corrigendum page. */
export default function CorrigendaPanel() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [notices, setNotices] = useState([]);
  const [pickedNoticeRef, setPickedNoticeRef] = useState("");
  const [pickedNotice, setPickedNotice] = useState(null);
  const [items, setItems] = useState([]);
  const [showNew, setShowNew] = useState(false);
  const [noticeSearch, setNoticeSearch] = useState("");
  const [corrSearch, setCorrSearch] = useState("");
  const [attachingTo, setAttachingTo] = useState(null); // corrigendum id currently uploading
  // v52bm — corrigendum_date defaults to today (admin-visible, published to
  // vendors as the "effective from" date and surfaced in the audit record).
  const todayLocal = () => {
    const d = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };
  const [draft, setDraft] = useState({
    title: "", summary: "", corrigendum_date: todayLocal(),
    new_submission_deadline: "",
  });
  // v52bm — per-field edits keyed by field name:
  //   { title: { new: "...", note: "..." }, ... }
  // Each entry becomes one field_amendments row when the admin publishes.
  const [edits, setEdits] = useState({});

  const setEdit = (key, patch) =>
    setEdits((prev) => ({ ...prev, [key]: { ...(prev[key] || {}), ...patch } }));

  const loadNotices = useCallback(() => {
    // Bucket A fix — pull drafts + published so admin can attach corrigenda
    // to unpublished notices too. Cache-buster defeats CloudFront caching.
    import("@/lib/api").then(({ adminApi }) =>
      adminApi.listAllNotices({ limit: 200, _: Date.now() })
        .then((d) => {
          setNotices(d.items || []);
          // v52bn — functional update so a ?notice= deep-link preselect is
          // never clobbered by the default pick resolving afterwards.
          if (d.items?.length) setPickedNoticeRef((prev) => prev || d.items[0].notice_ref);
        })
        .catch(() => {})
    );
  }, [pickedNoticeRef]);

  const loadCorrigenda = useCallback((ref) => {
    if (!ref) return;
    corrigendaApi.listAdmin(ref).then((d) => setItems(d.items || []))
      .catch((e) => showApiError(e));
  }, []);

  // v52bm — load full notice detail so Current column has every field.
  // Admin endpoint used so DRAFT notices (not yet published) also populate.
  const loadNoticeDetail = useCallback((ref) => {
    if (!ref) { setPickedNotice(null); return; }
    adminApi.getNoticeAdmin(ref)
      .then((n) => setPickedNotice(n))
      .catch(() => publicApi.getNotice(ref).then(setPickedNotice).catch(() => setPickedNotice(null)));
  }, []);

  useEffect(() => { loadNotices(); }, [loadNotices]);
  // v52bn — deep link from a live notice's Edit button:
  // /admin/e/corrigenda?notice=PMC-NOT-… preselects the notice and opens
  // the create form so the admin lands exactly where the change is made.
  useEffect(() => {
    const q = searchParams.get("notice");
    if (q) {
      setPickedNoticeRef(q);
      setShowNew(true);
    }
  }, [searchParams]);
  useEffect(() => {
    loadCorrigenda(pickedNoticeRef);
    loadNoticeDetail(pickedNoticeRef);
    setEdits({});
    // v52ca — switching notices clears the corrigenda filter so a stale
    // query from the previous notice can't hide rows on the new one.
    setCorrSearch("");
  }, [pickedNoticeRef, loadCorrigenda, loadNoticeDetail]);

  const publish = async () => {
    if (!draft.title || draft.title.trim().length < 3) {
      toast.error("Corrigendum title is required (min 3 characters)");
      return;
    }
    if (!draft.summary || draft.summary.trim().length < 8) {
      toast.error("Overall change description is required (min 8 characters)");
      return;
    }
    // v52bm — build field_amendments from per-row edits where the admin
    // entered a NEW value AND a per-field reason.
    const amendments = [];
    for (const f of NOTICE_FIELDS) {
      const e = edits[f.key];
      if (!e) continue;
      const newVal = (e.new ?? "").toString().trim();
      if (newVal === "") continue;
      const before = readField(pickedNotice, f);
      const beforeStr = before === undefined || before === null ? "" : String(before);
      if (newVal === beforeStr) continue;
      if (!e.note || e.note.trim().length < 3) {
        toast.error(`"${f.label}" was changed — add a reason (min 3 chars) next to it.`);
        return;
      }
      amendments.push({
        field: f.label,
        field_key: f.key,
        before: beforeStr,
        after: newVal,
        note: e.note.trim(),
      });
    }
    try {
      const payload = {
        title: draft.title.trim(),
        summary: draft.summary.trim(),
        effective_from: draft.corrigendum_date || undefined,
      };
      if (draft.new_submission_deadline) {
        payload.new_submission_deadline = draft.new_submission_deadline;
      }
      if (amendments.length) payload.field_amendments = amendments;
      const res = await corrigendaApi.publish(pickedNoticeRef, payload);
      toast.success(`Corrigendum No. ${res.corrigendum.corrigendum_no} published`);
      setShowNew(false);
      setDraft({ title: "", summary: "", corrigendum_date: todayLocal(),
                 new_submission_deadline: "" });
      setEdits({});
      // v52bn — round-trip: after publishing from the live-notice Edit flow,
      // land on the public notice page so the admin immediately sees the
      // corrigendum exactly as bidders will (fields + before/after table).
      navigate(`/notices/${pickedNoticeRef}`);
    } catch (err) { showApiError(err); }
  };

  // v52bz — shadcn Dialog state for the Withdraw-reason input (replaces
  // the native window.prompt() so QA can automate it + nicer UX).
  const [withdrawDialog, setWithdrawDialog] = useState({ open: false, cid: null, reason: "" });

  const withdraw = (cid) => setWithdrawDialog({ open: true, cid, reason: "" });

  const confirmWithdraw = async () => {
    const reason = (withdrawDialog.reason || "").trim();
    if (reason.length < 8) {
      return toast.error("Reason must be at least 8 characters — this is recorded in the audit log.");
    }
    try {
      await corrigendaApi.withdraw(pickedNoticeRef, withdrawDialog.cid, reason);
      // v52by — optimistic local flip so the row leaves the active list
      // immediately, without waiting for the refetch.
      setItems((cur) => cur.map((c) =>
        c.id === withdrawDialog.cid
          ? { ...c, is_active: false, withdrawn_at: new Date().toISOString(), withdrawn_reason: reason }
          : c));
      toast.success("Withdrawn — audit trail updated.");
      setWithdrawDialog({ open: false, cid: null, reason: "" });
      loadCorrigenda(pickedNoticeRef);
    } catch (err) { showApiError(err); }
  };

  // v52bn — attach a supporting document (revised BOQ, drawing, etc.) to a
  // corrigendum. Live notices route ALL document changes through here.
  const attachFile = async (cid, file) => {
    if (!file) return;
    setAttachingTo(cid);
    try {
      await corrigendaApi.attach(pickedNoticeRef, cid, file);
      toast.success(`Attached · ${file.name}`);
      loadCorrigenda(pickedNoticeRef);
    } catch (err) { showApiError(err); }
    finally { setAttachingTo(null); }
  };

  const corrQ = corrSearch.trim().toLowerCase();
  const visibleCorr = corrQ ? items.filter((c) =>
    (c.title || "").toLowerCase().includes(corrQ)
    || (c.summary || "").toLowerCase().includes(corrQ)
    || String(c.corrigendum_no || "").includes(corrQ)) : items;
  const activeCorr = visibleCorr.filter((c) => c.is_active);
  const withdrawnCorr = visibleCorr.filter((c) => !c.is_active);
  const activePager = useListPager(activeCorr, { testid: "corr-active-pager" });
  const withdrawnPager = useListPager(withdrawnCorr, { testid: "corr-withdrawn-pager" });

  return (
    <div data-testid="admin-corrigenda-panel">
      <div className="flex items-center justify-between mb-4 gap-3 flex-wrap">
        <div className="text-sm text-brand-navy/70">{t("panels.corrigenda.hint")}</div>
        <button type="button" onClick={() => setShowNew(!showNew)} data-testid="corr-new-toggle"
          disabled={!pickedNoticeRef}
          className="px-5 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40">
          {showNew ? t("panels.corrigenda.cancel") : t("panels.corrigenda.new")}
        </button>
      </div>

      <label className="block mb-4">
        <span className="pmc-label">{t("panels.corrigenda.notice_label")}<InfoDot tip="Pick the parent notice to which the corrigendum applies. All published corrigenda are attached to this notice's public page." /></span>
        <input value={noticeSearch} onChange={(e) => setNoticeSearch(e.target.value)}
          placeholder="Find a notice by reference or title to view/add its corrigenda…"
          aria-label="Pick a notice to see its corrigenda"
          data-testid="corr-search-notice"
          className="mt-1 mb-2 w-full px-4 py-2 border border-brand-navy/20 text-sm" />
        <select value={pickedNoticeRef} onChange={(e) => setPickedNoticeRef(e.target.value)}
                data-testid="corr-notice-picker"
                className="mt-1 w-full px-4 py-3 border border-brand-navy/20">
          {(() => {
            const q = noticeSearch.trim().toLowerCase();
            const list = q ? notices.filter((n) =>
              (n.notice_ref || "").toLowerCase().includes(q)
              || (n.title || "").toLowerCase().includes(q)) : notices;
            if (list.length === 0) return <option value="">No matches</option>;
            return list.map((n) => (
              <option key={n.id} value={n.notice_ref}>{n.notice_ref} — {n.title}</option>
            ));
          })()}
        </select>
      </label>

      {showNew && (
        <div className="border border-brand-navy-soft/40 bg-white p-6 mb-6 grid gap-4 md:grid-cols-2"
             data-testid="corr-new-form">
          <label className="col-span-2"><span className="pmc-label">{t("panels.corrigenda.title_label")} <span className="text-red-600">*</span><InfoDot tip="Short headline shown on the public notice page (e.g. 'Deadline extended by 7 days')." /></span>
            <input value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                   data-testid="corr-title"
                   className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label className="col-span-2"><span className="pmc-label">Overall change description <span className="text-red-600">*</span><InfoDot tip="Full text of the amendment. Rendered verbatim in the corrigendum PDF and notification email to registered bidders. Minimum 8 characters." /></span>
            <textarea rows={4} value={draft.summary}
                      onChange={(e) => setDraft({ ...draft, summary: e.target.value })}
                      data-testid="corr-summary"
                      placeholder="Why is this corrigendum being issued? What is changing and why?"
                      className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">Corrigendum date <span className="text-red-600">*</span><InfoDot tip="When this corrigendum takes effect. Defaults to now. Shown to vendors and recorded in the audit ledger." /></span>
            <input type="datetime-local" value={draft.corrigendum_date}
                   onChange={(e) => setDraft({ ...draft, corrigendum_date: e.target.value })}
                   data-testid="corr-date"
                   className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">New submission deadline (optional)<InfoDot tip="Only set if this corrigendum shifts the bid deadline. Overwrites the notice's current deadline on publish." /></span>
            <input type="datetime-local" value={draft.new_submission_deadline}
                   onChange={(e) => setDraft({ ...draft, new_submission_deadline: e.target.value })}
                   data-testid="corr-new-deadline"
                   className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>

          {/* v52bm — per-field current vs new table */}
          <div className="col-span-2 border-t border-brand-navy/10 pt-5">
            <div className="pmc-label mb-1">Change any field on the notice</div>
            <div className="text-xs text-brand-navy/60 mb-3">
              Leave the <b>New value</b> empty to keep the current value.
              If you type a new value, a <b>reason</b> is required for that row (recorded with the diff).
            </div>
            {!pickedNotice ? (
              <div className="text-sm text-brand-navy/50 italic">Loading notice fields…</div>
            ) : (
              <div className="border border-brand-navy/15 overflow-x-auto" data-testid="corr-fields-table">
                <table className="w-full text-sm">
                  <thead className="bg-brand-navy text-white text-xs uppercase tracking-widest">
                    <tr>
                      <th className="text-left px-3 py-2 w-[18%]">Field</th>
                      <th className="text-left px-3 py-2 w-[27%]">Current</th>
                      <th className="text-left px-3 py-2 w-[27%]">New value (optional)</th>
                      <th className="text-left px-3 py-2 w-[28%]">Reason for this change</th>
                    </tr>
                  </thead>
                  <tbody>
                    {NOTICE_FIELDS.map((f) => {
                      const current = readField(pickedNotice, f);
                      const row = edits[f.key] || {};
                      const InputEl = f.kind === "textarea" ? "textarea" : "input";
                      const inputType = f.kind === "datetime" ? "datetime-local"
                                       : f.kind === "number" ? "number" : "text";
                      return (
                        <tr key={f.key} className="border-t border-brand-navy/10 align-top"
                            data-testid={`corr-field-row-${f.key}`}>
                          <td className="px-3 py-2 font-semibold text-brand-navy">{f.label}</td>
                          <td className="px-3 py-2 bg-brand-pale/40 text-brand-navy/80 whitespace-pre-wrap break-words"
                              data-testid={`corr-field-current-${f.key}`}>
                            {fmtValue(current, f.kind)}
                          </td>
                          <td className="px-3 py-2">
                            {f.kind === "textarea" ? (
                              <textarea rows={3} value={row.new || ""}
                                        onChange={(e) => setEdit(f.key, { new: e.target.value })}
                                        data-testid={`corr-field-new-${f.key}`}
                                        className="w-full px-2 py-1 border border-brand-navy/20 text-sm" />
                            ) : (
                              <InputEl type={inputType} value={row.new || ""}
                                       onChange={(e) => setEdit(f.key, { new: e.target.value })}
                                       data-testid={`corr-field-new-${f.key}`}
                                       className="w-full px-2 py-1 border border-brand-navy/20 text-sm" />
                            )}
                          </td>
                          <td className="px-3 py-2">
                            <input value={row.note || ""}
                                   onChange={(e) => setEdit(f.key, { note: e.target.value })}
                                   data-testid={`corr-field-note-${f.key}`}
                                   placeholder={row.new ? "Required when changed" : "—"}
                                   disabled={!row.new}
                                   className="w-full px-2 py-1 border border-brand-navy/20 text-sm disabled:bg-slate-50" />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="col-span-2 flex justify-end">
            <button type="button" onClick={publish} data-testid="corr-publish"
              className="px-8 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90">
              {t("panels.corrigenda.publish")}
              <InfoDot tip="Publishes the corrigendum, emails all registered bidders and appends to the public notice page. Cannot be undone (only withdrawn with reason)." />
            </button>
          </div>
        </div>
      )}

      {(() => {
        const active = activeCorr;
        const withdrawn = withdrawnCorr;
        const renderRow = (c) => (
          <div key={c.id}
               className={`p-4 border-b border-brand-navy/10 ${c.is_active ? "" : "bg-slate-50"}`}
               data-testid={`corr-row-${c.corrigendum_no}`}>
            <div className="flex items-baseline gap-4 flex-wrap">
              <span className="font-mono text-xs text-brand-navy-soft">Corrigendum No. {c.corrigendum_no}</span>
              <span className={`text-sm font-semibold flex-1 ${c.is_active ? "text-brand-navy" : "text-brand-navy/50 line-through"}`}>
                {c.title}
              </span>
              <span className="text-xs text-brand-navy/50 font-mono"
                    data-testid={`corr-row-date-${c.corrigendum_no}`}>
                {(c.effective_from || c.published_at || "").slice(0, 16).replace("T", " ")}
              </span>
              {c.is_active ? (
                <button type="button" onClick={() => withdraw(c.id)}
                        data-testid={`corr-withdraw-${c.corrigendum_no}`}
                        className="text-[10px] uppercase tracking-widest px-2 py-1 border border-red-300 text-red-700 hover:bg-red-50">
                  {t("panels.corrigenda.withdraw")}
                </button>
              ) : (
                <span className="text-[10px] uppercase tracking-widest px-2 py-1 border border-slate-300 bg-white text-slate-500"
                      data-testid={`corr-status-withdrawn-${c.corrigendum_no}`}>
                  Withdrawn{c.withdrawn_at ? ` · ${c.withdrawn_at.slice(0, 10)}` : ""}
                </span>
              )}
            </div>
            <div className={`text-sm mt-2 whitespace-pre-line ${c.is_active ? "text-brand-navy/80" : "text-brand-navy/50"}`}>
              {c.summary}
            </div>
            {(c.field_amendments || []).length > 0 && (
              <div className="mt-3 border border-brand-navy/15 bg-white text-xs overflow-x-auto"
                   data-testid={`corr-row-amendments-${c.corrigendum_no}`}>
                <table className="w-full">
                  <thead className="bg-brand-pale/50 text-brand-navy">
                    <tr>
                      <th className="text-left px-2 py-1">Field</th>
                      <th className="text-left px-2 py-1">Before</th>
                      <th className="text-left px-2 py-1">After</th>
                      <th className="text-left px-2 py-1">Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {c.field_amendments.map((a, idx) => (
                      <tr key={idx} className="border-t border-brand-navy/10">
                        <td className="px-2 py-1 font-semibold">{a.field}</td>
                        <td className="px-2 py-1 bg-red-50/60 text-red-900 whitespace-pre-wrap break-words">{a.before || "—"}</td>
                        <td className="px-2 py-1 bg-emerald-50/60 text-emerald-900 whitespace-pre-wrap break-words">{a.after || "—"}</td>
                        <td className="px-2 py-1 text-brand-navy/70 whitespace-pre-wrap break-words">{a.note || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {/* v52bp — one-click download of the auto-generated one-page
                diff PDF (same artefact bidders received by email on publish). */}
            {c.is_active && (
              <div className="mt-3 flex items-center gap-2 flex-wrap">
                <a href={`/api/v1/notices/${pickedNoticeRef}/corrigenda/${c.id}/pdf`}
                   target="_blank" rel="noreferrer"
                   data-testid={`corr-pdf-admin-${c.corrigendum_no}`}
                   className="text-[10px] uppercase tracking-widest px-2 py-1 border border-brand-navy/30 text-brand-navy hover:bg-brand-navy hover:text-white">
                  📄 Download diff PDF
                </a>
                <span className="text-[10px] text-brand-navy/50">Same PDF that was emailed to active bidders</span>
              </div>
            )}
            {!c.is_active && c.withdrawn_reason && (
              <div className="text-xs text-slate-500 mt-2 italic"
                   data-testid={`corr-withdraw-reason-${c.corrigendum_no}`}>
                Withdrawal reason: {c.withdrawn_reason}
              </div>
            )}
            {c.is_active && c.new_submission_deadline && (
              <div className="text-xs text-amber-800 mt-2 bg-amber-50 border border-amber-200 px-3 py-1 inline-block">
                {t("panels.corrigenda.deadline_updated")} {c.new_submission_deadline?.slice(0, 16).replace("T", " ")}
              </div>
            )}
            {/* v52bn — corrigendum attachments: revised BOQs, drawings, etc.
                On live notices every document change arrives via these. */}
            {c.is_active && (
              <div className="mt-3 flex flex-wrap items-center gap-2"
                   data-testid={`corr-attach-area-${c.corrigendum_no}`}>
                {(c.attachments || []).map((a) => (
                  <a key={a.key || a.file_name} href={a.url} target="_blank" rel="noreferrer"
                     className="text-[11px] px-2 py-1 border border-brand-navy/25 text-brand-navy hover:bg-brand-navy hover:text-white"
                     data-testid={`corr-attach-file-${c.corrigendum_no}-${a.file_name}`}>
                    📎 {a.file_name}
                  </a>
                ))}
                <label className="text-[10px] uppercase tracking-widest px-2 py-1 border border-brand-navy/30 text-brand-navy hover:bg-brand-navy hover:text-white cursor-pointer"
                       data-testid={`corr-attach-btn-${c.corrigendum_no}`}>
                  {attachingTo === c.id ? "Uploading…" : "+ Attach document"}
                  <input type="file" className="hidden"
                         accept=".pdf,.doc,.docx,.xls,.xlsx,.dwg,.jpg,.png,.zip"
                         disabled={attachingTo === c.id}
                         onChange={(e) => { attachFile(c.id, e.target.files?.[0]); e.target.value = ""; }}
                         data-testid={`corr-attach-input-${c.corrigendum_no}`} />
                </label>
              </div>
            )}
          </div>
        );
        return (
          <>
            <input value={corrSearch} onChange={(e) => setCorrSearch(e.target.value)}
              aria-label="Search within this notice's corrigenda"
              placeholder="Filter THIS notice's corrigenda by number, title or summary…"
              data-testid="corr-search-within"
              className="w-full mb-1 px-4 py-2 border border-brand-navy/20 text-sm bg-white" />
            {/* v52ca — every keystroke must produce visible feedback. Without
                this line, filtering a notice with 0 corrigenda (or a query
                with no hits) looked exactly like a dead search box. */}
            {items.length === 0 ? (
              <div className="text-xs text-brand-navy/50 italic mb-3"
                   data-testid="corr-search-empty-hint">
                This notice has no corrigenda yet — publish the first one via “New corrigendum” above.
              </div>
            ) : corrQ ? (
              <div className="text-xs mb-3" data-testid="corr-search-feedback">
                {visibleCorr.length === 0 ? (
                  <span className="text-amber-700">No corrigenda match “{corrSearch}” — try the corrigendum number, a title word, or text from the change description.</span>
                ) : (
                  <span className="text-brand-navy/60">{visibleCorr.length} of {items.length} corrigenda match “{corrSearch}”.</span>
                )}
              </div>
            ) : <div className="mb-2" />}
            <div className="pmc-label mb-2" data-testid="corr-section-active">
              Active corrigenda ({active.length})
            </div>
            <div className="border border-brand-navy/10 bg-white">
              {active.length === 0 ? (
                <div className="p-6 text-brand-navy/50 text-sm">
                  No active corrigenda for this notice.
                </div>
              ) : (
                activePager.paged.map(renderRow)
              )}
              {activePager.controls}
            </div>
            {withdrawn.length > 0 && (
              <>
                <div className="pmc-label mt-6 mb-2 text-brand-navy/60" data-testid="corr-section-withdrawn">
                  Withdrawn (historical) — {withdrawn.length}
                </div>
                <div className="border border-slate-200 bg-slate-50/50">
                  {withdrawnPager.paged.map(renderRow)}
                  {withdrawnPager.controls}
                </div>
              </>
            )}
          </>
        );
      })()}
      <Dialog open={withdrawDialog.open}
              onOpenChange={(o) => !o && setWithdrawDialog({ open: false, cid: null, reason: "" })}>
        <DialogContent data-testid="corr-withdraw-dialog">
          <DialogHeader>
            <DialogTitle>Withdraw corrigendum</DialogTitle>
          </DialogHeader>
          <div className="text-sm text-brand-navy/70 mb-3">
            Enter the reason for withdrawal (minimum 8 characters). It is stamped into the audit trail
            and displayed to bidders alongside the withdrawn amendment.
          </div>
          <textarea value={withdrawDialog.reason}
                    onChange={(e) => setWithdrawDialog((p) => ({ ...p, reason: e.target.value }))}
                    data-testid="corr-withdraw-reason-input"
                    rows={4}
                    className="w-full border border-brand-navy/20 px-3 py-2 text-sm"
                    placeholder="e.g. New compliance clause supersedes the original amendment…" />
          <div className="text-[11px] text-brand-navy/50 mt-1">
            {withdrawDialog.reason.trim().length}/8 characters
          </div>
          <DialogFooter>
            <button type="button"
                    onClick={() => setWithdrawDialog({ open: false, cid: null, reason: "" })}
                    className="px-4 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/30">
              Cancel
            </button>
            <button type="button" onClick={confirmWithdraw}
                    disabled={withdrawDialog.reason.trim().length < 8}
                    data-testid="corr-withdraw-confirm"
                    className="px-4 py-2 text-[11px] uppercase tracking-widest bg-red-600 text-white disabled:opacity-40">
              Confirm withdraw
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

    </div>
  );
}
