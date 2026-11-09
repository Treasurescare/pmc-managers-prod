import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { vendorApi, mastersApi, publicApi, taxonomyApi, showApiError } from "@/lib/api";
import { contractTypeOptions } from "@/components/taxonomy";

/**
 * VendorCategories — v50l.
 * Supplier page to view approved categories, request additions from the
 * backend-driven category master, and see pending / recent decisions.
 * Mounted at /vendor/categories.
 */
export default function VendorCategories() {
  const navigate = useNavigate();
  const [state, setState] = useState({ approved: [], pending: [], recent: [] });
  const [master, setMaster] = useState([]);
  const [sectors, setSectors] = useState([]);
  const [contractTypes, setContractTypes] = useState([]);
  const [draft, setDraft] = useState({ code: "", name: "", rationale: "", sector_code: "", sector_name: "", contract_type_code: "", contract_type_name: "" });
  const [query, setQuery] = useState(() => new URLSearchParams(window.location.search).get("add") || "");
  const [unspsc, setUnspsc] = useState([]);
  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) { setUnspsc([]); return undefined; }
    const t = setTimeout(() => {
      taxonomyApi.search(q).then((r) => setUnspsc((r.items || []).map((x) => ({ code: x.code, name: x.title, unspsc_code: x.code })))).catch(() => setUnspsc([]));
    }, 250);
    return () => clearTimeout(t);
  }, [query]);
  const [busy, setBusy] = useState(false);
  const [quote, setQuote] = useState(null);
  useEffect(() => {
    if (!draft.name) { setQuote(null); return; }
    vendorApi.categoryFeeQuote(draft.name).then(setQuote).catch(() => setQuote(null));
  }, [draft.name]);
  useEffect(() => {
    const sid = new URLSearchParams(window.location.search).get("cat_session");
    if (sid) {
      vendorApi.categoryCheckoutStatus(sid).then((s) => {
        if (s.payment_status === "paid") toast.success("Payment received — your category request is back with PMC for approval. A receipt has been emailed.");
        else toast("Payment is still processing — refresh in a moment.");
        window.history.replaceState({}, "", "/vendor/categories");
        refresh();
      }).catch(() => {});
    }
  }, []);
  const pay = async (id) => {
    try { const r = await vendorApi.categoryCheckout(id, window.location.origin); window.location.href = r.checkout_url; }
    catch (e) { showApiError(e); }
  };

  const refresh = () => vendorApi.myCategories()
    .then(setState).catch(showApiError);

  useEffect(() => {
    refresh();
    mastersApi.listCategoriesPublic()
      .then((rows) => setMaster(Array.isArray(rows) ? rows : []))
      .catch(() => setMaster([]));
    publicApi.listSectorsPublic().then((r) => setSectors(Array.isArray(r) ? r : [])).catch(() => setSectors([]));
    publicApi.listContractTypesPublic().then((r) => setContractTypes(Array.isArray(r) ? r : [])).catch(() => setContractTypes([]));
  }, []);

  const approvedSet = new Set(state.approved.map((a) => String(a).toLowerCase()));
  const pendingCodes = new Set(state.pending.map((p) => p.category_code));
  const masterHits = master.filter((c) =>
    (!query || (c.name + " " + (c.unspsc_code || "")).toLowerCase().includes(query.toLowerCase()))
  );
    const seen = new Set(masterHits.map((c) => c.name.toLowerCase()));
    const seenCodes = new Set();
    const uniqUnspsc = unspsc.filter((c) => c.name && !seen.has(c.name.toLowerCase()) && !seenCodes.has(c.code) && seenCodes.add(c.code));
  const available = [...masterHits, ...uniqUnspsc]
    .filter((c) => !approvedSet.has(c.name.toLowerCase()) && !pendingCodes.has(c.code));
  useEffect(() => {
    const add = new URLSearchParams(window.location.search).get("add");
    const hit = add && !draft.code && available.find((c) => c.name.toLowerCase() === add.toLowerCase());
    if (hit) setDraft((d) => ({ ...d, code: hit.code, name: hit.name }));
  }, [available.length]); // eslint-disable-line react-hooks/exhaustive-deps

  const submit = async () => {
    if (!draft.code || !draft.name) {
      toast.error("Pick a category from the list first.");
      return;
    }
    setBusy(true);
    try {
      const created = await vendorApi.requestCategory({
        category_code: draft.code,
        category_name: draft.name,
        rationale: draft.rationale || null,
        sector_code: draft.sector_code || null,
        sector_name: draft.sector_name || null,
        contract_type_code: draft.contract_type_code || null,
        contract_type_name: draft.contract_type_name || null,
      });
      if (created?.payment_status === "unpaid") {
        toast.warning(created.fee_message || "Registration is free for one category — this additional category needs a payment.", {
          description: `Pay ${created.fee_currency} ${Number(created.fee_amount).toLocaleString()} from the Pending list so PMC can approve it.`,
        });
      } else {
        toast.success(`Request submitted · ${draft.name}`, { description: "An admin will review it shortly." });
      }
      setDraft({ code: "", name: "", rationale: "", sector_code: "", sector_name: "", contract_type_code: "", contract_type_name: "" });
      refresh();
    } catch (e) { showApiError(e); }
    finally { setBusy(false); }
  };

  return (
    <div className="max-w-5xl mx-auto p-6 lg:p-10" data-testid="vendor-categories">
      <button type="button"
        onClick={() => navigate("/vendor")}
        className="px-4 py-2 text-[11px] font-semibold uppercase tracking-widest border border-brand-navy text-brand-navy bg-white hover:bg-brand-navy hover:text-white mb-6"
        data-testid="vendor-cat-back">
        ← Back to supplier portal
      </button>
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
                  <span className="text-[10px] uppercase tracking-widest text-amber-800 bg-amber-50 border border-amber-300 px-2 py-0.5">{p.status === "payment_pending" ? "sent back — payment pending" : "pending"}</span>
                </div>
                {p.payment_status === "unpaid" && (
                  <div className="flex items-center justify-between gap-2 mt-2 bg-red-50 border border-red-200 px-3 py-2" data-testid={`pending-fee-${p.category_code}`}>
                    <span className="text-xs text-red-800">Additional category fee <b>{p.fee_currency} {Number(p.fee_amount || 0).toLocaleString()}</b> — unpaid. PMC can't approve until it's paid.</span>
                    <button type="button" onClick={() => pay(p.id)} data-testid={`pending-pay-${p.category_code}`}
                      className="px-3 py-1.5 text-[10px] uppercase tracking-widest bg-brand-navy text-white">Pay now</button>
                  </div>
                )}
                {p.payment_status === "paid" && <div className="text-xs text-emerald-700 mt-1" data-testid={`pending-paid-${p.category_code}`}>✓ Fee paid — awaiting approval</div>}
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
          Search the procurement category master or any UNSPSC category (e.g. "Wind generators"). Admin approval is required before tender matching picks it up.
        </p>
        {/* v56s — Sector → Contract type taxonomy context (cascading). Optional. */}
        <div className="grid md:grid-cols-2 gap-3 mb-3">
          <select data-testid="vcat-sector-code" value={draft.sector_code}
            onChange={(e) => {
              const s = sectors.find((x) => x.code === e.target.value);
              setDraft((d) => ({ ...d, sector_code: e.target.value, sector_name: s ? s.name : "", contract_type_code: "", contract_type_name: "" }));
            }}
            className="px-3 py-2 border border-brand-navy/20 text-sm bg-white">
            <option value="">Sector (optional)…</option>
            {sectors.map((s) => <option key={s.code} value={s.code}>{s.name}</option>)}
          </select>
          <select data-testid="vcat-contract-type-code" value={draft.contract_type_code}
            onChange={(e) => {
              const c = contractTypes.find((x) => x.code === e.target.value);
              setDraft((d) => ({ ...d, contract_type_code: e.target.value, contract_type_name: c ? c.name : "" }));
            }}
            className="px-3 py-2 border border-brand-navy/20 text-sm bg-white">
            <option value="">Contract type (optional)…</option>
            {contractTypeOptions(contractTypes)}
          </select>
        </div>
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
        {quote && (
          <div data-testid="cat-fee-quote" className={"text-xs mb-3 px-3 py-2 border " + (quote.required ? "bg-amber-50 border-amber-300 text-amber-900" : "bg-emerald-50 border-emerald-200 text-emerald-900")}>
            {quote.required
              ? <>{quote.message} This category costs <b>{quote.currency} {Number(quote.amount).toLocaleString()}</b> — you'll get a payment link after you submit.</>
              : quote.reason === "first_free" ? "Your first category is free." : "No fee is set for additional categories in your country right now."}
          </div>
        )}
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
