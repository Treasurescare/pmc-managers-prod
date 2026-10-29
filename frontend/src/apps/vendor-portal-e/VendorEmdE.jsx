import { useEffect, useMemo, useState } from "react";
import { useUiTheme } from "@/context/UiThemeContext";
import { bidApi } from "@/lib/api";
import VendorPortalChrome from "./VendorPortalChrome";
import { VendorFeeReceipts } from "./VendorFeeReceipts";

const money = (c, n) => `${(c || "USD").toUpperCase()} ${Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
const sumByCurrency = (rows, key) => {
  const m = {};
  rows.forEach((b) => { const v = Number(b[key] || 0); if (v > 0) { const c = (b.emd_currency || "USD").toUpperCase(); m[c] = (m[c] || 0) + v; } });
  return Object.entries(m).map(([c, v]) => money(c, v)).join(" · ") || "—";
};
const STATUS = (b) => {
  if (b.emd_refund_state === "released") return ["Refunded", "ok"];
  if (b.emd_refund_state) return ["Refund pending", "warn"];
  if (b.status === "emd_pending") return ["Due", "warn"];
  if (Number(b.emd_paid_amount || 0) > 0) return ["Paid", "ok"];
  if (Number(b.emd_due_amount || 0) <= 0) return ["No EMD", "muted"];
  return [String(b.status || "").replace(/_/g, " "), "muted"];
};

const Kpi = ({ label, value, sub, testid, color }) => (
  <div data-testid={testid}><div className="l">{label}</div><div className="pmc-figure" style={color ? { color } : undefined}>{value}</div><div className="s">{sub}</div></div>
);

const DepositsTable = ({ bids }) => {
  const [st, setSt] = useState("all");
  const [cur, setCur] = useState("all");
  const withEmd = bids.filter((b) => Number(b.emd_due_amount || 0) > 0 || Number(b.emd_paid_amount || 0) > 0);
  const statuses = [...new Set(withEmd.map((b) => STATUS(b)[0]))];
  const currencies = [...new Set(withEmd.map((b) => (b.emd_currency || "USD").toUpperCase()))];
  const rows = withEmd.filter((b) => (st === "all" || STATUS(b)[0] === st) && (cur === "all" || (b.emd_currency || "USD").toUpperCase() === cur));
  return (
    <section className="pmc-panel" data-testid="vemd-deposits">
      <div className="pmc-panel__head"><h2 className="pmc-panel__title">All deposits</h2>
        <div style={{ display: "flex", gap: "8px" }}>
          <select className="pmc-input" value={st} onChange={(e) => setSt(e.target.value)} data-testid="vemd-status-filter">
            <option value="all">All statuses</option>{statuses.map((s) => <option key={s}>{s}</option>)}</select>
          <select className="pmc-input" value={cur} onChange={(e) => setCur(e.target.value)} data-testid="vemd-currency-filter">
            <option value="all">All currencies</option>{currencies.map((c) => <option key={c}>{c}</option>)}</select>
        </div></div>
      {rows.length === 0 ? <div className="pmc-panel__body pmc-muted" data-testid="vemd-deposits-empty">No EMD deposits yet. They appear here when you start a bid on a tender that needs one.</div> : (
        <table className="pmc-table"><thead><tr><th>Bid</th><th className="num">EMD</th><th>Status</th><th>Detail</th><th></th></tr></thead>
          <tbody>{rows.map((b) => {
            const [label, tone] = STATUS(b);
            const paid = Number(b.emd_paid_amount || 0) > 0;
            return (
              <tr key={b.id} data-bid-ref={b.bid_ref} data-testid={`vemd-row-${b.bid_ref}`}>
                <td><div style={{ fontWeight: 600 }}>{b.notice_title || b.notice_ref}</div><div className="pmc-ref">{b.bid_ref}</div></td>
                <td className="num">{money(b.emd_currency, paid ? b.emd_paid_amount : b.emd_due_amount)}</td>
                <td><span className={`pmc-pill pmc-pill--${tone}`}>{label}</span></td>
                <td className="pmc-muted" style={{ fontSize: "12px" }}>{b.status === "emd_pending" && b.submission_deadline ? `Closes ${String(b.submission_deadline).slice(0, 10)}` : (b.emd_refund_due_at ? `Refund due ${String(b.emd_refund_due_at).slice(0, 10)}` : "—")}</td>
                <td>{b.status === "emd_pending"
                  ? <a href="#" className="pmc-btn pmc-btn--primary pmc-btn--sm" data-testid={`vemd-pay-${b.bid_ref}`}>Pay EMD</a>
                  : paid && <a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm" data-vemd-receipt-bid={b.id} data-vemd-receipt-ref={b.bid_ref} data-testid={`vemd-receipt-${b.bid_ref}`}>Receipt (PDF)</a>}</td>
              </tr>
            );
          })}</tbody></table>
      )}
    </section>
  );
};

export default function VendorEmdE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  const [bids, setBids] = useState(null);
  useEffect(() => { if (isE) { bidApi.mine().then((r) => setBids(Array.isArray(r) ? r : [])).catch(() => setBids([])); } }, [isE]);
  const k = useMemo(() => {
    const b = bids || [];
    const due = b.filter((x) => x.status === "emd_pending");
    const held = b.filter((x) => Number(x.emd_paid_amount || 0) > 0 && x.emd_refund_state !== "released");
    const refunding = b.filter((x) => x.emd_refund_state && x.emd_refund_state !== "released");
    return { due, held, refunding, dueTotal: sumByCurrency(due, "emd_due_amount"), heldTotal: sumByCurrency(held, "emd_paid_amount"), refundTotal: sumByCurrency(refunding, "emd_paid_amount") };
  }, [bids]);
  if (!isE && Legacy) return <Legacy />;
  if (!isE) return null;
  return (
    <div data-testid="vendor-emd-e" data-pmc-e-page="vendor-emd-e">
      <VendorPortalChrome active="/vendor/emd">
        <div className="sp-head"><div><div className="pmc-eyebrow">EMD &amp; payments</div><h1>Deposits, fees and refunds</h1></div>
          <div style={{ display: "flex", gap: "8px" }}>
            <a href="#" className="pmc-btn pmc-btn--secondary" data-testid="vemd-statement"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg> Statement (PDF)</a>
            {k.due.length > 0 && <a href="#" className="pmc-btn pmc-btn--primary" data-testid="vemd-pay-top">Pay EMD</a>}
          </div></div>
        {bids === null ? <div className="pmc-muted" data-testid="vemd-loading">Loading your payments…</div> : (<>
          <div className="sp-kpis" data-testid="vemd-kpis">
            <Kpi testid="vemd-kpi-due" label="Due now" value={k.dueTotal} sub={`${k.due.length} bid${k.due.length === 1 ? "" : "s"} awaiting EMD`} color={k.due.length ? "var(--warning)" : undefined} />
            <Kpi testid="vemd-kpi-held" label="Held in escrow" value={k.heldTotal} sub={`${k.held.length} deposit${k.held.length === 1 ? "" : "s"}`} />
            <Kpi testid="vemd-kpi-refund" label="Refunds in progress" value={k.refundTotal} sub={`${k.refunding.length} pending`} />
          </div>
          <VendorFeeReceipts />
          <DepositsTable bids={bids} />
        </>)}
        <section className="pmc-panel" style={{ marginTop: "16px" }}><div className="pmc-panel__head"><h2 className="pmc-panel__title">How release works</h2></div><div className="pmc-panel__body"><div className="pmc-timeline">
          <div><span className="dot"></span><div><b>Escrow confirms receipt</b><span>Your bid moves to sign &amp; seal</span></div></div>
          <div><span className="dot"></span><div><b>Admin, certifier, legal, accounts clear</b><span>Each step is on the ledger</span></div></div>
          <div><span className="dot"></span><div><b>Not awarded → refunded</b><span>To your refund account after the award</span></div></div>
          <div><span className="dot"></span><div><b>Awarded → security deposit</b><span>Converted on contract signature</span></div></div></div></div></section>
      </VendorPortalChrome>
    </div>
  );
}
