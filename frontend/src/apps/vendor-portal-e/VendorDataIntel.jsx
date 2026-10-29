import { useEffect, useState } from "react";
import { toast } from "sonner";
import { extraPayApi, showApiError } from "@/lib/api";
import VendorPortalChrome from "./VendorPortalChrome";

const KINDS = { market_insights: "Market insights (awards, winning prices, competitors)", vendor_report: "Vendor report (ratings, past work, blacklist checks)" };
const EMPTY = { kind: "market_insights", subject: "", category: "", country: "", notes: "" };

export default function VendorDataIntel() {
  const [rows, setRows] = useState([]);
  const [f, setF] = useState(EMPTY);
  const load = () => extraPayApi.intelMine().then((r) => setRows(r.items || [])).catch(() => {});
  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("session_id")) {
      const sid = new URLSearchParams(window.location.search).get("session_id");
      extraPayApi.payStatus(sid).then((s) => { if (s.payment_status === "paid") toast.success("Paid — PMC will deliver your report soon."); window.history.replaceState({}, "", "/vendor/data-intel"); load(); });
    } else load();
  }, []);
  const submit = async () => {
    if (f.subject.trim().length < 3) return toast.error("Describe what you need");
    try { await extraPayApi.intelCreate({ ...f, category: f.category || null, country: f.country || null, notes: f.notes || null }); toast.success("Request sent to PMC — you'll get a quote by email"); setF(EMPTY); load(); }
    catch (e) { showApiError(e); }
  };
  const pay = async (id) => { try { const r = await extraPayApi.intelPay(id); window.location.href = r.checkout_url; } catch (e) { showApiError(e); } };
  const inp = "pmc-input"; 
  return (
    <div data-testid="vendor-data-intel">
      <VendorPortalChrome active="/vendor/data-intel">
        <div className="sp-head"><div><div className="pmc-eyebrow">Services</div><h1>Data intel</h1></div></div>
        <section className="pmc-panel" style={{ padding: "16px", marginBottom: "16px" }}>
          <div style={{ display: "grid", gap: "10px", maxWidth: "720px" }}>
            <select className={inp} value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })} data-testid="intel-kind">
              {Object.entries(KINDS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
            <input className={inp} placeholder={f.kind === "vendor_report" ? "Which vendor? (name or reference)" : "What do you want to know? e.g. HVAC awards in Kazakhstan 2025"} value={f.subject} onChange={(e) => setF({ ...f, subject: e.target.value })} data-testid="intel-subject" />
            <div style={{ display: "flex", gap: "10px" }}>
              <input className={inp} placeholder="Category (optional)" value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })} data-testid="intel-category" />
              <input className={inp} placeholder="Country code (optional, e.g. KZ)" maxLength={3} value={f.country} onChange={(e) => setF({ ...f, country: e.target.value.toUpperCase() })} data-testid="intel-country" />
            </div>
            <textarea className={inp} rows={3} placeholder="Anything else PMC should know" value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} data-testid="intel-notes" />
            <div><button className="pmc-btn pmc-btn--primary" onClick={submit} data-testid="intel-submit">Request from PMC</button></div>
          </div>
        </section>
        <section className="pmc-panel" data-testid="intel-list">
          <div className="pmc-panel__head"><h2 className="pmc-panel__title">My requests</h2></div>
          {rows.length === 0 ? <div className="pmc-panel__body pmc-muted">No requests yet.</div> : rows.map((r) => (
            <div key={r.id} className="pmc-panel__body" style={{ borderTop: "1px solid var(--line)" }} data-testid={`intel-row-${r.id}`}>
              <b>{r.subject}</b> <span className="pmc-muted">· {KINDS[r.kind]?.split(" (")[0]} · {r.status}</span>
              {r.status === "quoted" && <div style={{ marginTop: "6px" }}>Quote: <b>{r.currency} {Number(r.amount).toLocaleString()}</b> <button className="pmc-btn pmc-btn--primary pmc-btn--sm" onClick={() => pay(r.id)} data-testid={`intel-pay-${r.id}`}>Pay</button></div>}
              {r.status === "delivered" && <div style={{ marginTop: "6px", whiteSpace: "pre-wrap" }} data-testid={`intel-delivery-${r.id}`}>{r.delivery?.summary}{r.delivery?.link_url && <> — <a href={r.delivery.link_url} target="_blank" rel="noreferrer">Open report</a></>}</div>}
              {r.status === "declined" && <div className="pmc-muted" style={{ marginTop: "6px" }}>Declined: {r.decision_notes}</div>}
            </div>
          ))}
        </section>
      </VendorPortalChrome>
    </div>
  );
}
