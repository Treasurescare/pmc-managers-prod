import { useEffect, useState, useCallback } from "react";
import { useUiTheme } from "@/context/UiThemeContext";
import { toast } from "sonner";
import { governanceApi } from "@/lib/api";
import AdminShellE from "./AdminShellE";
import AdminAvatarMenu from "./AdminAvatarMenu";

const TABS = [
  ["exceptions", "Exceptions register"],
  ["buyer", "Buyer classification"],
  ["integrity", "Integrity & collusion"],
  ["fees", "Fee waivers"],
  ["legal", "Legal register"],
  ["incidents", "Incidents & SLA"],
];

const Panel = ({ title, children, action }) => (
  <section className="pmc-panel" style={{ marginBottom: "20px" }}>
    <div className="pmc-panel__head"><h2 className="pmc-panel__title">{title}</h2>{action}</div>
    <div style={{ padding: "16px" }}>{children}</div>
  </section>
);

const Field = ({ label, children }) => (
  <div className="pmc-field" style={{ marginBottom: "10px" }}>
    <label style={{ display: "block", fontSize: "12px", color: "var(--ink-muted)", marginBottom: "4px" }}>{label}</label>
    {children}
  </div>
);

const inp = { width: "100%", padding: "8px 10px", border: "1px solid var(--line)", borderRadius: "6px", fontSize: "13px" };

function err(e, fallback) {
  const d = e?.response?.data?.detail;
  toast.error(typeof d === "string" ? d : fallback);
}

// ---------- Exceptions ----------
function ExceptionsTab() {
  const [rows, setRows] = useState([]);
  const [kind, setKind] = useState("");
  const load = useCallback(() => governanceApi.listExceptions(kind || undefined).then((r) => setRows(r.items)).catch(() => {}), [kind]);
  useEffect(() => { load(); }, [load]);
  return (
    <Panel title="Manual exceptions register" action={
      <select style={{ ...inp, width: "200px" }} value={kind} onChange={(e) => setKind(e.target.value)} data-testid="exc-kind-filter">
        <option value="">All kinds</option>
        <option value="kyc_bypass">KYC bypass</option>
        <option value="fee_waiver">Fee waiver</option>
        <option value="buyer_classification_override">Buyer override</option>
        <option value="integrity_override">Integrity override</option>
        <option value="stage_skip">Stage skip</option>
      </select>}>
      <p className="pmc-muted" style={{ fontSize: "13px", marginBottom: "12px" }}>Every bypass, waiver and override — one reviewable, ledger-backed log.</p>
      {rows.length === 0 ? <div className="pmc-muted" data-testid="exc-empty">No exceptions recorded.</div> : (
        <table style={{ width: "100%", fontSize: "13px", borderCollapse: "collapse" }} data-testid="exc-table">
          <thead><tr style={{ textAlign: "left", borderBottom: "1px solid var(--line)" }}><th>Ref</th><th>Kind</th><th>Target</th><th>Actor</th><th>Reason</th><th>When</th></tr></thead>
          <tbody>{rows.map((r) => (
            <tr key={r.id} style={{ borderBottom: "1px solid var(--line)" }}>
              <td>{r.exception_ref}</td><td><span className="pmc-pill">{r.kind}</span></td>
              <td>{r.target_type}/{r.target_id}</td><td>{r.actor_email}</td>
              <td style={{ maxWidth: "240px" }}>{r.reason}</td><td>{(r.at || "").slice(0, 16).replace("T", " ")}</td>
            </tr>))}</tbody>
        </table>)}
    </Panel>
  );
}

