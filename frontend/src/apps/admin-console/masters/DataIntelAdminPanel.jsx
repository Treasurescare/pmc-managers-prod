import { useEffect, useState } from "react";
import { toast } from "sonner";
import { extraPayApi, showApiError } from "@/lib/api";

const Row = ({ r, reload }) => {
  const [amt, setAmt] = useState(r.amount || r.suggested_amount || "");
  const [cur, setCur] = useState(r.currency || r.suggested_currency || "USD");
  const [sum, setSum] = useState("");
  const [link, setLink] = useState("");
  const run = async (fn, msg) => { try { await fn(); toast.success(msg); reload(); } catch (e) { showApiError(e); } };
  return (
    <div className="p-4 border-t border-brand-navy/10 text-sm" data-testid={`intel-admin-row-${r.id}`}>
      <div><b>{r.subject}</b> · {r.kind === "vendor_report" ? "Vendor report" : "Market insights"} · {r.company_name} ({r.vendor_ref}) · <span className="uppercase text-xs font-semibold">{r.status}</span></div>
      <div className="text-xs text-brand-navy/60">{[r.category, r.country, r.notes].filter(Boolean).join(" · ")}</div>
      {["requested", "quoted"].includes(r.status) && (
        <div className="flex gap-2 mt-2 items-center flex-wrap">
          <input type="number" value={amt} onChange={(e) => setAmt(e.target.value)} className="px-2 py-1 border w-28" data-testid={`intel-amount-${r.id}`} />
          <input value={cur} maxLength={3} onChange={(e) => setCur(e.target.value.toUpperCase())} className="px-2 py-1 border w-16" data-testid={`intel-currency-${r.id}`} />
          {r.suggested_amount && <span className="text-xs text-brand-navy/50">Fee rule: {r.suggested_currency} {r.suggested_amount}</span>}
          <button className="px-3 py-1 text-[10px] uppercase tracking-widest bg-brand-navy text-white" data-testid={`intel-quote-${r.id}`}
            onClick={() => run(() => extraPayApi.intelQuote(r.id, { amount: Number(amt), currency: cur }), "Quote emailed with payment link")}>Send quote + pay link</button>
          <button className="px-3 py-1 text-[10px] uppercase tracking-widest border border-red-300 text-red-700" data-testid={`intel-decline-${r.id}`}
            onClick={() => { const n = window.prompt("Reason for declining"); if (n) run(() => extraPayApi.intelDecline(r.id, n), "Declined"); }}>Decline</button>
        </div>
      )}
      {r.status === "paid" && (
        <div className="grid gap-2 mt-2 max-w-2xl">
          <textarea rows={3} value={sum} onChange={(e) => setSum(e.target.value)} placeholder="Findings / summary for the vendor" className="px-2 py-1 border" data-testid={`intel-summary-${r.id}`} />
          <input value={link} onChange={(e) => setLink(e.target.value)} placeholder="Report link (optional)" className="px-2 py-1 border" data-testid={`intel-link-${r.id}`} />
          <div><button className="px-3 py-1 text-[10px] uppercase tracking-widest bg-emerald-700 text-white" data-testid={`intel-deliver-${r.id}`}
            onClick={() => run(() => extraPayApi.intelDeliver(r.id, { summary: sum, link_url: link || null }), "Delivered")}>Deliver</button></div>
        </div>
      )}
    </div>
  );
};

export default function DataIntelAdminPanel() {
  const [rows, setRows] = useState([]);
  const load = () => extraPayApi.intelAdmin().then((r) => setRows(r.items || [])).catch(showApiError);
  useEffect(() => { load(); }, []);
  return (
    <div className="bg-white border border-brand-navy/10" data-testid="intel-admin-panel">
      <div className="p-4 text-sm text-brand-navy/60">Vendors request market insights or vendor reports. Quote a price (prefilled from the Data intel fee rule), the vendor pays by link, then deliver the findings.</div>
      {rows.length === 0 ? <div className="p-4 text-sm">No requests yet.</div> : rows.map((r) => <Row key={r.id} r={r} reload={load} />)}
    </div>
  );
}
