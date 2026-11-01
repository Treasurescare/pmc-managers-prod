import { useEffect, useState } from "react";
import { toast } from "sonner";
import { criteriaApi, uploadsApi, showApiError } from "@/lib/api";

const money = (x) => `${x.currency} ${Number(x.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
const SIDE = { pmc: "PMC officer", escrow_institution: "Escrow officer" };

const Instruction = ({ x, i, tid, act }) => {
  const b = x.bank || {};
  const sigs = x.signatures || {};
  return (
    <div className="border-t py-2 text-xs space-y-1" data-testid={`split-line-${tid}-${i}`}>
      <div className="flex justify-between flex-wrap gap-2">
        <div><b>{x.instruction_ref}</b> · {x.company}{x.lead ? " (lead)" : ""} · {x.share_pct}% · <b>{money(x)}</b></div>
        <span className="uppercase tracking-widest text-[10px]" data-testid={`split-status-${tid}-${i}`}>{(x.status || "").replace(/_/g, " ")}</span>
      </div>
      <div className="text-brand-navy/70">{x.route}</div>
      <div data-testid={`split-bank-${tid}-${i}`}>{b.bank_account_number ? `Pay to: ${b.bank_name || ""} ${b.bank_branch || ""} · A/c ${b.bank_account_number} · SWIFT ${b.bank_swift || "—"}` : <span className="text-red-700">No bank account on file for this member</span>}</div>
      <div>{["pmc", "escrow_institution"].map((s) => <span key={s} className="mr-3">{SIDE[s]}: {sigs[s] ? `✓ ${sigs[s].email}` : "not signed"}</span>)}</div>
      {x.status === "paid" ? <div className="text-emerald-800">Paid · ref {x.paid_ref} · {(x.paid_at || "").slice(0, 10)}</div> : (
        <div className="flex gap-2">
          {x.status !== "approved" && <button type="button" className="pmc-btn pmc-btn--secondary" onClick={() => act("sign", i)} data-testid={`split-sign-${tid}-${i}`}>Sign payment instruction</button>}
          {x.status === "approved" && <label className="pmc-btn pmc-btn--primary cursor-pointer" data-testid={`split-paid-${tid}-${i}`}>Record bank payment (attach slip)
            <input type="file" hidden onChange={(e) => e.target.files?.[0] && act("paid", i, e.target.files[0])} data-testid={`split-proof-${tid}-${i}`} /></label>}
        </div>)}
    </div>);
};

const Preview = ({ s }) => (
  <table className="w-full text-xs mt-1 table-fixed"><tbody>
    {s.lines.map((x, i) => <tr key={x.vendor_id || i} className="border-t"><td className="py-1 w-1/3">{x.company}{x.lead ? " (lead)" : ""}</td><td className="w-16">{x.share_pct}%</td><td className="font-semibold">{money(x)}</td></tr>)}
  </tbody></table>);

export default function ConsortiumSplitBox({ tid, status }) {
  const [s, setS] = useState(null);
  useEffect(() => { criteriaApi.consortiumSplit(tid).then(setS).catch(() => setS(null)); }, [tid, status]);
  if (!s || (!s.recorded && !s.applies)) return null;
  const act = async (kind, i, file) => {
    try {
      if (kind === "sign") { setS(await criteriaApi.splitSign(tid, i, window.prompt("Comment (optional)") || null)); toast.success("Signed"); return; }
      const ref = window.prompt("Bank / wire reference for this payment");
      if (!ref) return;
      const p = await uploadsApi.presign(file.name, file.type || "application/pdf", "vendor-docs", file.size);
      const r = await uploadsApi.direct(p.key, file);
      setS(await criteriaApi.splitPaid(tid, i, ref, r?.key || p.key)); toast.success("Payment recorded");
    } catch (e) { showApiError(e); }
  };
  return (
    <div className="mt-3 border border-brand-navy/15 p-2 bg-brand-pale/40" data-testid={`consortium-split-${tid}`}>
      {s.recorded ? <>
        <div className="text-xs font-semibold">Consortium payment instructions · {s.consortium} · {s.basis}</div>
        <div className="text-[11px] text-brand-navy/70">Each member's payment must be signed by both escrow officers before the bank payment can be recorded with its slip.</div>
        {s.lines.map((x, i) => <Instruction key={x.instruction_ref || i} x={x} i={i} tid={tid} act={act} />)}
      </> : <>
        <div className="text-xs font-semibold">Consortium bid — on release the money is split automatically:</div>
        <div className="text-[11px] mt-1">If released to the contractor</div><Preview s={s.preview.release_to_contractor} />
        <div className="text-[11px] mt-1">If refunded</div><Preview s={s.preview.release_to_vendor} />
      </>}
    </div>);
}
