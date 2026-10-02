import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { useUiTheme } from "@/context/UiThemeContext";
import { vendorApi, uploadsApi, showApiError, BACKEND_URL } from "@/lib/api";
import VendorPortalChrome from "./VendorPortalChrome";

/**
 * v50n — Vendor Company & KYC page (fully wired).
 *
 * Tabs across the top switch client-side between:
 *   Licences & certificates · Company documents · Team & roles ·
 *   Bank accounts · Reviews
 * and the "Add licence" / "Upload renewal" buttons open a real dialog that
 * posts to /api/v1/vendor/licenses. Status (Valid / Expiring / Expired /
 * Missing) is computed live by the backend on every read.
 */

const TABS = [
  ["licenses",  "Licences & certificates"],
  ["documents", "Company documents"],
  ["team",      "Team & roles"],
  ["bank",      "Bank accounts"],
  ["reviews",   "Reviews"],
];

function fmtDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("en-GB",
      { day: "2-digit", month: "short", year: "numeric" });
  } catch { return iso.slice(0, 10); }
}

function statusPill(status) {
  const map = {
    valid:    ["pmc-pill--success", "Valid"],
    expiring: ["pmc-pill--warning", "Expires soon"],
    expired:  ["pmc-pill--danger", "Expired"],
    missing:  ["pmc-pill--danger", "Missing"],
  };
  const [cls, label] = map[status] || ["", status || "—"];
  return <span className={`pmc-pill ${cls}`}>{label}</span>;
}

