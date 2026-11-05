import { useEffect, useState } from "react";
import { toast } from "sonner";
import { pricingApi, showApiError } from "@/lib/api";

const inp = "mt-1 w-full px-2 py-1.5 border border-brand-navy/20 bg-white text-xs";

const FeeRow = ({ it, val, setVal, ref_ }) => (
  <div className="grid md:grid-cols-[1fr_auto_1fr] gap-2 items-start py-2 border-b border-brand-navy/10" data-testid={`fee-plan-item-${it.code}-${ref_}`}>
    <div>
      <b>{it.name}</b>
      <div className="text-brand-navy/60">{it.has_rule ? `${it.rule_name}: ${it.rate}${it.estimate != null ? ` · est. ${it.currency} ${Number(it.estimate).toLocaleString()} on the budget` : ""}` : "No fee rule for this country / band"}</div>
    </div>
    <div className="flex gap-3">
      <label className="flex items-center gap-1"><input type="radio" checked={val.charge} disabled={!it.has_rule} onChange={() => setVal({ ...val, charge: true })} data-testid={`fee-plan-charge-${it.code}-${ref_}`} />Charge</label>
      <label className="flex items-center gap-1"><input type="radio" checked={!val.charge} onChange={() => setVal({ ...val, charge: false })} data-testid={`fee-plan-waive-${it.code}-${ref_}`} />Waive</label>
    </div>
    {!val.charge && it.has_rule
      ? <input className={inp} placeholder="Reason for waiving (required)" value={val.reason || ""} onChange={(e) => setVal({ ...val, reason: e.target.value })} data-testid={`fee-plan-reason-${it.code}-${ref_}`} />
      : <span />}
  </div>);

export const FeePlanPanel = ({ n, onSaved, onClose }) => {
  const [d, setD] = useState(null);
  const [tier, setTier] = useState(n.fee_plan?.tier || "");
  const [vals, setVals] = useState({});
  const [payer, setPayer] = useState(n.fee_plan?.award_payer || "");
  const [email, setEmail] = useState(n.fee_plan?.payer_email || "");
  useEffect(() => {
    pricingApi.feePlan(n.notice_ref, tier || undefined).then((r) => {
      setD(r);
      if (!tier && r.tier) setTier(r.tier);
      const saved = Object.fromEntries((r.saved?.items || []).map((i) => [i.code, { charge: i.charge, reason: i.reason }]));
      setVals(Object.fromEntries(r.items.map((i) => [i.code, saved[i.code] && (i.has_rule || !saved[i.code].charge) ? saved[i.code] : { charge: i.charge, reason: "" }])));
      setPayer((p) => p || r.award_payer_default);
    }).catch(showApiError);
  }, [n.notice_ref, tier]);
  if (!d) return <div className="text-xs p-3" data-testid={`fee-plan-loading-${n.notice_ref}`}>Loading fees…</div>;
  const award = vals.transaction?.charge;
  const emailBad = award && payer === "buyer" && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim());
  const reasonMissing = d.items.some((i) => i.has_rule && vals[i.code] && !vals[i.code].charge && !(vals[i.code].reason || "").trim());
  const save = () => {
    if (emailBad) return toast.error("Enter the buyer's billing email — the award fee link is sent there.", { id: "fee-plan" });
    if (reasonMissing) return toast.error("Give a reason for each waived fee.", { id: "fee-plan" });
    toast.dismiss("fee-plan");
    return pricingApi.saveFeePlan(n.notice_ref, { tier: tier || null, award_payer: payer, payer_email: email || null,
      items: Object.entries(vals).map(([code, v]) => ({ code, charge: v.charge, reason: v.reason || null })) })
      .then(() => { toast.success("Fees confirmed for this tender"); onSaved?.(); }).catch(showApiError);
  };
  return (
    <div className="mt-2 border border-brand-navy/20 bg-white p-3 text-xs" data-testid={`fee-plan-${n.notice_ref}`}>
      <div className="flex flex-wrap gap-4 items-end mb-2">
        <div><span className="pmc-label">Band</span><div className="font-semibold" data-testid={`fee-plan-band-${n.notice_ref}`}>{d.band?.name || "No band"} · {d.country || "no country"}</div></div>
        <label><span className="pmc-label">Buyer tier</span>
          <select className={inp} value={tier} onChange={(e) => setTier(e.target.value)} data-testid={`fee-plan-tier-${n.notice_ref}`}>
            <option value="">Any / not set</option>{d.tiers.map((t) => <option key={t}>{t}</option>)}</select></label>
      </div>
      {d.items.map((it) => <FeeRow key={it.code} it={it} ref_={n.notice_ref} val={vals[it.code] || { charge: false }} setVal={(v) => setVals({ ...vals, [it.code]: v })} />)}
      {award && (
        <div className="py-2 grid md:grid-cols-2 gap-3" data-testid={`fee-plan-award-${n.notice_ref}`}>
          <div><span className="pmc-label">Who pays the award fee?</span>
            <div className="flex gap-3 mt-1">
              <label className="flex items-center gap-1"><input type="radio" checked={payer === "buyer"} onChange={() => setPayer("buyer")} data-testid={`fee-plan-payer-buyer-${n.notice_ref}`} />Buyer</label>
              <label className="flex items-center gap-1"><input type="radio" checked={payer === "supplier"} onChange={() => setPayer("supplier")} data-testid={`fee-plan-payer-supplier-${n.notice_ref}`} />Winning supplier (shown to bidders)</label>
            </div></div>
          {payer === "buyer" && <label><span className="pmc-label">Buyer billing email (payment link goes here)</span>
            <input className={inp} value={email} onChange={(e) => setEmail(e.target.value)} placeholder="accounts@buyer.com" data-testid={`fee-plan-email-${n.notice_ref}`} />
            {emailBad && <span className="text-red-700" data-testid={`fee-plan-email-error-${n.notice_ref}`}>Billing email is required when the buyer pays.</span>}</label>}
        </div>)}
      <div className="flex justify-end gap-2 mt-2">
        {onClose && <button className="px-3 py-1 border border-brand-navy/30 uppercase tracking-widest text-[10px]" onClick={onClose} data-testid={`fee-plan-close-${n.notice_ref}`}>Close</button>}
        <button className="px-3 py-1 bg-brand-navy text-white uppercase tracking-widest text-[10px]" onClick={save} data-testid={`fee-plan-save-${n.notice_ref}`}>Confirm fees</button>
      </div>
    </div>);
};
