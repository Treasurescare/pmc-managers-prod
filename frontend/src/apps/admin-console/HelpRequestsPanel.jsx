import { useEffect, useState } from "react";
import { toast } from "sonner";
import { adminApi, formatApiError } from "@/lib/api";

const KIND_LABELS = {
  "forgot-username": "Forgot username",
  "forgot-password": "Forgot password",
  "other": "Other",
};

export default function HelpRequestsPanel() {
  const [items, setItems] = useState([]);
  const [status, setStatus] = useState("open");
  const [busyId, setBusyId] = useState(null);
  const [notesById, setNotes] = useState({});

  const load = async () => {
    try {
      const r = await adminApi.listHelpRequests(status);
      setItems(r.items || []);
    } catch (err) { toast.error(formatApiError(err)); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [status]);

  const resolve = async (id) => {
    const notes = (notesById[id] || "").trim();
    if (!notes) return toast.error("Add resolution notes first.");
    setBusyId(id);
    try {
      await adminApi.resolveHelpRequest(id, notes);
      toast.success("Marked resolved.");
      load();
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusyId(null); }
  };

  return (
    <div data-testid="help-requests-panel">
      <div className="flex items-center gap-4 mb-4">
        <div className="pmc-label">Filter</div>
        {[["open", "Open"], ["resolved", "Resolved"], ["", "All"]].map(([v, l]) => (
          <button key={l} onClick={() => setStatus(v)}
                  data-testid={`help-filter-${v || "all"}`}
                  className={"px-3 py-1 text-[11px] font-semibold uppercase tracking-widest border " +
                    (status === v ? "bg-brand-navy text-white border-brand-navy"
                                  : "bg-white text-brand-navy/70 border-brand-navy/20")}>
            {l}
          </button>
        ))}
        <div className="ml-auto text-sm text-brand-navy/60">{items.length} requests</div>
      </div>

      {items.length === 0 && (
        <div className="text-center py-16 text-brand-navy/50 border border-dashed border-brand-navy/20">
          No requests in this view.
        </div>
      )}

      <div className="space-y-3">
        {items.map((it) => (
          <div key={it.id} className="bg-white border border-brand-navy/10 p-5"
               data-testid={`help-req-${it.id}`}>
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <div className="pmc-label">{KIND_LABELS[it.kind] || it.kind}</div>
                <div className="font-semibold text-brand-navy">{it.full_name}</div>
                <div className="text-xs text-brand-navy/60">
                  {[it.email, it.phone, it.company_name].filter(Boolean).join(" · ") || "—"}
                </div>
              </div>
              <div className="text-right text-xs text-brand-navy/60">
                <div>{new Date(it.created_at).toLocaleString()}</div>
                <div className={"mt-1 inline-block px-2 py-0.5 border " +
                                (it.status === "resolved"
                                  ? "border-emerald-500 text-emerald-700"
                                  : "border-amber-500 text-amber-700")}>
                  {it.status}
                </div>
              </div>
            </div>
            <div className="mt-3 text-sm text-brand-navy/80 whitespace-pre-wrap">{it.message}</div>

            {it.status === "resolved" && (
              <div className="mt-3 pt-3 border-t border-brand-navy/10 text-xs">
                <div className="pmc-label">Resolved by {it.resolved_by} · {new Date(it.resolved_at).toLocaleString()}</div>
                <div className="mt-1 text-brand-navy/80">{it.resolution_notes}</div>
              </div>
            )}

            {it.status !== "resolved" && (
              <div className="mt-4 pt-3 border-t border-brand-navy/10 space-y-2">
                <textarea rows={2} placeholder="Resolution notes (visible in audit)…"
                          value={notesById[it.id] || ""}
                          onChange={(e) => setNotes({ ...notesById, [it.id]: e.target.value })}
                          data-testid={`help-notes-${it.id}`}
                          className="w-full px-3 py-2 text-sm border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft" />
                <div className="text-right">
                  <button onClick={() => resolve(it.id)} disabled={busyId === it.id}
                          data-testid={`help-resolve-${it.id}`}
                          className="px-5 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-50">
                    {busyId === it.id ? "Saving…" : "Mark resolved"}
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
