import { useEffect, useState, useCallback } from "react";
import { useUiTheme } from "@/context/UiThemeContext";
import { toast } from "sonner";
import { vendorTenderApi, showApiError } from "@/lib/api";
import VendorPortalChrome from "./VendorPortalChrome";
import CriteriaEditorModal from "@/apps/admin-console/notice/CriteriaEditorModal";

const EMPTY = {
  title: "", description: "", category: "", document_type: "tender",
  delivery_country: "KZ", submission_deadline: "", budget_currency: "USD",
  budget_amount: "", pre_bid_meeting_date: "", required_licenses: "", contact_name: "", contact_email: "",
};
const inp = { width: "100%", padding: "9px 11px", border: "1px solid var(--line)", borderRadius: "6px", fontSize: "13px" };
const STATUS_LABEL = {
  draft: "Draft", submitted: "Awaiting PMC review", changes_requested: "Changes requested",
  approved: "Approved & published", rejected: "Rejected",
};

export default function VendorTenderBuilderE() {
  const { isE } = useUiTheme();
  const [sub, setSub] = useState(null);
  const [tenders, setTenders] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [editingRef, setEditingRef] = useState(null);
  const [critRef, setCritRef] = useState(null);
  const [busy, setBusy] = useState(false);

  const loadMine = useCallback(() => vendorTenderApi.mine().then((r) => setTenders(r.items || [])).catch(() => {}), []);
  const loadSub = useCallback(() => vendorTenderApi.subscription().then(setSub).catch(() => {}), []);

  useEffect(() => {
    loadSub(); loadMine();
    const params = new URLSearchParams(window.location.search);
    const sid = params.get("sub_session");
    if (sid) {
      vendorTenderApi.subStatus(sid).then((s) => {
        if (s.payment_status === "paid") { toast.success("Subscription active — you can now prepare tenders."); loadSub(); }
        window.history.replaceState({}, "", "/vendor/tender-builder");
      }).catch(() => {});
    }
    if (params.get("sub_cancel")) { toast("Subscription payment cancelled"); window.history.replaceState({}, "", "/vendor/tender-builder"); }
  }, [loadSub, loadMine]);

  if (!isE) return null;

  const subscribe = async () => {
    try { const r = await vendorTenderApi.subCheckout(window.location.origin); window.location.href = r.checkout_url; }
    catch (e) { showApiError(e); }
  };

  const toPayload = () => ({
    ...form,
    budget_amount: form.budget_amount === "" ? null : Number(form.budget_amount),
    required_licenses: form.required_licenses ? form.required_licenses.split(",").map((s) => s.trim()).filter(Boolean) : [],
  });

  const save = async (submitAfter) => {
    setBusy(true);
    try {
      let ref = editingRef;
      if (ref) { await vendorTenderApi.update(ref, toPayload()); }
      else { const r = await vendorTenderApi.create(toPayload()); ref = r.notice_ref; setEditingRef(ref); }
      if (submitAfter) { await vendorTenderApi.submit(ref); toast.success("Submitted for PMC review"); }
      else { toast.success("Draft saved"); }
      setForm(EMPTY); setEditingRef(null); loadMine();
    } catch (e) { showApiError(e); } finally { setBusy(false); }
  };

  const edit = (t) => {
    setEditingRef(t.notice_ref);
    setForm({ ...EMPTY, ...t, budget_amount: t.budget_amount ?? "", required_licenses: (t.required_licenses || []).join(", ") });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const gated = sub && sub.required && !sub.active;

  return (
    <div data-testid="vendor-tender-builder" data-pmc-e-page="vendor-tender-builder">
      <VendorPortalChrome active="/vendor/tender-builder">
        <div style={{ maxWidth: "980px", margin: "0 auto", padding: "8px 4px 40px" }}>
          <h1 className="pmc-display" style={{ fontSize: "28px", margin: "0 0 4px" }}>Prepare a tender</h1>
          <p className="pmc-muted" style={{ fontSize: "14px", marginBottom: "18px" }}>Draft a tender using PMC's builder. Every tender you submit is reviewed by a PMC officer before it goes live. You cannot bid on a tender you prepared.</p>

          {gated ? (
            <div className="pmc-panel" style={{ padding: "24px", textAlign: "center" }} data-testid="sub-gate">
              <div className="pmc-eyebrow" style={{ marginBottom: "6px" }}>Subscription required</div>
              <div style={{ fontSize: "20px", fontWeight: 700, marginBottom: "4px" }}>
                {sub.price.currency?.toUpperCase()} {sub.price.amount} <span className="pmc-muted" style={{ fontSize: "13px" }}>/ {sub.price.period_days} days</span>
              </div>
              <p className="pmc-muted" style={{ fontSize: "13px", marginBottom: "16px" }}>Subscribe to unlock the tender builder.</p>
              <button className="pmc-btn pmc-btn--primary" data-testid="subscribe-btn" onClick={subscribe}>Subscribe & pay</button>
            </div>
          ) : (
            <>
              {sub && sub.active && <div className="pmc-muted" style={{ fontSize: "12px", marginBottom: "12px" }} data-testid="sub-active">Subscription active{sub.expires_at ? ` — renews ${String(sub.expires_at).slice(0, 10)}` : ""}.</div>}
              <section className="pmc-panel" style={{ padding: "18px", marginBottom: "22px" }}>
                <h2 className="pmc-panel__title" style={{ marginBottom: "12px" }}>{editingRef ? `Editing ${editingRef}` : "New tender"}</h2>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                  <L label="Title"><input style={inp} data-testid="vt-title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></L>
                  <L label="Category"><input style={inp} data-testid="vt-category" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} /></L>
                  <L label="Document type"><select style={inp} data-testid="vt-doctype" value={form.document_type} onChange={(e) => setForm({ ...form, document_type: e.target.value })}><option value="tender">Tender</option><option value="rfp">RFP</option><option value="rfq">RFQ</option></select></L>
                  <L label="Delivery country"><input style={inp} data-testid="vt-country" value={form.delivery_country} onChange={(e) => setForm({ ...form, delivery_country: e.target.value })} /></L>
                  <L label="Submission deadline"><input type="datetime-local" style={inp} data-testid="vt-deadline" value={form.submission_deadline} onChange={(e) => setForm({ ...form, submission_deadline: e.target.value })} /></L>
                  <L label="Pre-bid meeting (optional)"><input type="datetime-local" style={inp} data-testid="vt-prebid" value={form.pre_bid_meeting_date} onChange={(e) => setForm({ ...form, pre_bid_meeting_date: e.target.value })} /></L>
                  <L label="Budget currency"><input style={inp} data-testid="vt-currency" value={form.budget_currency} onChange={(e) => setForm({ ...form, budget_currency: e.target.value })} /></L>
                  <L label="Indicative budget"><input type="number" style={inp} data-testid="vt-budget" value={form.budget_amount} onChange={(e) => setForm({ ...form, budget_amount: e.target.value })} /></L>
                  <L label="Required licences (comma-separated)"><input style={inp} data-testid="vt-licenses" value={form.required_licenses} onChange={(e) => setForm({ ...form, required_licenses: e.target.value })} /></L>
                  <L label="Contact name"><input style={inp} data-testid="vt-contact-name" value={form.contact_name} onChange={(e) => setForm({ ...form, contact_name: e.target.value })} /></L>
                </div>
                <L label="Contact email"><input style={inp} data-testid="vt-contact-email" value={form.contact_email} onChange={(e) => setForm({ ...form, contact_email: e.target.value })} /></L>
                <L label="Scope / description"><textarea style={{ ...inp, height: "120px" }} data-testid="vt-description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></L>
                <div style={{ display: "flex", gap: "8px", marginTop: "12px" }}>
                  <button className="pmc-btn pmc-btn--secondary" data-testid="vt-save-draft" disabled={busy} onClick={() => save(false)}>Save draft</button>
                  <button className="pmc-btn pmc-btn--primary" data-testid="vt-submit" disabled={busy} onClick={() => save(true)}>Submit for review</button>
                  {editingRef && <button className="pmc-btn pmc-btn--ghost" onClick={() => { setForm(EMPTY); setEditingRef(null); }}>Cancel</button>}
                </div>
              </section>

              <h2 className="pmc-panel__title" style={{ marginBottom: "10px" }}>My prepared tenders</h2>
              {tenders.length === 0 ? <div className="pmc-muted" data-testid="vt-empty">You haven't prepared any tenders yet.</div> : (
                <div style={{ display: "grid", gap: "10px" }} data-testid="vt-list">
                  {tenders.map((t) => (
                    <div key={t.id} className="pmc-panel" style={{ padding: "12px 14px", display: "flex", justifyContent: "space-between", alignItems: "center" }} data-testid={`vt-row-${t.notice_ref}`}>
                      <div>
                        <div style={{ fontWeight: 600 }}>{t.title}</div>
                        <div className="pmc-muted" style={{ fontSize: "12px" }}>{t.notice_ref} · {STATUS_LABEL[t.review_status] || t.review_status}{t.review_note ? ` · note: ${t.review_note}` : ""}</div>
                      </div>
                      {["draft", "changes_requested"].includes(t.review_status) && <span style={{ display: "flex", gap: "6px" }}>
                        <button className="pmc-btn pmc-btn--sm pmc-btn--secondary" data-testid={`vt-criteria-${t.notice_ref}`} onClick={() => setCritRef(t.notice_ref)}>Criteria{t.tender_criteria?.length ? ` (${t.tender_criteria.length})` : ""}</button>
                        <button className="pmc-btn pmc-btn--sm pmc-btn--secondary" data-testid={`vt-edit-${t.notice_ref}`} onClick={() => edit(t)}>Edit</button></span>}
                    </div>
                  ))}
                </div>
              )}
              {critRef && <CriteriaEditorModal mode="vendor" noticeRef={critRef} onClose={() => setCritRef(null)} onSaved={loadMine} />}
            </>
          )}
        </div>
      </VendorPortalChrome>
    </div>
  );
}

const L = ({ label, children }) => (
  <div style={{ marginBottom: "8px" }}>
    <label style={{ display: "block", fontSize: "12px", color: "var(--ink-muted)", marginBottom: "4px" }}>{label}</label>
    {children}
  </div>
);
