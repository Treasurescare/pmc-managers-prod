import { useEffect, useState } from "react";
import { toast } from "sonner";
import { escrowMagicApi, showApiError } from "@/lib/api";
import { Instructions } from "@/apps/admin-console/escrow/ConsortiumSplitBox";

export default function MagicSplitSection({ token }) {
  const [items, setItems] = useState([]);
  const load = () => escrowMagicApi.splits(token).then((r) => setItems(r.items || [])).catch(() => setItems([]));
  useEffect(() => { load(); }, [token]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!items.length) return null;
  const actFor = (tid) => {
    const act = async (kind, i) => {
      if (kind !== "sign") return;
      const c = window.prompt("Comment (optional) — press OK to sign", "");
      if (c === null) return;
      try { await escrowMagicApi.signSplit(token, tid, i, c || null); toast.success("Payment instruction signed"); load(); }
      catch (e) { showApiError(e); }
    };
    act.canPay = false;
    return act;
  };
  return (
    <div className="mt-10 space-y-4" data-testid="magic-split-section">
      <div className="pmc-label">Consortium payment instructions</div>
      <p className="text-sm text-brand-navy/60">Each member's share needs your signature and the other officer's before PMC can make and record the bank payment.</p>
      {items.map((s) => (
        <div key={s.tid} className="bg-white border border-brand-navy/15 p-3" data-testid={`magic-split-${s.tid}`}>
          <div className="text-xs font-semibold">{s.bid_ref} · {s.consortium} · total {s.lines[0]?.currency} {Number(s.total).toLocaleString()}</div>
          <Instructions s={s} tid={s.tid} act={actFor(s.tid)} />
        </div>))}
    </div>);
}