// ---------- Buyer classification ----------
function BuyerTab() {
  const [rows, setRows] = useState([]);
  const [form, setForm] = useState({ notice_ref: "", buyer_name: "", buyer_type: "public_sector", basis: "" });
  const load = useCallback(() => governanceApi.listBuyerClassifications().then((r) => setRows(r.items)).catch(() => {}), []);
  useEffect(() => { load(); }, [load]);
  const submit = async () => {
    try { await governanceApi.classifyBuyer(form); toast.success("Classification saved (pending verification)"); setForm({ notice_ref: "", buyer_name: "", buyer_type: "public_sector", basis: "" }); load(); }
    catch (e) { err(e, "Could not save classification"); }
  };
  const verify = async (notice_ref, agree) => {
    try { await governanceApi.verifyBuyer({ notice_ref, agree }); toast.success(agree ? "Verified" : "Rejected"); load(); }
    catch (e) { err(e, "Could not verify"); }
  };
  return (
    <>
      <Panel title="Classify a buyer (public / private)">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
          <Field label="Notice ref"><input style={inp} data-testid="buyer-notice" value={form.notice_ref} onChange={(e) => setForm({ ...form, notice_ref: e.target.value })} /></Field>
          <Field label="Buyer name"><input style={inp} data-testid="buyer-name" value={form.buyer_name} onChange={(e) => setForm({ ...form, buyer_name: e.target.value })} /></Field>
          <Field label="Buyer type"><select style={inp} data-testid="buyer-type" value={form.buyer_type} onChange={(e) => setForm({ ...form, buyer_type: e.target.value })}><option value="public_sector">Public sector</option><option value="private_sector">Private sector</option></select></Field>
          <Field label="Basis / evidence"><input style={inp} data-testid="buyer-basis" value={form.basis} onChange={(e) => setForm({ ...form, basis: e.target.value })} /></Field>
        </div>
        <button className="pmc-btn pmc-btn--primary" data-testid="buyer-submit" onClick={submit}>Save classification</button>
        <p className="pmc-muted" style={{ fontSize: "12px", marginTop: "8px" }}>A second officer must verify — the classifier cannot verify their own entry.</p>
      </Panel>
      <Panel title="Classifications">
        {rows.length === 0 ? <div className="pmc-muted" data-testid="buyer-empty">Nothing classified yet.</div> : (
          <table style={{ width: "100%", fontSize: "13px", borderCollapse: "collapse" }} data-testid="buyer-table">
            <thead><tr style={{ textAlign: "left", borderBottom: "1px solid var(--line)" }}><th>Notice</th><th>Buyer</th><th>Type</th><th>Status</th><th>By / Verified</th><th></th></tr></thead>
            <tbody>{rows.map((r) => (
              <tr key={r.id} style={{ borderBottom: "1px solid var(--line)" }}>
                <td>{r.notice_ref}</td><td>{r.buyer_name}</td>
                <td><span className="pmc-pill">{r.buyer_type === "public_sector" ? "Public" : "Private"}</span></td>
                <td><span className={"pmc-pill " + (r.status === "verified" ? "pmc-pill--success" : r.status === "rejected" ? "pmc-pill--danger" : "pmc-pill--warning")}>{r.status}</span></td>
                <td style={{ fontSize: "11px" }}>{r.classified_by}<br />{r.verified_by || "—"}</td>
                <td>{r.status === "pending_verification" && (<span style={{ display: "flex", gap: "6px" }}><button className="pmc-btn pmc-btn--sm pmc-btn--primary" data-testid={`buyer-verify-${r.notice_ref}`} onClick={() => verify(r.notice_ref, true)}>Verify</button><button className="pmc-btn pmc-btn--sm pmc-btn--secondary" data-testid={`buyer-reject-${r.notice_ref}`} onClick={() => verify(r.notice_ref, false)}>Reject</button></span>)}</td>
              </tr>))}</tbody>
          </table>)}
      </Panel>
    </>
  );
}

