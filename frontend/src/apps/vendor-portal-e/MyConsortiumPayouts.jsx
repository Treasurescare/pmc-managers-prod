import { useEffect, useState } from "react";
import { consortiumApi } from "@/lib/api";

const STATUS = { awaiting_signatures: "Waiting for officer signatures", approved: "Approved — payment being made", paid: "Paid", pending_payout: "Waiting for officer signatures" };

export default function MyConsortiumPayouts() {
  const [items, setItems] = useState([]);
  useEffect(() => { consortiumApi.myPayouts().then((r) => setItems(r.items || [])).catch(() => {}); }, []);
  if (!items.length) return null;
  return (
    <div className="mt-8 space-y-2" data-testid="my-consortium-payouts">
      <div className="pmc-eyebrow">My consortium payments</div>
      <div className="overflow-x-auto bg-white border">
        <table className="w-full text-sm text-slate-900"><thead><tr className="text-left text-xs text-slate-600">
          <th className="p-2">Payment</th><th>Consortium · bid</th><th>Your share</th><th>To your account</th><th>Officer signatures</th><th>Status</th></tr></thead>
          <tbody>{items.map((x) => (
            <tr key={x.instruction_ref} className="border-t align-top" data-testid={`payout-${x.instruction_ref}`}>
              <td className="p-2 font-mono text-xs">{x.instruction_ref}<div className="text-slate-500">{(x.released_at || "").slice(0, 10)}</div></td>
              <td>{x.consortium}<div className="text-xs text-slate-500">{x.bid_ref} · {x.notice_ref}</div></td>
              <td><b>{x.currency} {Number(x.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}</b><div className="text-xs text-slate-500">{x.share_pct}%</div></td>
              <td className="text-xs">{x.bank?.bank_name || "—"}{x.bank?.account_last4 ? ` ····${x.bank.account_last4}` : ""}</td>
              <td className="text-xs">{["PMC officer", "Escrow officer"].map((s) => {
                const g = x.signatures.find((y) => y.side === s);
                return <div key={s}>{s}: {g ? `✓ ${(g.at || "").slice(0, 10)}` : "pending"}</div>;
              })}</td>
              <td className="text-xs" data-testid={`payout-status-${x.instruction_ref}`}><b>{STATUS[x.status] || x.status}</b>
                {x.status === "paid" && <div>Bank ref {x.paid_ref} · {(x.paid_at || "").slice(0, 10)}</div>}</td>
            </tr>))}</tbody></table>
      </div>
    </div>);
}
