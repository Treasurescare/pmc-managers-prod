import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { mastersApi, showApiError } from "@/lib/api";

/**
 * CategoryRequestsPanel — v50l; v51ag adds search + status date filter.
 */
export default function CategoryRequestsPanel() {
  const [rows, setRows] = useState([]);
  const [status, setStatus] = useState("pending");
  const [notes, setNotes] = useState({});
  const [busyId, setBusyId] = useState(null);
  // v51ag — client-side filters
  const [q, setQ] = useState("");
  const [reqFrom, setReqFrom] = useState("");
  const [reqTo, setReqTo] = useState("");
  // v52v — Created by filter (shared pattern).
  const [createdBy, setCreatedBy] = useState("");

  const load = useCallback(() => {
    mastersApi.listCategoryRequests(status)
      .then((d) => setRows(Array.isArray(d) ? d : (d?.items || [])))
      .catch(showApiError);
  }, [status]);
  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const cby = (createdBy || "").trim().toLowerCase();
    return rows.filter((r) => {
      if (needle) {
        const hay = [
          r.category_name, r.category_code, r.vendor_company, r.vendor_ref,
          r.vendor_email, r.rationale,
        ].filter(Boolean).join(" ").toLowerCase();
        if (!hay.includes(needle)) return false;
      }
      if (cby) {
        const h = String(r.vendor_email || r.created_by_email || "").toLowerCase();
        if (!h.includes(cby)) return false;
      }
      const d = (r.requested_at || "").slice(0, 10);
      if (reqFrom && d && d < reqFrom) return false;
      if (reqTo   && d && d > reqTo)   return false;
      return true;
    });
  }, [rows, q, reqFrom, reqTo, createdBy]);

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

  const clearFilters = () => { setQ(""); setReqFrom(""); setReqTo(""); setCreatedBy(""); };

  return (
    <div data-testid="category-requests-panel">
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        {["pending", "approved", "rejected"].map((s) => (
          <button key={s} onClick={() => setStatus(s)}
            data-testid={`cat-req-tab-${s}`}
            className={"px-3 py-1.5 text-[10px] uppercase tracking-widest border " +
              (status === s ? "bg-brand-navy text-white border-brand-navy"
                            : "bg-white text-brand-navy/70 border-brand-navy/20")}>
            {s} ({status === s ? filtered.length : "…"})
          </button>
        ))}
      </div>

      {/* v51ag — search / date-range filter bar */}
      <div className="bg-white border border-brand-navy/15 rounded px-3 py-3 mb-4 flex flex-wrap items-end gap-3"
           data-testid="cat-req-filter-bar">
        <label className="flex flex-col flex-1 min-w-[200px]">
          <span className="pmc-label text-[10px]">Search</span>
          <input value={q} onChange={(e) => setQ(e.target.value)}
                 placeholder="Category, vendor name or email…"
                 data-testid="cat-req-search"
                 className="mt-1 px-2 py-1.5 border border-brand-navy/15 text-sm"/>
        </label>
        <label className="flex flex-col min-w-[180px]">
          <span className="pmc-label text-[10px]">Created by</span>
          <input value={createdBy} onChange={(e) => setCreatedBy(e.target.value)}
                 placeholder="vendor email contains…"
                 data-testid="cat-req-created-by"
                 className="mt-1 px-2 py-1.5 border border-brand-navy/15 text-sm"/>
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
                 data-testid="cat-req-from"
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
                 data-testid="cat-req-to"
                 className="mt-1 px-2 py-1.5 border border-brand-navy/15 text-sm"/>
        </label>
        <button type="button" onClick={clearFilters}
                data-testid="cat-req-clear"
                className="px-3 py-2 text-[10px] uppercase tracking-widest border border-brand-navy/20 text-brand-navy/70 hover:bg-brand-navy/5">
          Clear
        </button>
      </div>

      {filtered.length === 0 && (
        <div className="p-6 text-sm text-brand-navy/50 bg-white border border-brand-navy/10">
          {rows.length === 0 ? `No ${status} requests.` : "No requests match your filters."}
        </div>
      )}
      <div className="space-y-3">
        {filtered.map((r) => (
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