// ---------- Integrity & collusion ----------
function IntegrityTab() {
  const [rows, setRows] = useState([]);
  const [form, setForm] = useState({ notice_ref: "", title: "", reason: "" });
  const [colRef, setColRef] = useState("");
  const [col, setCol] = useState(null);
  const load = useCallback(() => governanceApi.listIntegrityCases().then((r) => setRows(r.items)).catch(() => {}), []);
  useEffect(() => { load(); }, [load]);
  const raise = async () => {
    try { await governanceApi.raiseIntegrity(form); toast.success("Integrity case raised"); setForm({ notice_ref: "", title: "", reason: "" }); load(); }
    catch (e) { err(e, "Could not raise case"); }
  };
  const act = async (fn, label) => { try { await fn(); toast.success(label); load(); } catch (e) { err(e, "Action failed"); } };
  const scan = async () => { try { const r = await governanceApi.collusion(colRef); setCol(r); } catch (e) { err(e, "Scan failed"); } };
  return (
    <>
      <Panel title="Collusion indicators (human review only)">
        <div style={{ display: "flex", gap: "8px", alignItems: "flex-end" }}>
          <div style={{ flex: 1 }}><Field label="Notice ref"><input style={inp} data-testid="col-notice" value={colRef} onChange={(e) => setColRef(e.target.value)} /></Field></div>
          <button className="pmc-btn pmc-btn--primary" data-testid="col-scan" onClick={scan}>Scan</button>
        </div>
        {col && (<div data-testid="col-result" style={{ marginTop: "10px" }}>
          <p className="pmc-muted" style={{ fontSize: "13px" }}>{col.bidder_count} bidders · {col.flag_count} indicator(s). {col.disclaimer}</p>
          {(col.flags || []).map((f, i) => (<div key={i} style={{ padding: "8px", border: "1px solid var(--line)", borderRadius: "6px", marginTop: "6px" }}><span className={"pmc-pill " + (f.severity === "high" ? "pmc-pill--danger" : "pmc-pill--warning")}>{f.severity}</span> {f.message}</div>))}
        </div>)}
      </Panel>
      <Panel title="Raise an integrity hold">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
          <Field label="Notice ref"><input style={inp} data-testid="int-notice" value={form.notice_ref} onChange={(e) => setForm({ ...form, notice_ref: e.target.value })} /></Field>
          <Field label="Title"><input style={inp} data-testid="int-title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></Field>
        </div>
        <Field label="Reason"><textarea style={{ ...inp, height: "60px" }} data-testid="int-reason" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} /></Field>
        <button className="pmc-btn pmc-btn--primary" data-testid="int-raise" onClick={raise}>Raise case</button>
      </Panel>
      <Panel title="Integrity cases">
        {rows.length === 0 ? <div className="pmc-muted" data-testid="int-empty">No integrity cases.</div> : rows.map((r) => (
          <div key={r.id} style={{ padding: "12px", border: "1px solid var(--line)", borderRadius: "6px", marginBottom: "8px" }} data-testid={`int-case-${r.case_ref}`}>
            <div style={{ display: "flex", justifyContent: "space-between" }}><b>{r.title}</b><span className={"pmc-pill " + (r.status === "overridden" ? "pmc-pill--danger" : r.status === "open" || r.status === "under_review" ? "pmc-pill--warning" : "pmc-pill--success")}>{r.status}</span></div>
            <div className="pmc-muted" style={{ fontSize: "12px" }}>{r.case_ref} · notice {r.notice_ref} · {r.reason}</div>
            {r.senior_override && <div style={{ fontSize: "12px", color: "var(--danger, #b00)", marginTop: "4px" }}>Senior override by {r.senior_override.by}: {r.senior_override.reason} (disclosed)</div>}
            {["open", "under_review"].includes(r.status) && (
              <div style={{ display: "flex", gap: "6px", marginTop: "8px", flexWrap: "wrap" }}>
                <button className="pmc-btn pmc-btn--sm pmc-btn--secondary" data-testid={`int-vote-uphold-${r.case_ref}`} onClick={() => act(() => governanceApi.reviewIntegrity({ case_ref: r.case_ref, vote: "uphold" }), "Vote recorded")}>Vote uphold</button>
                <button className="pmc-btn pmc-btn--sm pmc-btn--secondary" data-testid={`int-vote-dismiss-${r.case_ref}`} onClick={() => act(() => governanceApi.reviewIntegrity({ case_ref: r.case_ref, vote: "dismiss" }), "Vote recorded")}>Vote dismiss</button>
                <button className="pmc-btn pmc-btn--sm pmc-btn--primary" data-testid={`int-resolve-uphold-${r.case_ref}`} onClick={() => act(() => governanceApi.resolveIntegrity({ case_ref: r.case_ref, resolution: "upheld" }), "Resolved")}>Resolve: uphold</button>
                <button className="pmc-btn pmc-btn--sm pmc-btn--primary" data-testid={`int-resolve-dismiss-${r.case_ref}`} onClick={() => act(() => governanceApi.resolveIntegrity({ case_ref: r.case_ref, resolution: "dismissed" }), "Resolved")}>Resolve: dismiss</button>
                <button className="pmc-btn pmc-btn--sm pmc-btn--danger" data-testid={`int-override-${r.case_ref}`} onClick={() => { const reason = window.prompt("Senior override reason (recorded & disclosed):"); if (reason && reason.length >= 10) act(() => governanceApi.overrideIntegrity({ case_ref: r.case_ref, decision: "dismissed", reason }), "Override recorded"); else if (reason) toast.error("Reason must be at least 10 characters"); }}>Senior override</button>
              </div>)}
          </div>))}
      </Panel>
    </>
  );
}