function LicenseDialog({ initial, catalogue, onClose, onSave, saving }) {
  const [form, setForm] = useState({
    licence_type: initial?.licence_type || "",
    country: initial?.country || "KZ",
    number: initial?.number || "",
    issued_at: initial?.issued_at || "",
    expires_at: initial?.expires_at || "",
    file: null,
  });
  const isEdit = !!initial?.id;
  const upd = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = () => {
    if (!form.licence_type.trim()) return toast.error("Pick the licence type.");
    if (!form.number.trim()) return toast.error("Enter the licence number.");
    if (form.issued_at && form.expires_at && form.issued_at > form.expires_at)
      return toast.error("Issue date cannot be after expiry date.");
    onSave(form);
  };

  return (
    <>
      <div className="pmc-drawer-scrim" style={{ display: "block" }} onClick={onClose} />
      <div role="dialog" aria-modal="true" data-testid="license-dialog"
           style={{ position: "fixed", top: "50%", left: "50%",
                    transform: "translate(-50%,-50%)", width: "min(560px,92vw)",
                    background: "var(--surface,#fff)", border: "1px solid var(--line,#0001)",
                    borderRadius: "var(--radius-md,6px)", padding: 24, zIndex: 60,
                    boxShadow: "0 20px 50px rgba(0,0,0,.25)" }}>
        <div className="pmc-eyebrow">{isEdit ? "Update licence" : "Add licence"}</div>
        <h2 style={{ margin: "6px 0 16px" }}>{isEdit ? form.licence_type : "New licence / certificate"}</h2>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <label style={{ gridColumn: "1 / -1" }}>
            <span className="pmc-eyebrow">Licence type</span>
            <select value={form.licence_type} onChange={(e) => upd("licence_type", e.target.value)}
                    className="pmc-input" style={{ width: "100%", marginTop: 4 }}
                    data-testid="license-type">
              <option value="">— pick a licence type —</option>
              {catalogue.map((lt) => <option key={lt} value={lt}>{lt}</option>)}
              <option value="__other__">Other (ISO, ISO 45001, etc.)</option>
            </select>
          </label>
          {form.licence_type === "__other__" && (
            <label style={{ gridColumn: "1 / -1" }}>
              <span className="pmc-eyebrow">Custom licence name</span>
              <input className="pmc-input" style={{ width: "100%", marginTop: 4 }}
                     placeholder="e.g. ISO 9001:2015"
                     onChange={(e) => upd("licence_type", e.target.value)}
                     data-testid="license-custom" />
            </label>
          )}
          <label>
            <span className="pmc-eyebrow">Country</span>
            <select value={form.country} onChange={(e) => upd("country", e.target.value)}
                    className="pmc-input" style={{ width: "100%", marginTop: 4 }}
                    data-testid="license-country">
              {["KZ","IN","AE","GB","US"].map((c) => <option key={c}>{c}</option>)}
            </select>
          </label>
          <label>
            <span className="pmc-eyebrow">Licence number</span>
            <input value={form.number} onChange={(e) => upd("number", e.target.value)}
                   className="pmc-input" style={{ width: "100%", marginTop: 4 }}
                   placeholder="e.g. KZ-EL-2025-04418"
                   data-testid="license-number" />
          </label>
          <label>
            <span className="pmc-eyebrow">Issued</span>
            <input type="date" value={form.issued_at || ""} onChange={(e) => upd("issued_at", e.target.value)}
                   className="pmc-input" style={{ width: "100%", marginTop: 4 }}
                   data-testid="license-issued" />
          </label>
          <label>
            <span className="pmc-eyebrow">Expires</span>
            <input type="date" value={form.expires_at || ""} onChange={(e) => upd("expires_at", e.target.value)}
                   className="pmc-input" style={{ width: "100%", marginTop: 4 }}
                   data-testid="license-expires" />
          </label>
          <label style={{ gridColumn: "1 / -1" }}>
            <span className="pmc-eyebrow">Upload certificate (optional)</span>
            <input type="file" accept=".pdf,.jpg,.jpeg,.png"
                   onChange={(e) => upd("file", e.target.files?.[0] || null)}
                   className="pmc-input" style={{ width: "100%", marginTop: 4 }}
                   data-testid="license-file" />
          </label>
        </div>

        <div style={{ marginTop: 20, display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button type="button" onClick={onClose} className="pmc-btn pmc-btn--secondary"
                  data-testid="license-cancel">Cancel</button>
          <button type="button" onClick={submit} disabled={saving}
                  className="pmc-btn pmc-btn--primary"
                  data-testid="license-submit">
            {saving ? "Saving…" : (isEdit ? "Save changes" : "Add licence")}
          </button>
        </div>
      </div>
    </>
  );
}

export default function VendorCompanyKycE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  const [me, setMe] = useState(null);
  const [licData, setLicData] = useState({ licenses: [], catalogue: [], missing: [], expiring_soon: 0, expired: 0 });
  const [activeTab, setActiveTab] = useState("licenses");
  const [dialog, setDialog] = useState(null); // null | { mode:"add"|"edit", license? }
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const [meRes, licRes] = await Promise.all([
        vendorApi.me(),
        vendorApi.listLicenses(),
      ]);
      setMe(meRes);
      setLicData(licRes);
    } catch (e) { showApiError(e); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { if (isE) load(); }, [isE, load]);

  const openAdd = (licence_type) => setDialog({ mode: "add", license: licence_type ? { licence_type } : null });
  const openEdit = (license) => setDialog({ mode: "edit", license });
  const closeDialog = () => setDialog(null);

  const saveLicense = async (form) => {
    setSaving(true);
    try {
      let file_key = null;
      if (form.file) {
        const pre = await uploadsApi.presign(
          form.file.name, form.file.type, "vendor-license", form.file.size);
        await uploadsApi.direct(pre.key, form.file);
        file_key = pre.key;
      }
      const payload = {
        licence_type: form.licence_type,
        country: form.country,
        number: form.number,
        issued_at: form.issued_at || null,
        expires_at: form.expires_at || null,
        file_key,
      };
      if (dialog?.mode === "edit") await vendorApi.updateLicense(dialog.license.id, payload);
      else await vendorApi.addLicense(payload);
      toast.success(dialog?.mode === "edit" ? "Licence updated" : "Licence added");
      closeDialog();
      load();
    } catch (e) { showApiError(e, { fallbackTitle: "Could not save licence" }); }
    finally { setSaving(false); }
  };

  const removeLicense = async (lic) => {
    if (!window.confirm(`Remove ${lic.licence_type} (${lic.country})?`)) return;
    try {
      await vendorApi.deleteLicense(lic.id);
      toast.success("Licence removed");
      load();
    } catch (e) { showApiError(e); }
  };

  if (!isE && Legacy) return <Legacy />;
  if (!isE) return null;

  const { licenses, catalogue, missing, expiring_soon, expired } = licData;
  const headerNeedsAttention = expiring_soon > 0 || expired > 0 || missing.length > 0;

  return (
    <div data-testid="vendor-company-kyc-e" data-pmc-e-page="vendor-company-kyc-e">
      <VendorPortalChrome active="/vendor/company">
        <div style={{ display: "flex", justifyContent: "space-between",
                      alignItems: "flex-end", marginBottom: 20, flexWrap: "wrap", gap: 12 }}>
          <div>
            <div className="pmc-eyebrow">Company &amp; KYC</div>
            <h1 className="pmc-display" style={{ fontSize: 40, lineHeight: "44px", margin: "6px 0 0" }}
                data-testid="vkyc-company-name">
              {me?.company_name || "Your company"}
            </h1>
          </div>
          <Link to="/vendor/account" className="pmc-btn pmc-btn--secondary"
                data-testid="vkyc-edit-profile">
            <svg className="pmc-ico" aria-hidden="true"><use href="#i-settings" /></svg> Edit profile
          </Link>
        </div>

        <div className="ck-head pmc-panel" data-testid="vkyc-head">
          <div>
            <span className="l">KYC status</span>
            <span className="pmc-pill pmc-pill--success">
              {me?.kyc_status || "Verified"}
            </span>
            <span className="s">{me?.vendor_ref ? `Ref ${me.vendor_ref}` : ""}</span>
          </div>
          <div>
            <span className="l">Supplier ID</span>
            <b className="pmc-ref" style={{ color: "var(--ink)", fontSize: 14 }}
               data-testid="vkyc-ref">{me?.vendor_ref || "—"}</b>
            <span className="s">{me?.country ? `Registered ${me.country}` : ""}</span>
          </div>
          <div>
            <span className="l">Categories</span>
            <b style={{ fontSize: 14 }}>
              {(me?.business_categories || []).length || "—"}
            </b>
            <span className="s">
              {(me?.business_categories || []).slice(0, 2).join(" · ")}
            </span>
          </div>
          <div>
            <span className="l">Rating</span>
            <b style={{ fontSize: 18 }}>{me?.rating_label || "—"}</b>
            <span className="s">{me?.rating_note || ""}</span>
          </div>
        </div>

        {headerNeedsAttention && (
          <div className="pmc-callout pmc-callout--warn" style={{ margin: "16px 0" }}
               data-testid="vkyc-alert">
            <svg className="pmc-ico" aria-hidden="true"><use href="#i-clock" /></svg>
            <div>
              <b>
                {[
                  expiring_soon ? `${expiring_soon} expiring soon` : null,
                  expired ? `${expired} expired` : null,
                  missing.length ? `${missing.length} KZ licence${missing.length === 1 ? "" : "s"} missing` : null,
                ].filter(Boolean).join(" · ")}
              </b>
              {" "}Tenders that need them will show “KYC gap” until you update.{" "}
              <button type="button" onClick={() => setActiveTab("licenses")}
                      style={{ background: "transparent", border: 0, color: "inherit",
                               textDecoration: "underline", cursor: "pointer" }}
                      data-testid="vkyc-fix-now">Fix now</button>
            </div>
          </div>
        )}

        <div className="pmc-tabs" style={{ marginBottom: 16 }} role="tablist"
             data-testid="vkyc-tabs">
          {TABS.map(([k, label]) => (
            <button key={k} role="tab" aria-selected={activeTab === k}
                    className={"pmc-tab" + (activeTab === k ? " active" : "")}
                    onClick={() => setActiveTab(k)}
                    data-testid={`vkyc-tab-${k}`}>
              {label}
              {k === "licenses" && licenses.length > 0 && <span className="n">{licenses.length}</span>}
            </button>
          ))}
        </div>

        {activeTab === "licenses" && (
          <section className="pmc-panel" data-testid="vkyc-licenses-panel">
            {loading && <div className="p-6 text-sm" data-testid="vkyc-loading">Loading licences…</div>}
            {!loading && (
              <>
                <table className="pmc-table">
                  <thead>
                    <tr><th>Licence</th><th>Country</th><th>Number</th><th>Expires</th><th>Status</th><th></th></tr>
                  </thead>
                  <tbody>
                    {licenses.map((lic) => (
                      <tr key={lic.id} data-testid={`vkyc-row-${lic.id}`}>
                        <td style={{ fontWeight: 600 }}>{lic.licence_type}</td>
                        <td>{lic.country}</td>
                        <td className="pmc-ref">{lic.number}</td>
                        <td>{fmtDate(lic.expires_at)}</td>
                        <td>{statusPill(lic.status)}</td>
                        <td style={{ textAlign: "right" }}>
                          <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                            {lic.file_key && (
                              <a href={`${BACKEND_URL}/api/v1/uploads/files/${lic.file_key}`}
                                 target="_blank" rel="noopener noreferrer"
                                 className="pmc-btn pmc-btn--ghost pmc-btn--sm"
                                 data-testid={`vkyc-view-${lic.id}`}>View</a>
                            )}
                            <button type="button" onClick={() => openEdit(lic)}
                                    className="pmc-btn pmc-btn--secondary pmc-btn--sm"
                                    data-testid={`vkyc-edit-${lic.id}`}>
                              {lic.status === "expiring" || lic.status === "expired" ? "Upload renewal" : "Edit"}
                            </button>
                            <button type="button" onClick={() => removeLicense(lic)}
                                    className="pmc-btn pmc-btn--ghost pmc-btn--sm"
                                    data-testid={`vkyc-delete-${lic.id}`}>Remove</button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {missing.map((licence_type) => (
                      <tr key={licence_type} data-testid={`vkyc-missing-${licence_type}`}
                          style={{ background: "var(--warning-soft,#fef9e7)" }}>
                        <td style={{ fontWeight: 600 }}>{licence_type}</td>
                        <td>KZ</td>
                        <td className="pmc-ref" style={{ color: "var(--danger,#b91c1c)" }}>Not on file</td>
                        <td>—</td>
                        <td>{statusPill("missing")}</td>
                        <td style={{ textAlign: "right" }}>
                          <button type="button"
                                  onClick={() => openAdd(licence_type)}
                                  className="pmc-btn pmc-btn--secondary pmc-btn--sm"
                                  data-testid={`vkyc-add-${licence_type.replace(/\s+/g, "-")}`}>
                            Add licence
                          </button>
                        </td>
                      </tr>
                    ))}
                    {licenses.length === 0 && missing.length === 0 && (
                      <tr>
                        <td colSpan={6} style={{ textAlign: "center", padding: 32 }}
                            data-testid="vkyc-empty">
                          No licences on file yet.{" "}
                          <button type="button" onClick={() => openAdd(null)}
                                  style={{ background: "transparent", border: 0,
                                           color: "var(--brand-navy,#0B1A14)",
                                           textDecoration: "underline", cursor: "pointer" }}>
                            Add your first licence
                          </button>
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
                <div style={{ padding: 14, borderTop: "1px solid var(--line,#0001)",
                              display: "flex", justifyContent: "flex-end" }}>
                  <button type="button" onClick={() => openAdd(null)}
                          className="pmc-btn pmc-btn--primary pmc-btn--sm"
                          data-testid="vkyc-add-license">
                    <svg className="pmc-ico" aria-hidden="true"><use href="#i-plus" /></svg> Add licence
                  </button>
                </div>
              </>
            )}
          </section>
        )}

        {activeTab === "documents" && (
          <section className="pmc-panel" data-testid="vkyc-documents-panel">
            <div className="p-6 text-sm pmc-muted" data-testid="vkyc-documents-empty">
              Company documents (Certificate of incorporation, Trade licence, Tax registration, Bank letter, etc.)
              are uploaded during registration and are visible here once the KYC team confirms them.
            </div>
          </section>
        )}

        {activeTab === "team" && (
          <section className="pmc-panel" data-testid="vkyc-team-panel">
            <div className="p-6 text-sm pmc-muted" data-testid="vkyc-team-empty">
              Team &amp; roles for this vendor are managed under <Link to="/vendor/account">Account &amp; security</Link>.
            </div>
          </section>
        )}

        {activeTab === "bank" && (
          <section className="pmc-panel" data-testid="vkyc-bank-panel">
            <div className="p-6 text-sm pmc-muted" data-testid="vkyc-bank-empty">
              Bank account details are shared with the escrow officer on award.
              To change them, raise a <Link to="/vendor">profile change request</Link>.
            </div>
          </section>
        )}

        {activeTab === "reviews" && (
          <section className="pmc-panel" data-testid="vkyc-reviews-panel">
            <div className="p-6 text-sm pmc-muted" data-testid="vkyc-reviews-empty">
              Buyer reviews are listed under <Link to="/vendor/reviews">Reviews</Link>.
            </div>
          </section>
        )}
      </VendorPortalChrome>

      {dialog && (
        <LicenseDialog initial={dialog.license}
                       catalogue={catalogue}
                       onClose={closeDialog}
                       onSave={saveLicense}
                       saving={saving} />
      )}
    </div>
  );
}
