import { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";
import { tenderProApi, feeBillingApi, showApiError } from "@/lib/api";
import { CountrySelect } from "@/components/CountryPicker";

/**
 * v46b — "Charge fee" widget. Admin picks a fee master (any of the 5 kinds),
 * enters the tender value (or leaves 0 for fixed-fee masters), and creates a
 * Stripe checkout session. Amount is server-authoritative from the slab.
 */
export default function FeeCharger() {
  const [masters, setMasters]     = useState([]);
  const [country, setCountry]     = useState("");
  const [kind, setKind]           = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [tenderValue, setTenderValue] = useState("0");
  const [buyerEmail, setBuyerEmail]   = useState("");
  const [contextRef, setContextRef]   = useState("");
  const [preview, setPreview]         = useState(null);
  const [busy, setBusy]           = useState(false);

  const load = useCallback(async () => {
    try {
      const list = await tenderProApi.listEmdMasters(country || undefined, kind || undefined);
      setMasters(list || []);
    } catch (e) { showApiError(e); }
  }, [country, kind]);

  useEffect(() => { load(); }, [load]);

  const previewFee = async () => {
    if (!selectedId) return toast.error("Pick a fee master first");
    try {
      const r = await tenderProApi.computeEmd(selectedId, parseFloat(tenderValue) || 0);
      setPreview(r);
    } catch (e) { showApiError(e); setPreview(null); }
  };

  const charge = async () => {
    if (!selectedId) return toast.error("Pick a fee master first");
    setBusy(true);
    try {
      const r = await feeBillingApi.feeCheckout({
        fee_master_id: selectedId,
        tender_value: parseFloat(tenderValue) || 0,
        origin_url: window.location.origin,
        buyer_email: buyerEmail.trim() || null,
        context_ref: contextRef.trim() || null,
      });
      toast.success(`Checkout ready: ${r.currency.toUpperCase()} ${r.amount}`);
      // Open Stripe checkout in new tab
      const w = window.open(r.checkout_url, "_blank", "noopener,noreferrer");
      if (!w) window.location.href = r.checkout_url;
    } catch (e) { showApiError(e); }
    finally { setBusy(false); }
  };

  const kindLabels = {
    tender_fee: "Tender fee", emd: "EMD (bid security)",
    registration: "Vendor registration",
    subscription: "Subscription (monthly)",
    premium_subscription: "Premium subscription",
    transaction: "Transaction fee",
    data_intel: "Data / intelligence fee",
  };

  return (
    <div className="bg-white border p-5" data-testid="fee-charger">
      <div className="pmc-label mb-3">Charge a fee via Stripe</div>
      <p className="text-xs text-brand-navy/60 mb-4 max-w-2xl">
        Pick any active fee master (EMD, tender fee, registration, subscription, premium,
        transaction, data-intel). The amount is computed from the matching slab and pushed
        to Stripe Checkout. Amount is server-authoritative — the client is never trusted for pricing.
      </p>

      <div className="grid gap-3 md:grid-cols-4 mb-4">
        <label className="text-xs uppercase tracking-widest text-brand-navy/60">
          Filter by country (opt)
          <CountrySelect value={country} onChange={setCountry} testId="fc-country" />
        </label>
        <label className="text-xs uppercase tracking-widest text-brand-navy/60">
          Filter by kind (opt)
          <select value={kind} onChange={(e) => setKind(e.target.value)}
                  data-testid="fc-kind"
                  className="mt-1 w-full px-3 py-2 border normal-case tracking-normal">
            <option value="">All kinds</option>
            {Object.entries(kindLabels).map(([k, v]) => (<option key={k} value={k}>{v}</option>))}
          </select>
        </label>
        <label className="col-span-2 text-xs uppercase tracking-widest text-brand-navy/60">
          Fee master ({masters.length} available)
          <select value={selectedId} onChange={(e) => { setSelectedId(e.target.value); setPreview(null); }}
                  data-testid="fc-master"
                  className="mt-1 w-full px-3 py-2 border normal-case tracking-normal">
            <option value="">— pick a master —</option>
            {masters.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name} · {kindLabels[m.kind] || m.kind} · {m.country} · {m.currency}
                {!m.is_active ? " (inactive)" : ""}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="grid gap-3 md:grid-cols-3 mb-4">
        <label className="text-xs uppercase tracking-widest text-brand-navy/60">
          Tender value (for slab match)
          <input type="number" min="0" step="1" value={tenderValue}
                 onChange={(e) => { setTenderValue(e.target.value); setPreview(null); }}
                 data-testid="fc-tender-value"
                 className="mt-1 w-full px-3 py-2 border normal-case tracking-normal font-mono" />
        </label>
        <label className="text-xs uppercase tracking-widest text-brand-navy/60">
          Buyer email (opt)
          <input type="email" value={buyerEmail}
                 onChange={(e) => setBuyerEmail(e.target.value)}
                 data-testid="fc-buyer-email"
                 className="mt-1 w-full px-3 py-2 border normal-case tracking-normal" />
        </label>
        <label className="text-xs uppercase tracking-widest text-brand-navy/60">
          Context ref (tender / notice)
          <input value={contextRef} onChange={(e) => setContextRef(e.target.value)}
                 placeholder="PMC-KZ-RFP-…"
                 data-testid="fc-context-ref"
                 className="mt-1 w-full px-3 py-2 border normal-case tracking-normal font-mono" />
        </label>
      </div>

      <div className="flex gap-2 flex-wrap">
        <button type="button" onClick={previewFee}
                data-testid="fc-preview"
                className="px-4 py-2 text-[11px] font-semibold uppercase tracking-widest border border-brand-navy text-brand-navy hover:bg-brand-navy hover:text-white">
          Preview fee
        </button>
        <button type="button" onClick={charge} disabled={busy || !selectedId}
                data-testid="fc-charge"
                className="px-6 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40">
          {busy ? "Creating checkout…" : "Charge via Stripe"}
        </button>
      </div>

      {preview && (
        <div className="mt-4 border border-emerald-500/60 bg-emerald-50 p-4 text-sm text-emerald-900"
             data-testid="fc-preview-result">
          <div className="pmc-label mb-1">Preview</div>
          <div className="flex flex-wrap gap-4 font-mono">
            <span>Amount: <b>{(preview.currency || "USD").toUpperCase()} {preview.amount?.toLocaleString?.() ?? preview.amount}</b></span>
            <span>Type: <b>{preview.type}</b></span>
            {preview.percentage != null && <span>Percentage: <b>{preview.percentage}%</b></span>}
          </div>
        </div>
      )}
    </div>
  );
}
