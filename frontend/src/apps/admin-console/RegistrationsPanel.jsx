import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { adminApi, api, formatApiError } from "@/lib/api";

export default function RegistrationsPanel() {
  const [items, setItems] = useState([]);
  const [status, setStatus] = useState("submitted");
  const [selected, setSelected] = useState(null);
  const [notes, setNotes] = useState("");
  const [sendingReminders, setSendingReminders] = useState(false);

  const load = useCallback(() => {
    adminApi.listRegistrations({ status })
      .then(setItems)
      .catch((e) => toast.error(formatApiError(e)));
  }, [status]);
  useEffect(() => { load(); }, [load]);

  const sendReminders = async () => {
    setSendingReminders(true);
    try {
      const r = await api.post("/api/v1/registrations/admin/send-reminders");
      toast.success(`Reminders sent to ${r.data.reminded} of ${r.data.checked} stale drafts`);
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setSendingReminders(false);
    }
  };

  const decide = async (action) => {
    if (!selected) return;
    if ((action === "reject" || action === "clarify") && !notes.trim()) {
      toast.error("Notes required for this action");
      return;
    }
    try {
      await adminApi.decideRegistration(selected.id, action, notes || null);
      toast.success(`${action} recorded`);
      setSelected(null); setNotes(""); load();
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[5fr_7fr]" data-testid="admin-registrations-panel">
      <div>
        <div className="flex items-center gap-2 mb-3 flex-wrap">
          {["submitted", "under_review", "needs_clarification", "approved", "rejected", "draft"].map((s) => (
            <button key={s} onClick={() => setStatus(s)} data-testid={`reg-filter-${s}`}
              className={"px-3 py-1.5 text-[10px] uppercase tracking-widest border " +
                (status === s ? "bg-brand-navy text-white border-brand-navy" : "bg-white text-brand-navy/70 border-brand-navy/20")}>{s}</button>
          ))}
          <button type="button" onClick={sendReminders} disabled={sendingReminders}
            data-testid="reg-send-reminders"
            className="ml-auto px-3 py-1.5 text-[10px] uppercase tracking-widest border border-brand-navy-soft/50 text-brand-navy-soft hover:bg-brand-navy-soft hover:text-white transition-colors disabled:opacity-50"
            title="Email everyone whose draft is more than 7 days old">
            {sendingReminders ? "Sending…" : "Nudge stale drafts"}
          </button>
        </div>
        <div className="border border-brand-navy/10 bg-white">
          {items.length === 0 && <div className="p-6 text-brand-navy/50 text-sm">No registrations at this status.</div>}
          {items.map((r) => (
            <button key={r.id} type="button" onClick={() => { setSelected(r); setNotes(""); }}
              data-testid={`reg-row-${r.id}`}
              className={"w-full text-left p-4 border-b border-brand-navy/10 hover:bg-brand-navy/5 " + (selected?.id === r.id ? "bg-brand-navy/5" : "")}>
              <div className="text-sm font-semibold text-brand-navy">{r.company_name || "(no company)"}</div>
              <div className="text-xs text-brand-navy/60 mt-1 font-mono">{r.email}</div>
              <div className="text-[10px] uppercase tracking-widest text-brand-navy-soft mt-1">{r.status}</div>
            </button>
          ))}
        </div>
      </div>
      <div>
        {selected ? (
          <div className="border border-brand-navy/10 bg-white p-6" data-testid="reg-detail">
            <div className="pmc-label">Company</div>
            <h3 className="font-display text-2xl text-brand-navy mt-1">{selected.company_name || "(no company)"}</h3>
            <div className="text-sm text-brand-navy/70 mt-2">{selected.email} · {selected.country}</div>
            <dl className="mt-6 grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
              <div><dt className="pmc-label">Reg. number</dt><dd className="text-brand-navy">{selected.registration_number || "—"}</dd></div>
              <div><dt className="pmc-label">Entity type</dt><dd className="text-brand-navy">{selected.legal_entity_type || "—"}</dd></div>
              <div><dt className="pmc-label">Primary sector</dt><dd className="text-brand-navy">{selected.primary_sector || "—"}</dd></div>
              <div><dt className="pmc-label">KZ licenses</dt><dd className="text-brand-navy">{(selected.kz_licenses || []).join(", ") || "—"}</dd></div>
              <div className="col-span-2"><dt className="pmc-label">Business description</dt><dd className="text-brand-navy whitespace-pre-wrap">{selected.business_description || "—"}</dd></div>
            </dl>
            {selected.document_slots && Object.keys(selected.document_slots).length > 0 && (
              <div className="mt-6 border-t border-brand-navy/10 pt-4" data-testid="reg-documents">
                <div className="pmc-label mb-2">Uploaded documents ({Object.keys(selected.document_slots).length})</div>
                <ul className="grid gap-2 md:grid-cols-2">
                  {Object.entries(selected.document_slots).map(([slot, meta]) => (
                    <li key={slot} className="border border-brand-navy/10 p-2 text-xs bg-slate-50"
                        data-testid={`reg-doc-${slot}`}>
                      <div className="font-semibold text-brand-navy">{slot.replace(/_/g, " ")}</div>
                      <div className="text-brand-navy/60 mt-0.5 truncate">{meta.file_name}</div>
                      <div className="mt-1 flex gap-1">
                        <a href={`${process.env.REACT_APP_BACKEND_URL}${meta.url}`} target="_blank" rel="noreferrer"
                           className="text-[10px] uppercase tracking-widest px-2 py-1 border border-brand-navy/20 text-brand-navy hover:bg-white">View</a>
                        <a href={`${process.env.REACT_APP_BACKEND_URL}${meta.url}`} download={meta.file_name}
                           className="text-[10px] uppercase tracking-widest px-2 py-1 border border-brand-navy/20 text-brand-navy hover:bg-white">Download</a>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <div className="mt-6">
              <label className="pmc-label">Reviewer notes (required for reject / clarify)</label>
              <textarea rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} data-testid="reg-notes"
                className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy" />
            </div>
            <div className="mt-4 flex gap-2 flex-wrap">
              <button type="button" onClick={() => decide("approve")} data-testid="reg-approve" className="px-6 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90">Approve</button>
              <button type="button" onClick={() => decide("clarify")} data-testid="reg-clarify" className="px-6 py-3 text-[12px] font-semibold uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5">Request clarification</button>
              <button type="button" onClick={() => decide("reject")} data-testid="reg-reject" className="px-6 py-3 text-[12px] font-semibold uppercase tracking-widest border border-red-500/50 text-red-600 hover:bg-red-50">Reject</button>
            </div>
          </div>
        ) : (
          <div className="border border-dashed border-brand-navy/20 bg-white p-14 text-center text-brand-navy/50">
            Select a registration on the left to review it.
          </div>
        )}
      </div>
    </div>
  );
}