// ---------- Fee waivers ----------
function FeesTab() {
  const [rows, setRows] = useState([]);
  const [form, setForm] = useState({ subject_type: "vendor", subject_ref: "", fee_type: "", amount: 0, currency: "USD", reason: "" });
  const load = useCallback(() => governanceApi.listFeeWaivers().then((r) => setRows(r.items)).catch(() => {}), []);
  useEffect(() => { load(); }, [load]);
  const request = async () => {
    try { await governanceApi.requestFeeWaiver({ ...form, amount: Number(form.amount) }); toast.success("Waiver requested"); setForm({ subject_type: "vendor", subject_ref: "", fee_type: "", amount: 0, currency: "USD", reason: "" }); load(); }
    catch (e) { err(e, "Could not request waiver"); }
  };
  const decide = async (waiver_ref, decision) => { try { await governanceApi.decideFeeWaiver({ waiver_ref, decision }); toast.success(decision); load(); } catch (e) { err(e, "Could not decide"); } };
  return (
    <>
      <Panel title="Request a fee waiver">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px" }}>
          <Field label="Subject type"><select style={inp} data-testid="fw-subject-type" value={form.subject_type} onChange={(e) => setForm({ ...form, subject_type: e.target.value })}><option value="vendor">Vendor</option><option value="notice">Notice</option><option value="engagement">Engagement</option></select></Field>
          <Field label="Subject ref"><input style={inp} data-testid="fw-subject-ref" value={form.subject_ref} onChange={(e) => setForm({ ...form, subject_ref: e.target.value })} /></Field>
          <Field label="Fee type"><input style={inp} data-testid="fw-fee-type" value={form.fee_type} onChange={(e) => setForm({ ...form, fee_type: e.target.value })} /></Field>
          <Field label="Amount"><input style={inp} type="number" data-testid="fw-amount" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} /></Field>
          <Field label="Currency"><input style={inp} data-testid="fw-currency" value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })} /></Field>
          <Field label="Reason"><input style={inp} data-testid="fw-reason" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} /></Field>
        </div>
        <button className="pmc-btn pmc-btn--primary" data-testid="fw-request" onClick={request}>Request waiver</button>
        <p className="pmc-muted" style={{ fontSize: "12px", marginTop: "8px" }}>The approver must be a different person — the requester cannot approve their own waiver.</p>
      </Panel>
      <Panel title="Fee waivers">
        {rows.length === 0 ? <div className="pmc-muted" data-testid="fw-empty">No fee waivers.</div> : (
          <table style={{ width: "100%", fontSize: "13px", borderCollapse: "collapse" }} data-testid="fw-table">
            <thead><tr style={{ textAlign: "left", borderBottom: "1px solid var(--line)" }}><th>Ref</th><th>Subject</th><th>Fee</th><th>Amount</th><th>Status</th><th>Requested by</th><th></th></tr></thead>
            <tbody>{rows.map((r) => (
              <tr key={r.id} style={{ borderBottom: "1px solid var(--line)" }}>
                <td>{r.waiver_ref}</td><td>{r.subject_type}/{r.subject_ref}</td><td>{r.fee_type}</td><td>{r.currency} {r.amount}</td>
                <td><span className={"pmc-pill " + (r.status === "approved" ? "pmc-pill--success" : r.status === "rejected" ? "pmc-pill--danger" : "pmc-pill--warning")}>{r.status}</span></td>
                <td style={{ fontSize: "11px" }}>{r.requested_by}</td>
                <td>{r.status === "pending" && (<span style={{ display: "flex", gap: "6px" }}><button className="pmc-btn pmc-btn--sm pmc-btn--primary" data-testid={`fw-approve-${r.waiver_ref}`} onClick={() => decide(r.waiver_ref, "approved")}>Approve</button><button className="pmc-btn pmc-btn--sm pmc-btn--secondary" data-testid={`fw-reject-${r.waiver_ref}`} onClick={() => decide(r.waiver_ref, "rejected")}>Reject</button></span>)}</td>
              </tr>))}</tbody>
          </table>)}
      </Panel>
    </>
  );
}

