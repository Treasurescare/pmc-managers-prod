import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { corrigendaApi, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";

/** Wave 39 — Corrigendum publisher. Attached under Notices admin flow. */
export default function CorrigendaPanel() {
  const { t } = useI18n();
  const [notices, setNotices] = useState([]);
  const [pickedNoticeRef, setPickedNoticeRef] = useState("");
  const [items, setItems] = useState([]);
  const [showNew, setShowNew] = useState(false);
  const [draft, setDraft] = useState({
    title: "", summary: "", effective_from: "", new_submission_deadline: "",
  });

  const loadNotices = useCallback(() => {
    fetch(`${process.env.REACT_APP_BACKEND_URL}/api/v1/notices?limit=200`)
      .then((r) => r.json())
      .then((d) => {
        setNotices(d.items || []);
        if (!pickedNoticeRef && d.items?.length) setPickedNoticeRef(d.items[0].notice_ref);
      })
      .catch(() => {});
  }, [pickedNoticeRef]);

  const loadCorrigenda = useCallback((ref) => {
    if (!ref) return;
    corrigendaApi.listAdmin(ref).then((d) => setItems(d.items || []))
      .catch((e) => toast.error(formatApiError(e)));
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
      const res = await corrigendaApi.publish(pickedNoticeRef, payload);
      toast.success(`Corrigendum No. ${res.corrigendum.corrigendum_no} published`);
      setShowNew(false);
      setDraft({ title: "", summary: "", effective_from: "", new_submission_deadline: "" });
      loadCorrigenda(pickedNoticeRef);
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const withdraw = async (cid) => {
    if (!window.confirm(t("panels.corrigenda.withdraw_confirm"))) return;
    try {
      await corrigendaApi.withdraw(pickedNoticeRef, cid);
      toast.success("Withdrawn");
      loadCorrigenda(pickedNoticeRef);
    } catch (err) { toast.error(formatApiError(err)); }
  };

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
        <span className="pmc-label">{t("panels.corrigenda.notice_label")}</span>
        <select value={pickedNoticeRef} onChange={(e) => setPickedNoticeRef(e.target.value)}
                data-testid="corr-notice-picker"
                className="mt-1 w-full px-4 py-3 border border-brand-navy/20">
          {notices.map((n) => (
            <option key={n.id} value={n.notice_ref}>{n.notice_ref} — {n.title}</option>
          ))}
        </select>
      </label>

      {showNew && (
        <div className="border border-brand-navy-soft/40 bg-white p-6 mb-6 grid gap-4 md:grid-cols-2"
             data-testid="corr-new-form">
          <label className="col-span-2"><span className="pmc-label">{t("panels.corrigenda.title_label")}</span>
            <input value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                   data-testid="corr-title"
                   className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label className="col-span-2"><span className="pmc-label">{t("panels.corrigenda.summary_label")}</span>
            <textarea rows={5} value={draft.summary}
                      onChange={(e) => setDraft({ ...draft, summary: e.target.value })}
                      data-testid="corr-summary"
                      className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">{t("panels.corrigenda.effective_from")}</span>
            <input type="datetime-local" value={draft.effective_from}
                   onChange={(e) => setDraft({ ...draft, effective_from: e.target.value })}
                   data-testid="corr-effective"
                   className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">{t("panels.corrigenda.new_deadline")}</span>
            <input type="datetime-local" value={draft.new_submission_deadline}
                   onChange={(e) => setDraft({ ...draft, new_submission_deadline: e.target.value })}
                   data-testid="corr-new-deadline"
                   className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <div className="col-span-2 flex justify-end">
            <button type="button" onClick={publish} data-testid="corr-publish"
              className="px-8 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90">
              {t("panels.corrigenda.publish")}
            </button>
          </div>
        </div>
      )}

      <div className="border border-brand-navy/10 bg-white">
        {items.length === 0 && (
          <div className="p-6 text-brand-navy/50 text-sm">{t("panels.corrigenda.empty")}</div>
        )}
        {items.map((c) => (
          <div key={c.id}
               className={`p-4 border-b border-brand-navy/10 ${c.is_active ? "" : "opacity-50 line-through"}`}
               data-testid={`corr-row-${c.corrigendum_no}`}>
            <div className="flex items-baseline gap-4 flex-wrap">
              <span className="font-mono text-xs text-brand-navy-soft">Corrigendum No. {c.corrigendum_no}</span>
              <span className="text-sm font-semibold text-brand-navy flex-1">{c.title}</span>
              <span className="text-xs text-brand-navy/50 font-mono">{c.published_at?.slice(0, 10)}</span>
              {c.is_active && (
                <button type="button" onClick={() => withdraw(c.id)}
                        data-testid={`corr-withdraw-${c.corrigendum_no}`}
                        className="text-[10px] uppercase tracking-widest px-2 py-1 border border-red-300 text-red-700 hover:bg-red-50">
                  {t("panels.corrigenda.withdraw")}
                </button>
              )}
            </div>
            <div className="text-sm text-brand-navy/80 mt-2 whitespace-pre-line">{c.summary}</div>
            {c.new_submission_deadline && (
              <div className="text-xs text-amber-800 mt-2 bg-amber-50 border border-amber-200 px-3 py-1 inline-block">
                {t("panels.corrigenda.deadline_updated")} {c.new_submission_deadline?.slice(0, 16).replace("T", " ")}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
