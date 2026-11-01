import { useEffect, useState } from "react";
import { toast } from "sonner";
import { criteriaApi, showApiError } from "@/lib/api";

const Lines = ({ s, tid, onPaid }) => (
  <table className="w-full text-xs mt-1 table-fixed"><colgroup><col className="w-1/4" /><col className="w-16" /><col className="w-1/6" /><col /><col className="w-32" /></colgroup><tbody>
    {s.lines.map((x, i) => (
      <tr key={x.vendor_id || i} className="border-t" data-testid={`split-line-${tid}-${i}`}>
        <td className="py-1">{x.company}{x.lead ? " (lead)" : ""}</td><td>{x.share_pct}%</td>
        <td className="font-semibold">{x.currency} {Number(x.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
        <td className="text-brand-navy/70">{x.route}</td>
        <td className="text-right">{onPaid ? (x.status === "paid" ? <span className="text-emerald-800">Paid · {x.paid_ref}</span>
          : <button type="button" className="pmc-btn pmc-btn--secondary" onClick={() => onPaid(i)} data-testid={`split-paid-${tid}-${i}`}>Mark paid</button>) : null}</td>
      </tr>))}
  </tbody></table>);

export default function ConsortiumSplitBox({ tid, status }) {
  const [s, setS] = useState(null);
  useEffect(() => { criteriaApi.consortiumSplit(tid).then(setS).catch(() => setS(null)); }, [tid, status]);
  if (!s || (!s.recorded && !s.applies)) return null;
  const paid = async (i) => {
    const ref = window.prompt("Payment reference (bank / wire number)");
    if (!ref) return;
    try { setS(await criteriaApi.splitPaid(tid, i, ref)); toast.success("Marked paid"); } catch (e) { showApiError(e); }
  };
  return (
    <div className="mt-3 border border-brand-navy/15 p-2 bg-brand-pale/40" data-testid={`consortium-split-${tid}`}>
      {s.recorded ? <>
        <div className="text-xs font-semibold">Consortium split · {s.consortium} · {s.basis}</div>
        <Lines s={s} tid={tid} onPaid={paid} />
      </> : <>
        <div className="text-xs font-semibold">Consortium bid — on release the money is split automatically:</div>
        <div className="text-[11px] mt-1">If released to the contractor</div><Lines s={s.preview.release_to_contractor} tid={`${tid}-c`} />
        <div className="text-[11px] mt-1">If refunded</div><Lines s={s.preview.release_to_vendor} tid={`${tid}-r`} />
      </>}
    </div>);
}
