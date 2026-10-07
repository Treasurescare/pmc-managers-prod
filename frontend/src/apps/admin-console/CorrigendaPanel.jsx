import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { corrigendaApi, formatApiError, showApiError} from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import { InfoDot } from "@/components/InfoDot";
import { useListPager } from "@/components/ListPager";

/** Wave 39 — Corrigendum publisher. Attached under Notices admin flow. */
export default function CorrigendaPanel() {
  const { t } = useI18n();
  const [notices, setNotices] = useState([]);
  const [pickedNoticeRef, setPickedNoticeRef] = useState("");
  const [items, setItems] = useState([]);
  const [showNew, setShowNew] = useState(false);
  const [noticeSearch, setNoticeSearch] = useState("");
  const [corrSearch, setCorrSearch] = useState("");
  const [draft, setDraft] = useState({
    title: "", summary: "", effective_from: "", new_submission_deadline: "",
    extend_deadline_days: "", field_amendments: [],
  });
  // v51ad — admin can add row-level field amendments (before/after diff shown
  // to vendors on the public corrigendum page).
  const addAmendment = () => setDraft((d) => ({ ...d,
    field_amendments: [...(d.field_amendments || []), { field: "", before: "", after: "" }] }));
  const updateAmendment = (i, patch) => setDraft((d) => ({ ...d,
    field_amendments: d.field_amendments.map((a, j) => j === i ? { ...a, ...patch } : a) }));
  const removeAmendment = (i) => setDraft((d) => ({ ...d,
    field_amendments: d.field_amendments.filter((_, j) => j !== i) }));

  const loadNotices = useCallback(() => {
    // Bucket A fix — pull drafts + published so admin can attach corrigenda
    // to unpublished notices too. Cache-buster defeats CloudFront caching.
    import("@/lib/api").then(({ adminApi }) =>
      adminApi.listAllNotices({ limit: 200, _: Date.now() })
        .then((d) => {
          setNotices(d.items || []);
          if (!pickedNoticeRef && d.items?.length) setPickedNoticeRef(d.items[0].notice_ref);
        })
        .catch(() => {})
    );
  }, [pickedNoticeRef]);

  const loadCorrigenda = useCallback((ref) => {
    if (!ref) return;
    corrigendaApi.listAdmin(ref).then((d) => setItems(d.items || []))
      .catch((e) => showApiError(e));
  }, []);

  useEffect(() => { loadNotices(); }, [loadNotices]);
  useEffect(() => { loadCorrigenda(pickedNoticeRef); }, [pickedNoticeRef, loadCorrigenda]);

  const publish = async () => {
    if (!draft.title || !draft.summary) {
      toast.error(t("panels.corrigenda.title_summary_required"));
      return;
    }
    try {
      const payload = { ...draft };
      if (!payload.effective_from) delete payload.effective_from;
      if (!payload.new_submission_deadline) delete payload.new_submission_deadline;
      if (payload.extend_deadline_days === "" || payload.extend_deadline_days == null) {
        delete payload.extend_deadline_days;
      } else {
        payload.extend_deadline_days = Number(payload.extend_deadline_days);
      }
      payload.field_amendments = (payload.field_amendments || [])
        .filter((a) => (a.field || "").trim() && ((a.before || a.after || "").toString().trim()));
      if (payload.field_amendments.length === 0) delete payload.field_amendments;
      const res = await corrigendaApi.publish(pickedNoticeRef, payload);
      toast.success(`Corrigendum No. ${res.corrigendum.corrigendum_no} published`);
      setShowNew(false);
      setDraft({ title: "", summary: "", effective_from: "", new_submission_deadline: "",
                 extend_deadline_days: "", field_amendments: [] });
      loadCorrigenda(pickedNoticeRef);
    } catch (err) { showApiError(err); }
  };

  const withdraw = async (cid) => {
    // Bug (from PDF v3 observation) — require reason on withdraw, log to audit.
    const reason = window.prompt(
      "Reason for withdrawing this corrigendum? (required, min 8 chars — will be logged to audit)"
    );
    if (!reason) return;
    if (reason.trim().length < 8) {
      return toast.error("Reason must be at least 8 characters — this is recorded in the audit log.");
    }
    try {
      await corrigendaApi.withdraw(pickedNoticeRef, cid, reason.trim());
      toast.success("Withdrawn — audit trail updated.");
      loadCorrigenda(pickedNoticeRef);
    } catch (err) { showApiError(err); }
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
          placeholder="Search notices by ref or title…"
          data-testid="corr-notice-search"
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
          <label className="col-span-2"><span className="pmc-label">{t("panels.corrigenda.title_label")}<InfoDot tip="Short headline shown on the public notice page (e.g. 'Deadline extended by 7 days')." /></span>
            <input value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                   data-testid="corr-title"
                   className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label className="col-span-2"><span className="pmc-label">{t("panels.corrigenda.summary_label")}<InfoDot tip="Full text of the amendment. Rendered verbatim in the corrigendum PDF and notification email to registered bidders." /></span>
            <textarea rows={5} value={draft.summary}
                      onChange={(e) => setDraft({ ...draft, summary: e.target.value })}
                      data-testid="corr-summary"
                      className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">{t("panels.corrigenda.effective_from")}<InfoDot tip="Optional. When this amendment takes effect. Leave blank for 'immediately on publish'." /></span>
            <input type="datetime-local" value={draft.effective_from}
                   onChange={(e) => setDraft({ ...draft, effective_from: e.target.value })}
                   data-testid="corr-effective"
                   className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">{t("panels.corrigenda.new_deadline")}<InfoDot tip="Optional. If this corrigendum extends or shortens the bid deadline, set the new cut-off here. Overwrites the notice's deadline." /></span>
            <input type="datetime-local" value={draft.new_submission_deadline}
                   onChange={(e) => setDraft({ ...draft, new_submission_deadline: e.target.value })}
                   data-testid="corr-new-deadline"
                   className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">Extend deadline by (days)<InfoDot tip="Optional shortcut. If set and the field above is blank, the backend adds N days to the notice's current submission deadline." /></span>
            <input type="number" min="0" max="365" value={draft.extend_deadline_days}
                   onChange={(e) => setDraft({ ...draft, extend_deadline_days: e.target.value })}
                   data-testid="corr-extend-days"
                   placeholder="e.g. 7"
                   className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <div className="col-span-2 border-t border-brand-navy/10 pt-4">
            <div className="pmc-label mb-2">Field amendments (optional, versioned diff)
              <InfoDot tip="Show vendors exactly which tender fields changed. Each row: pick the field (BOQ item, eligibility clause, budget, etc.), paste the before and after values. Vendors see a versioned diff on the public corrigendum page." /></div>
            {(draft.field_amendments || []).map((a, i) => (
              <div key={i} className="grid gap-2 md:grid-cols-[1fr_2fr_2fr_auto] mb-2"
                   data-testid={`corr-amend-row-${i}`}>
                <input value={a.field} onChange={(e) => updateAmendment(i, { field: e.target.value })}
                       placeholder="Field (BOQ item 3 / eligibility / budget)"
                       data-testid={`corr-amend-field-${i}`}
                       className="px-3 py-2 border border-brand-navy/15 text-sm" />
                <input value={a.before} onChange={(e) => updateAmendment(i, { before: e.target.value })}
                       placeholder="Before"
                       data-testid={`corr-amend-before-${i}`}
                       className="px-3 py-2 border border-brand-navy/15 text-sm bg-red-50/50" />
                <input value={a.after}  onChange={(e) => updateAmendment(i, { after: e.target.value })}
                       placeholder="After"
                       data-testid={`corr-amend-after-${i}`}
                       className="px-3 py-2 border border-brand-navy/15 text-sm bg-emerald-50/50" />
                <button type="button" onClick={() => removeAmendment(i)}
                        data-testid={`corr-amend-remove-${i}`}
                        className="px-2 py-1 text-[10px] uppercase tracking-widest border border-red-300 text-red-700 hover:bg-red-50">✕</button>
              </div>
            ))}
            <button type="button" onClick={addAmendment}
                    data-testid="corr-amend-add"
                    className="mt-1 px-3 py-1.5 text-[10px] uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-navy/5">
              + Add field amendment
            </button>
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
              <span className="text-xs text-brand-navy/50 font-mono">{c.published_at?.slice(0, 10)}</span>
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
          </div>
        );
        return (
          <>
            <input value={corrSearch} onChange={(e) => setCorrSearch(e.target.value)}
              placeholder="Search corrigenda by number, title or summary…"
              data-testid="corr-search"
              className="w-full mb-3 px-4 py-2 border border-brand-navy/20 text-sm bg-white" />
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
    </div>
  );
}
