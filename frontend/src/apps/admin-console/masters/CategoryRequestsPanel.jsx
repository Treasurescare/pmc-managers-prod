import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { mastersApi, showApiError } from "@/lib/api";

/**
 * CategoryRequestsPanel — v50l.
 * Admin tab listing pending vendor category requests with approve/reject
 * actions. Mounted inside Admin → Masters → Vendor requests.
 */
export default function CategoryRequestsPanel() {
  const [rows, setRows] = useState([]);
  const [status, setStatus] = useState("pending");
  const [notes, setNotes] = useState({});
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(() => {
    mastersApi.listCategoryRequests(status)
      // v50r — defensive: wrong-router-order used to return the
      // {"detail": "Vendor not found"} dict instead of an array and the
      // panel would crash on rows.map. Keep guard even after fix.
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
      if (action === "approve") await mastersApi.approveCategoryRequest(id, note);
      else await mastersApi.rejectCategoryRequest(id, note);
      toast.success(`${action === "approve" ? "Approved" : "Rejected"} · supplier notified`);
      setNotes((n) => { const x = { ...n }; delete x[id]; return x; });
      load();
    } catch (e) { showApiError(e); }
    finally { setBusyId(null); }
  };

  return (
    <div data-testid="category-requests-panel">
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        {["pending", "approved", "rejected"].map((s) => (
          <button key={s} onClick={() => setStatus(s)}
            data-testid={`cat-req-tab-${s}`}
            className={"px-3 py-1.5 text-[10px] uppercase tracking-widest border " +
              (status === s ? "bg-brand-navy text-white border-brand-navy"
                            : "bg-white text-brand-navy/70 border-brand-navy/20")}>
            {s} ({status === s ? rows.length : "…"})
          </button>
        ))}
      </div>
      {rows.length === 0 && (
        <div className="p-6 text-sm text-brand-navy/50 bg-white border border-brand-navy/10">
          No {status} requests.
        </div>
      )}
      <div className="space-y-3">
        {rows.map((r) => (
          <div key={r.id} className="bg-white border border-brand-navy/10 p-4"
               data-testid={`cat-req-${r.id}`}>
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div className="min-w-0">
                <div className="text-sm font-semibold text-brand-navy">{r.category_name}</div>
                <div className="text-xs text-brand-navy/60 mt-0.5">
                  <strong>{r.vendor_company || "—"}</strong> · {r.vendor_ref} · {r.vendor_email}
                </div>
                {r.rationale && (
                  <div className="text-xs text-brand-navy/70 mt-2 italic">"{r.rationale}"</div>
                )}
                <div className="text-[11px] text-brand-navy/50 mt-1 font-mono">
                  code {r.category_code} · requested {r.requested_at?.slice(0, 16).replace("T", " ")}
                </div>
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
                  data-testid={`cat-req-notes-${r.id}`} />
                <button type="button" onClick={() => decide(r.id, "approve")} disabled={busyId === r.id}
                  data-testid={`cat-req-approve-${r.id}`}
                  className="px-3 py-1.5 text-[10px] uppercase tracking-widest bg-emerald-700 text-white hover:bg-emerald-800 disabled:opacity-50">
                  Approve
                </button>
                <button type="button" onClick={() => decide(r.id, "reject")} disabled={busyId === r.id}
                  data-testid={`cat-req-reject-${r.id}`}
                  className="px-3 py-1.5 text-[10px] uppercase tracking-widest bg-red-700 text-white hover:bg-red-800 disabled:opacity-50">
                  Reject
                </button>
              </div>
            )}
            {r.status !== "pending" && r.decision_notes && (
              <div className="text-xs text-brand-navy/60 mt-2">Decision note: "{r.decision_notes}"</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