// ---------- Legal register ----------
function LegalTab() {
  const [rows, setRows] = useState([]);
  const [form, setForm] = useState({ country: "", legal_status: "approved", counsel_note: "" });
  const load = useCallback(() => governanceApi.listLegalRegister().then((r) => setRows(r.items)).catch(() => {}), []);
  useEffect(() => { load(); }, [load]);
  const save = async () => {
    try { await governanceApi.upsertLegalRegister(form); toast.success("Legal register updated"); setForm({ country: "", legal_status: "approved", counsel_note: "" }); load(); }
    catch (e) { err(e, "Could not update"); }
  };
  return (
    <>
      <Panel title="Per-country legal approval (board-visible)">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
          <Field label="Country"><input style={inp} data-testid="legal-country" value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value })} /></Field>
          <Field label="Legal status"><select style={inp} data-testid="legal-status" value={form.legal_status} onChange={(e) => setForm({ ...form, legal_status: e.target.value })}><option value="approved">Approved</option><option value="pending">Pending</option><option value="blocked">Blocked</option></select></Field>
        </div>
        <Field label="Counsel note"><textarea style={{ ...inp, height: "60px" }} data-testid="legal-note" value={form.counsel_note} onChange={(e) => setForm({ ...form, counsel_note: e.target.value })} /></Field>
        <button className="pmc-btn pmc-btn--primary" data-testid="legal-save" onClick={save}>Save entry</button>
      </Panel>
      <Panel title="Legal register">
        {rows.length === 0 ? <div className="pmc-muted" data-testid="legal-empty">No countries recorded.</div> : (
          <table style={{ width: "100%", fontSize: "13px", borderCollapse: "collapse" }} data-testid="legal-table">
            <thead><tr style={{ textAlign: "left", borderBottom: "1px solid var(--line)" }}><th>Country</th><th>Status</th><th>Approved by</th><th>Note</th><th>Updated</th></tr></thead>
            <tbody>{rows.map((r) => (
              <tr key={r.id} style={{ borderBottom: "1px solid var(--line)" }}>
                <td>{r.country}</td><td><span className={"pmc-pill " + (r.legal_status === "approved" ? "pmc-pill--success" : r.legal_status === "blocked" ? "pmc-pill--danger" : "pmc-pill--warning")}>{r.legal_status}</span></td>
                <td style={{ fontSize: "11px" }}>{r.approved_by || r.updated_by}</td><td style={{ maxWidth: "240px" }}>{r.counsel_note}</td><td>{(r.updated_at || "").slice(0, 10)}</td>
              </tr>))}</tbody>
          </table>)}
      </Panel>
    </>
  );
}

