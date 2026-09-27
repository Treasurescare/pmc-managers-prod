import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { adminApi, api, formatApiError, showApiError} from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import { InfoDot } from "@/components/InfoDot";
import { useListPager } from "@/components/ListPager";

export default function RegistrationsPanel() {
  const { t } = useI18n();
  const [items, setItems] = useState([]);
  const [status, setStatus] = useState("submitted");
  const [selected, setSelected] = useState(null);
  const [notes, setNotes] = useState("");
  const [sendingReminders, setSendingReminders] = useState(false);
  const [deciding, setDeciding] = useState(false);
  const [search, setSearch] = useState("");

  const load = useCallback(() => {
    // Bug #15 fix — when the reviewer switches status tab, clear the
    // currently-selected row so the previous company's details don't
    // linger over the new tab's rows.
    setSelected(null);
    setNotes("");
    adminApi.listRegistrations({ status })
      .then(setItems)
      .catch((e) => showApiError(e));
  }, [status]);
  useEffect(() => { load(); }, [load]);

  const sendReminders = async () => {
    setSendingReminders(true);
    try {
      const r = await api.post("/api/v1/registrations/admin/send-reminders");
      // Bug #46 — clearer message when zero stale drafts
      const { reminded = 0, checked = 0 } = r.data || {};
      if (checked === 0) {
        toast.info(t("panels.registrations.no_stale"));
      } else if (reminded === 0) {
        toast.warning(t("panels.registrations.stale_checked_none").replace("{checked}", checked));
      } else {
        toast.success(
          t("panels.registrations.stale_reminded")
            .replace("{reminded}", reminded).replace("{checked}", checked)
        );
      }
    } catch (err) {
      showApiError(err);
    } finally {
      setSendingReminders(false);
    }
  };

  const decide = async (action) => {
    if (!selected || deciding) return;
    if ((action === "reject" || action === "clarify") && !notes.trim()) {
      toast.error(t("panels.registrations.notes_required"));
      return;
    }
    setDeciding(true);
    try {
      const r = await adminApi.decideRegistration(selected.id, action, notes || null);
      // Bug #46 — proper verb (avoids "clarify recorded" typo)
      const verb = action === "clarify" ? "clarification"
                 : action === "approve"  ? "approval"
                 : action === "reject"   ? "rejection" : action;
      toast.success(`${verb.charAt(0).toUpperCase() + verb.slice(1)} recorded`);
      setSelected(null); setNotes("");
      // Bucket A fix — auto-switch the filter to the new status so the
      // reviewer sees where the record went. Previously the row simply
      // disappeared from the "submitted" tab and the user thought the
      // action didn't take effect.
      const nextStatus = r?.status
        || (action === "approve" ? "approved"
        : action === "reject" ? "rejected"
        : action === "clarify" ? "needs_clarification" : status);
      if (nextStatus !== status) setStatus(nextStatus);
      else load();
    } catch (err) {
      showApiError(err);
    } finally {
      setDeciding(false);
    }
  };

  const STATUS_LABELS = {
    submitted: t("panels.registrations.filter_submitted"),
    under_review: t("panels.registrations.filter_under_review"),
    needs_clarification: t("panels.registrations.filter_needs_clarification"),
    approved: t("panels.registrations.filter_approved"),
    rejected: t("panels.registrations.filter_rejected"),
    draft: t("panels.registrations.filter_draft"),
  };

  const q = search.trim().toLowerCase();
  const filtered = q
    ? items.filter((r) =>
        (r.company_name || "").toLowerCase().includes(q)
        || (r.email || "").toLowerCase().includes(q)
        || (r.registration_number || "").toLowerCase().includes(q))
    : items;
  const { paged, controls } = useListPager(filtered, { testid: "reg-pager" });

  return (
    <div className="grid gap-6 lg:grid-cols-[5fr_7fr]" data-testid="admin-registrations-panel">
      <div>
        <div className="flex items-center gap-2 mb-3 flex-wrap">
          {Object.keys(STATUS_LABELS).map((s) => (
            <button key={s} onClick={() => setStatus(s)} data-testid={`reg-filter-${s}`}
              className={"px-3 py-1.5 text-[10px] uppercase tracking-widest border " +
                (status === s ? "bg-brand-navy text-white border-brand-navy" : "bg-white text-brand-navy/70 border-brand-navy/20")}>{STATUS_LABELS[s]}</button>
          ))}
          <button type="button" onClick={sendReminders} disabled={sendingReminders}
            data-testid="reg-send-reminders"
            className="ml-auto px-3 py-1.5 text-[10px] uppercase tracking-widest border border-brand-navy-soft/50 text-brand-navy-soft hover:bg-brand-navy-soft hover:text-white transition-colors disabled:opacity-50"
            title={t("panels.registrations.nudge_tooltip")}>
            {sendingReminders ? t("panels.registrations.nudge_sending") : t("panels.registrations.nudge_stale")}
          </button>
        </div>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by company, email or registration number…"
          data-testid="reg-search"
          className="w-full px-4 py-2 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white text-sm mb-3"
        />
        <div className="border border-brand-navy/10 bg-white">
          {filtered.length === 0 ? (
            <div className="p-6 text-brand-navy/50 text-sm">{q ? "No matches" : t("panels.registrations.empty")}</div>
          ) : paged.map((r) => (
            <button key={r.id} type="button" onClick={() => { setSelected(r); setNotes(""); }}
              data-testid={`reg-row-${r.id}`}
              className={"w-full text-left p-4 border-b border-brand-navy/10 hover:bg-brand-navy/5 " + (selected?.id === r.id ? "bg-brand-navy/5" : "")}>
              <div className="text-sm font-semibold text-brand-navy">{r.company_name || t("panels.registrations.no_company")}</div>
              <div className="text-xs text-brand-navy/60 mt-1 font-mono">{r.email}</div>
              <div className="text-[10px] uppercase tracking-widest text-brand-navy-soft mt-1 flex items-center gap-2">
                <span>{STATUS_LABELS[r.status] || r.status}</span>
                {(r.submitted_at || r.created_at) && (
                  <span className="text-brand-navy/50 normal-case tracking-normal">
                    · {new Date(r.submitted_at || r.created_at).toLocaleDateString()}
                  </span>
                )}
              </div>
            </button>
          ))}
          {controls}
        </div>
      </div>
      <div>
        {selected ? (
          <div className="border border-brand-navy/10 bg-white p-6" data-testid="reg-detail">
            <div className="pmc-label">{t("panels.registrations.company")}</div>
            <h3 className="font-display text-2xl text-brand-navy mt-1">{selected.company_name || t("panels.registrations.no_company")}</h3>
            <div className="text-sm text-brand-navy/70 mt-2">{selected.email} · {selected.country}</div>
            <dl className="mt-6 grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
              <div><dt className="pmc-label">{t("panels.registrations.reg_number")}</dt><dd className="text-brand-navy">{selected.registration_number || "—"}</dd></div>
              <div><dt className="pmc-label">{t("panels.registrations.entity_type")}</dt><dd className="text-brand-navy">{selected.legal_entity_type || "—"}</dd></div>
              <div><dt className="pmc-label">{t("panels.registrations.primary_sector")}</dt><dd className="text-brand-navy">{selected.primary_sector || "—"}</dd></div>
              <div><dt className="pmc-label">{t("panels.registrations.kz_licenses")}</dt><dd className="text-brand-navy">{(selected.kz_licenses || []).join(", ") || "—"}</dd></div>
              <div className="col-span-2"><dt className="pmc-label">{t("panels.registrations.business_desc")}</dt><dd className="text-brand-navy whitespace-pre-wrap">{selected.business_description || "—"}</dd></div>
            </dl>
            {selected.document_slots && Object.keys(selected.document_slots).length > 0 && (
              <div className="mt-6 border-t border-brand-navy/10 pt-4" data-testid="reg-documents">
                <div className="pmc-label mb-2">{t("panels.registrations.uploaded_docs_prefix")} ({Object.keys(selected.document_slots).length})</div>
                <ul className="grid gap-2 md:grid-cols-2">
                  {Object.entries(selected.document_slots).map(([slot, meta]) => (
                    <li key={slot} className="border border-brand-navy/10 p-2 text-xs bg-slate-50"
                        data-testid={`reg-doc-${slot}`}>
                      <div className="font-semibold text-brand-navy">{slot.replace(/_/g, " ")}</div>
                      <div className="text-brand-navy/60 mt-0.5 truncate">{meta.file_name}</div>
                      <div className="mt-1 flex gap-1">
                        <a href={`${process.env.REACT_APP_BACKEND_URL}${meta.url}`} target="_blank" rel="noreferrer"
                           className="text-[10px] uppercase tracking-widest px-2 py-1 border border-brand-navy/20 text-brand-navy hover:bg-white">{t("panels.registrations.view")}</a>
                        <a href={`${process.env.REACT_APP_BACKEND_URL}${meta.url}`} download={meta.file_name}
                           className="text-[10px] uppercase tracking-widest px-2 py-1 border border-brand-navy/20 text-brand-navy hover:bg-white">{t("panels.registrations.download")}</a>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <div className="mt-6">
              <label className="pmc-label">{t("panels.registrations.reviewer_notes")}<InfoDot tip="Notes are recorded in the audit log and emailed to the vendor when action = Clarify or Reject. Required for those two actions." /></label>
              <textarea rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} data-testid="reg-notes"
                className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy" />
            </div>
            <div className="mt-4 flex gap-2 flex-wrap">
              {(selected.status === "approved" || selected.status === "rejected") ? (
                <div className={"w-full flex items-center justify-between gap-3 px-4 py-3 border " +
                                (selected.status === "approved"
                                  ? "border-emerald-500/40 bg-emerald-50 text-emerald-800"
                                  : "border-red-500/40 bg-red-50 text-red-700")}
                     data-testid={`reg-status-banner-${selected.status}`}>
                  <div>
                    <div className="text-[10px] font-mono uppercase tracking-widest">
                      Registration {selected.status}
                    </div>
                    <div className="text-sm mt-0.5">
                      {selected.status === "approved"
                        ? `Approved on ${selected.reviewed_at ? new Date(selected.reviewed_at).toLocaleDateString() : "—"}${selected.vendor_ref ? ` · vendor ${selected.vendor_ref}` : ""}. No further action required.`
                        : `Rejected on ${selected.reviewed_at ? new Date(selected.reviewed_at).toLocaleDateString() : "—"}. Vendor cannot re-apply with the same email for 90 days.`}
                    </div>
                    {selected.reviewer_notes && (
                      <div className="mt-2 text-xs whitespace-pre-wrap">Notes: {selected.reviewer_notes}</div>
                    )}
                  </div>
                </div>
              ) : (
                <>
              <button type="button" onClick={() => decide("approve")} disabled={deciding} data-testid="reg-approve" className="px-6 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90 disabled:opacity-50 disabled:cursor-not-allowed">
                {deciding ? t("panels.registrations.approve_working") : t("panels.registrations.approve")}
                <InfoDot tip="Grants vendor account access. Notes optional. Vendor receives welcome email with password-set link." />
              </button>
              <button type="button" onClick={() => decide("clarify")} disabled={deciding} data-testid="reg-clarify" className="px-6 py-3 text-[12px] font-semibold uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5 disabled:opacity-50 disabled:cursor-not-allowed">
                {t("panels.registrations.clarify")}
                <InfoDot tip="Send back for corrections. Notes are mandatory and are emailed verbatim to the vendor's registration email." />
              </button>
              <button type="button" onClick={() => decide("reject")} disabled={deciding} data-testid="reg-reject" className="px-6 py-3 text-[12px] font-semibold uppercase tracking-widest border border-red-500/50 text-red-600 hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed">
                {t("panels.registrations.reject")}
                <InfoDot tip="Terminal decision. Notes required and recorded in the audit log. Vendor cannot re-apply with the same email for 90 days." />
              </button>
                </>
              )}
            </div>
          </div>
        ) : (
          <div className="border border-dashed border-brand-navy/20 bg-white p-14 text-center text-brand-navy/50">
            {t("panels.registrations.select_prompt")}
          </div>
        )}
      </div>
    </div>
  );
}
