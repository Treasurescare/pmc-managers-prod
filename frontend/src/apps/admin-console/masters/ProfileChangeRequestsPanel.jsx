import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { mastersApi, showApiError } from "@/lib/api";

const FIELD_LABELS = {
  company_name: "Company name",
  address: "Registered address",
  office_phone: "Office telephone",
  mobile: "Mobile",
  email: "Login email",
};

/**
 * ProfileChangeRequestsPanel — v50m.
 * Admin tab under Masters → "Profile changes" showing vendor profile edit
 * requests (address / phone / email) with approve/reject actions.
 * Email changes additionally require the vendor to have already clicked
 * the confirmation link emailed to the NEW address.
 */
export default function ProfileChangeRequestsPanel() {
  const [rows, setRows] = useState([]);
  const [status, setStatus] = useState("pending");
  const [notes, setNotes] = useState({});
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(() => {
    mastersApi.listProfileChangeRequests(status)
      .then((d) => setRows(Array.isArray(d) ? d : (d?.items || [])))
      .catch(showApiError);
  }, [status]);
  useEffect(() => { load(); }, [load]);

  const decide = async (id, action) => {
    const note = notes[id] || "";
    if (action === "reject" && !note.trim()) {
      toast.error("A rejection reason is required.");
      return;
    }
    setBusyId(id);
    try {
      if (action === "approve") await mastersApi.approveProfileChangeRequest(id, note);
      else await mastersApi.rejectProfileChangeRequest(id, note);
      toast.success(`${action === "approve" ? "Approved" : "Rejected"} · vendor notified`);
      setNotes((n) => { const x = { ...n }; delete x[id]; return x; });
      load();
    } catch (e) { showApiError(e); }
    finally { setBusyId(null); }
  };

  return (
    <div data-testid="profile-change-requests-panel">
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        {["pending", "approved", "rejected"].map((s) => (
          <button key={s} onClick={() => setStatus(s)}
            data-testid={`pcr-tab-${s}`}
            className={"px-3 py-1.5 text-[10px] uppercase tracking-widest border " +
              (status === s ? "bg-brand-navy text-white border-brand-navy"
                            : "bg-white text-brand-navy/70 border-brand-navy/20")}>
            {s}
          </button>
        ))}
      </div>
      {rows.length === 0 && (
        <div className="p-6 text-sm text-brand-navy/50 bg-white border border-brand-navy/10"
             data-testid="pcr-empty">
          No {status} profile change requests.
        </div>
      )}
      <div className="space-y-3">
        {rows.map((r) => {
          const emailBlocked = r.field === "email" && !r.email_verified;
          return (
            <div key={r.id} className="bg-white border border-brand-navy/10 p-4"
                 data-testid={`pcr-row-${r.id}`}>
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <div className="min-w-0">
                  <div className="text-sm font-semibold text-brand-navy">
                    {FIELD_LABELS[r.field] || r.field}
                  </div>
                  <div className="text-xs text-brand-navy/60 mt-0.5">
                    <strong>{r.vendor_company || "—"}</strong> · {r.vendor_ref} · {r.vendor_email}
                  </div>
                  <div className="text-sm text-brand-navy/80 mt-2">
                    <span className="text-brand-navy/50">From:</span>{" "}
                    <span className="line-through">{r.old_value || <em>not set</em>}</span>
                  </div>
                  <div className="text-sm text-brand-navy mt-0.5">
                    <span className="text-brand-navy/50">To:</span>{" "}
                    <b data-testid={`pcr-new-${r.id}`}>{r.new_value}</b>
                  </div>
                  {r.reason && (
                    <div className="text-xs text-brand-navy/70 mt-2 italic">"{r.reason}"</div>
                  )}
                  <div className="text-[11px] text-brand-navy/50 mt-1 font-mono">
                    requested {r.requested_at?.slice(0, 16).replace("T", " ")}
                  </div>
                  {r.field === "email" && (
                    <div className={"text-[11px] mt-1 inline-block px-2 py-0.5 border " +
                      (r.email_verified
                        ? "border-emerald-300 text-emerald-800 bg-emerald-50"
                        : "border-amber-300 text-amber-900 bg-amber-50")}
                      data-testid={`pcr-emailstate-${r.id}`}>
                      {r.email_verified ? "✓ New email verified" : "⚠ New email NOT yet verified by vendor"}
                    </div>
                  )}
                </div>
                <span className={"text-[10px] uppercase tracking-widest px-2 py-0.5 shrink-0 " +
                  (r.status === "approved" ? "text-emerald-800 bg-emerald-50 border border-emerald-200"
                   : r.status === "rejected" ? "text-red-800 bg-red-50 border border-red-200"
                   : "text-amber-900 bg-amber-50 border border-amber-300")}>
                  {r.status}
                </span>
              </div>
              {status === "pending" && (
                <div className="mt-3 flex items-center gap-2 flex-wrap">
                  <input value={notes[r.id] || ""}
                    onChange={(e) => setNotes({ ...notes, [r.id]: e.target.value })}
                    placeholder="Notes (required for reject)"
                    className="flex-1 min-w-[200px] px-3 py-1.5 border border-brand-navy/20 text-sm"
                    data-testid={`pcr-notes-${r.id}`} />
                  <button type="button" onClick={() => decide(r.id, "approve")}
                          disabled={busyId === r.id || emailBlocked}
                          title={emailBlocked ? "Vendor must verify the new email first" : ""}
                          data-testid={`pcr-approve-${r.id}`}
                          className="px-3 py-1.5 text-[10px] uppercase tracking-widest bg-emerald-700 text-white hover:bg-emerald-800 disabled:opacity-50">
                    Approve
                  </button>
                  <button type="button" onClick={() => decide(r.id, "reject")}
                          disabled={busyId === r.id}
                          data-testid={`pcr-reject-${r.id}`}
                          className="px-3 py-1.5 text-[10px] uppercase tracking-widest bg-red-700 text-white hover:bg-red-800 disabled:opacity-50">
                    Reject
                  </button>
                </div>
              )}
              {r.status !== "pending" && r.decision_notes && (
                <div className="text-xs text-brand-navy/60 mt-2">
                  Decision note: "{r.decision_notes}"
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
