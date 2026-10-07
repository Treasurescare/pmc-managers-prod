import { useCallback, useEffect, useMemo, useState } from "react";
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
 * ProfileChangeRequestsPanel — v50m; v51ag adds search + field + date filter.
 */
export default function ProfileChangeRequestsPanel() {
  const [rows, setRows] = useState([]);
  const [status, setStatus] = useState("pending");
  const [notes, setNotes] = useState({});
  const [busyId, setBusyId] = useState(null);
  // v51ag — client-side filters
  const [q, setQ] = useState("");
  const [field, setField] = useState("");
  const [reqFrom, setReqFrom] = useState("");
  const [reqTo, setReqTo] = useState("");

  const load = useCallback(() => {
    mastersApi.listProfileChangeRequests(status)
      .then((d) => setRows(Array.isArray(d) ? d : (d?.items || [])))
      .catch(showApiError);
  }, [status]);
  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return rows.filter((r) => {
      if (field && r.field !== field) return false;
      if (needle) {
        const hay = [
          r.vendor_company, r.vendor_ref, r.vendor_email,
          r.old_value, r.new_value, r.reason, r.field,
          FIELD_LABELS[r.field],
        ].filter(Boolean).join(" ").toLowerCase();
        if (!hay.includes(needle)) return false;
      }
      const d = (r.requested_at || "").slice(0, 10);
      if (reqFrom && d && d < reqFrom) return false;
      if (reqTo   && d && d > reqTo)   return false;
      return true;
    });
  }, [rows, q, field, reqFrom, reqTo]);

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

  const clearFilters = () => { setQ(""); setField(""); setReqFrom(""); setReqTo(""); };

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

      {/* v51ag — filter bar */}
      <div className="bg-white border border-brand-navy/15 rounded px-3 py-3 mb-4 flex flex-wrap items-end gap-3"
           data-testid="pcr-filter-bar">
        <label className="flex flex-col flex-1 min-w-[200px]">
          <span className="pmc-label text-[10px]">Search</span>
          <input value={q} onChange={(e) => setQ(e.target.value)}
                 placeholder="Vendor, old/new value, reason…"
                 data-testid="pcr-search"
                 className="mt-1 px-2 py-1.5 border border-brand-navy/15 text-sm"/>
        </label>
        <label className="flex flex-col min-w-[160px]">
          <span className="pmc-label text-[10px]">Field</span>
          <select value={field} onChange={(e) => setField(e.target.value)}
                  data-testid="pcr-field-filter"
                  className="mt-1 px-2 py-1.5 border border-brand-navy/15 text-sm bg-white">
            <option value="">All fields</option>
            {Object.entries(FIELD_LABELS).map(([k, v]) =>
              <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
        <label className="flex flex-col">
          <span className="pmc-label text-[10px]">Requested from</span>
          <input type="date" value={reqFrom}
                 max={reqTo || undefined}
                 onChange={(e) => {
                   const v = e.target.value;
                   if (v && reqTo && v > reqTo) {
                     toast.error('"Requested from" cannot be later than "Requested to"');
                     return;
                   }
                   setReqFrom(v);
                 }}
                 data-testid="pcr-from"
                 className="mt-1 px-2 py-1.5 border border-brand-navy/15 text-sm"/>
        </label>
        <label className="flex flex-col">
          <span className="pmc-label text-[10px]">Requested to</span>
          <input type="date" value={reqTo}
                 min={reqFrom || undefined}
                 onChange={(e) => {
                   const v = e.target.value;
                   if (v && reqFrom && v < reqFrom) {
                     toast.error('"Requested to" cannot be earlier than "Requested from"');
                     return;
                   }
                   setReqTo(v);
                 }}
                 data-testid="pcr-to"
                 className="mt-1 px-2 py-1.5 border border-brand-navy/15 text-sm"/>
        </label>
        <button type="button" onClick={clearFilters}
                data-testid="pcr-clear"
                className="px-3 py-2 text-[10px] uppercase tracking-widest border border-brand-navy/20 text-brand-navy/70 hover:bg-brand-navy/5">
          Clear
        </button>
      </div>

      {filtered.length === 0 && (
        <div className="p-6 text-sm text-brand-navy/50 bg-white border border-brand-navy/10"
             data-testid="pcr-empty">
          {rows.length === 0
            ? `No ${status} profile change requests.`
            : "No profile change requests match your filters."}
        </div>
      )}
      <div className="space-y-3">
        {filtered.map((r) => {
          const emailBlocked = r.field === "email" && !r.email_verified;
          const phoneBlocked = (r.field === "mobile" || r.field === "office_phone") && !r.phone_confirmed;
          const approveBlocked = emailBlocked || phoneBlocked;
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
                  {(r.field === "mobile" || r.field === "office_phone") && (
                    <div className={"text-[11px] mt-1 inline-block px-2 py-0.5 border " +
                      (r.phone_confirmed
                        ? "border-emerald-300 text-emerald-800 bg-emerald-50"
                        : "border-amber-300 text-amber-900 bg-amber-50")}
                      data-testid={`pcr-phonestate-${r.id}`}>
                      {r.phone_confirmed ? "✓ Confirmed by vendor (click-link on current email)" : "⚠ Awaiting vendor confirmation on current email"}
                    </div>
                  )}
                  {r.evidence_key && (
                    <div className="mt-2 inline-flex items-center gap-2 px-2 py-1 border border-brand-navy/20 bg-brand-pale/30"
                         data-testid={`pcr-evidence-${r.id}`}>
                      <span className="text-[11px] text-brand-navy/60">📎 Evidence:</span>
                      <a href={`/api/v1/uploads/files/${r.evidence_key}`}
                         target="_blank" rel="noreferrer"
                         className="text-[11px] font-mono text-brand-navy underline"
                         data-testid={`pcr-evidence-view-${r.id}`}>
                        {r.evidence_filename || "View document"}
                      </a>
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
                          disabled={busyId === r.id || approveBlocked}
                          title={emailBlocked ? "Vendor must verify the new email first"
                                 : phoneBlocked ? "Vendor must click the confirmation link in their current email first"
                                 : ""}
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
