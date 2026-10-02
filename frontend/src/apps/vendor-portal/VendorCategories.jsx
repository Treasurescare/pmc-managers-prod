import { useEffect, useState } from "react";
import { toast } from "sonner";
import { vendorApi, mastersApi, showApiError } from "@/lib/api";

/**
 * VendorCategories — v50l.
 * Supplier page to view approved categories, request additions from the
 * backend-driven category master, and see pending / recent decisions.
 * Mounted at /vendor/categories.
 */
export default function VendorCategories() {
  const [state, setState] = useState({ approved: [], pending: [], recent: [] });
  const [master, setMaster] = useState([]);
  const [draft, setDraft] = useState({ code: "", name: "", rationale: "" });
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = () => vendorApi.myCategories()
    .then(setState).catch(showApiError);

  useEffect(() => {
    refresh();
    mastersApi.listCategoriesPublic()
      .then((rows) => setMaster(Array.isArray(rows) ? rows : []))
      .catch(() => setMaster([]));
  }, []);

  const approvedSet = new Set(state.approved);
  const pendingCodes = new Set(state.pending.map((p) => p.category_code));
  const available = master.filter((c) =>
    !approvedSet.has(c.name) && !pendingCodes.has(c.code) &&
    (!query || (c.name + " " + (c.unspsc_code || "")).toLowerCase().includes(query.toLowerCase()))
  );

  const submit = async () => {
    if (!draft.code || !draft.name) {
      toast.error("Pick a category from the list first.");
      return;
    }
    setBusy(true);
    try {
      await vendorApi.requestCategory({
        category_code: draft.code,
        category_name: draft.name,
        rationale: draft.rationale || null,
      });
      toast.success(`Request submitted · ${draft.name}`, {
        description: "An admin will review it shortly.",
      });
      setDraft({ code: "", name: "", rationale: "" });
      refresh();
    } catch (e) { showApiError(e); }
    finally { setBusy(false); }
  };

  return (
    <div className="max-w-5xl mx-auto p-6 lg:p-10" data-testid="vendor-categories">
      <div className="pmc-label">Categories of interest</div>
      <h1 className="font-serif text-3xl text-brand-navy mt-1 mb-6">My bidding categories</h1>

      <section className="bg-white border border-brand-navy/10 p-5 mb-6">
        <div className="pmc-label">Approved · {state.approved.length}</div>
        <p className="text-xs text-brand-navy/60 mt-1 mb-3">
          Tenders in these categories match your profile and show in Find Tenders.
        </p>
        {state.approved.length === 0 ? (
          <div className="text-sm text-brand-navy/50">No categories yet — request your first below.</div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {state.approved.map((n) => (
              <span key={n} className="text-xs bg-emerald-50 border border-emerald-200 text-emerald-900 px-3 py-1 font-medium"
                    data-testid={`approved-${n}`}>✓ {n}</span>
            ))}
          </div>
        )}
      </section>

      {state.pending.length > 0 && (
        <section className="bg-white border border-brand-navy/10 p-5 mb-6" data-testid="pending-list">
          <div className="pmc-label">Pending review · {state.pending.length}</div>
          <div className="divide-y divide-brand-navy/10 mt-2">
            {state.pending.map((p) => (
              <div key={p.id} className="py-2 text-sm" data-testid={`pending-${p.category_code}`}>
                <div className="flex justify-between flex-wrap gap-2">
                  <strong>{p.category_name}</strong>
                  <span className="text-[10px] uppercase tracking-widest text-amber-800 bg-amber-50 border border-amber-300 px-2 py-0.5">pending</span>
                </div>
                {p.rationale && <div className="text-xs text-brand-navy/60 mt-1">"{p.rationale}"</div>}
                <div className="text-[11px] text-brand-navy/50 mt-1">Requested {p.requested_at?.slice(0, 10)}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="bg-white border border-brand-navy/10 p-5 mb-6">
        <div className="pmc-label">Request additional category</div>
        <p className="text-xs text-brand-navy/60 mt-1 mb-3">
          Pick from the procurement category master. Admin approval is required before tender matching picks it up.
        </p>
        <input value={query} onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by name or UNSPSC code…"
          className="w-full px-3 py-2 border border-brand-navy/20 text-sm mb-3"
          data-testid="cat-search" />
        <div className="max-h-56 overflow-y-auto border border-brand-navy/10 mb-3">
          {available.slice(0, 50).map((c) => (
            <label key={c.id || c.code}
              className={"flex items-center gap-2 px-3 py-2 cursor-pointer text-sm border-b border-brand-navy/5 hover:bg-brand-pale/50 " +
                         (draft.code === c.code ? "bg-emerald-50" : "")}>
              <input type="radio" name="catpick" checked={draft.code === c.code}
                onChange={() => setDraft((d) => ({ ...d, code: c.code, name: c.name }))}
                data-testid={`pick-${c.code}`} />
              {c.unspsc_code && <span className="text-xs font-mono text-brand-navy/50">{c.unspsc_code}</span>}
              <span>{c.name}</span>
            </label>
          ))}
          {available.length === 0 && <div className="p-4 text-xs text-brand-navy/50">No matching categories left.</div>}
        </div>
        <textarea value={draft.rationale} onChange={(e) => setDraft({ ...draft, rationale: e.target.value })}
          rows={3} placeholder="Why are you qualified for this category? (optional, helps admin decide)"
          className="w-full px-3 py-2 border border-brand-navy/20 text-sm mb-3"
          data-testid="cat-rationale" />
        <button type="button" onClick={submit} disabled={busy || !draft.code}
          data-testid="cat-submit"
          className="px-5 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-50">
          {busy ? "Submitting…" : "Request category"}
        </button>
      </section>

      {state.recent.length > 0 && (
        <section className="bg-white border border-brand-navy/10 p-5" data-testid="recent-decisions">
          <div className="pmc-label">Recent decisions</div>
          <div className="divide-y divide-brand-navy/10 mt-2 text-sm">
            {state.recent.map((r) => (
              <div key={r.id} className="py-2 flex justify-between flex-wrap gap-2">
                <div>
                  <strong>{r.category_name}</strong>
                  {r.decision_notes && <div className="text-xs text-brand-navy/60 mt-1">"{r.decision_notes}"</div>}
                </div>
                <span className={"text-[10px] uppercase tracking-widest px-2 py-0.5 " +
                  (r.status === "approved" ? "text-emerald-800 bg-emerald-50 border border-emerald-200"
                                           : "text-red-800 bg-red-50 border border-red-200")}>
                  {r.status}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