// ---------- Incidents ----------
function IncidentsTab() {
  const [rows, setRows] = useState([]);
  const [form, setForm] = useState({ title: "", severity: "high", category: "bid_opening", impact: "", public_disclosure: true, public_statement: "" });
  const load = useCallback(() => governanceApi.listIncidents().then((r) => setRows(r.items)).catch(() => {}), []);
  useEffect(() => { load(); }, [load]);
  const create = async () => {
    try { await governanceApi.createIncident(form); toast.success("Incident logged"); setForm({ title: "", severity: "high", category: "bid_opening", impact: "", public_disclosure: true, public_statement: "" }); load(); }
    catch (e) { err(e, "Could not log incident"); }
  };
  const update = async (incident_ref, status) => { try { await governanceApi.updateIncident({ incident_ref, status }); toast.success(status === "resolved" ? "Incident resolved" : "Incident set to monitoring"); load(); } catch (e) { err(e, "Could not update"); } };
  return (
    <>
      <Panel title="Log an incident">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px" }}>
          <Field label="Title"><input style={inp} data-testid="inc-title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></Field>
          <Field label="Severity"><select style={inp} data-testid="inc-severity" value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })}><option>low</option><option>medium</option><option>high</option><option>critical</option></select></Field>
          <Field label="Category"><input style={inp} data-testid="inc-category" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} /></Field>
        </div>
        <Field label="Impact"><textarea style={{ ...inp, height: "50px" }} data-testid="inc-impact" value={form.impact} onChange={(e) => setForm({ ...form, impact: e.target.value })} /></Field>
        <Field label="Public statement (shown on Trust page if disclosed)"><textarea style={{ ...inp, height: "50px" }} data-testid="inc-statement" value={form.public_statement} onChange={(e) => setForm({ ...form, public_statement: e.target.value })} /></Field>
        <label style={{ fontSize: "13px", display: "flex", gap: "6px", alignItems: "center" }}><input type="checkbox" data-testid="inc-disclose" checked={form.public_disclosure} onChange={(e) => setForm({ ...form, public_disclosure: e.target.checked })} /> Disclose publicly</label>
        <button className="pmc-btn pmc-btn--primary" data-testid="inc-create" style={{ marginTop: "8px" }} onClick={create}>Log incident</button>
      </Panel>
      <Panel title="Incidents">
        {rows.length === 0 ? <div className="pmc-muted" data-testid="inc-empty">No incidents.</div> : rows.map((r) => (
          <div key={r.id} style={{ padding: "12px", border: "1px solid var(--line)", borderRadius: "6px", marginBottom: "8px" }} data-testid={`inc-row-${r.incident_ref}`}>
            <div style={{ display: "flex", justifyContent: "space-between" }}><b>{r.title}</b><span className={"pmc-pill " + (r.status === "resolved" ? "pmc-pill--success" : "pmc-pill--warning")}>{r.status}</span></div>
            <div className="pmc-muted" style={{ fontSize: "12px" }}>{r.incident_ref} · {r.severity} · {r.category} · {r.public_disclosure ? "public" : "internal"}</div>
            {r.status !== "resolved" && (<div style={{ display: "flex", gap: "6px", marginTop: "8px" }}><button className="pmc-btn pmc-btn--sm pmc-btn--secondary" data-testid={`inc-monitoring-${r.incident_ref}`} onClick={() => update(r.incident_ref, "monitoring")}>Monitoring</button><button className="pmc-btn pmc-btn--sm pmc-btn--primary" data-testid={`inc-resolve-${r.incident_ref}`} onClick={() => update(r.incident_ref, "resolved")}>Resolve</button></div>)}
          </div>))}
      </Panel>
    </>
  );
}

export default function AdminGovernanceE() {
  const { isE } = useUiTheme();
  const [tab, setTab] = useState("exceptions");
  if (!isE) return null;
  return (
    <div data-testid="admin-governance-e" data-pmc-e-page="admin-governance-e">
      <AdminShellE active="Governance & integrity" header={<>
        <div className="crumb">Money &amp; compliance / <b>Governance &amp; integrity</b></div>
        <label className="pmc-search"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Search tenders, bids, vendors, ledger events…" data-testid="gov-search-input" /><span className="pmc-kbd">Ctrl K</span></label>
        <div className="pmc-atop__r">
          <button className="pmc-btn pmc-btn--secondary" data-help-open="" data-testid="gov-help-btn"><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> Help</button>
          <button className="pmc-ib pmc-bell" aria-label="Alerts" data-testid="gov-bell-btn"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg><span className="pmc-bell__n">0</span></button>
          <AdminAvatarMenu />
        </div>
      </>}>
        <h1 className="pmc-display" style={{ fontSize: "30px", margin: "0 0 4px" }}>Governance &amp; integrity</h1>
        <p className="pmc-muted" style={{ fontSize: "14px", marginBottom: "16px" }}>Due-diligence controls: exceptions register, buyer classification, integrity committee, fee waivers, legal register and incident disclosure.</p>
        <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginBottom: "18px", borderBottom: "1px solid var(--line)", paddingBottom: "8px" }}>
          {TABS.map(([k, label]) => (
            <button key={k} className={"pmc-btn pmc-btn--sm " + (tab === k ? "pmc-btn--primary" : "pmc-btn--ghost")} data-testid={`gov-tab-${k}`} onClick={() => setTab(k)}>{label}</button>
          ))}
        </div>
        {tab === "exceptions" && <ExceptionsTab />}
        {tab === "buyer" && <BuyerTab />}
        {tab === "integrity" && <IntegrityTab />}
        {tab === "fees" && <FeesTab />}
        {tab === "legal" && <LegalTab />}
        {tab === "incidents" && <IncidentsTab />}
      </AdminShellE>
    </div>
  );
}
