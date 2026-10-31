import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { useUiTheme } from "@/context/UiThemeContext";
import { vendorApi, publicApi, mastersApi, showApiError } from "@/lib/api";
import { COUNTRY_PHONE, phoneSpecFor, validatePhoneForCountry } from "@/lib/phoneCountries";
import VendorPortalChrome from "./VendorPortalChrome";

const FIELD_META = {
  company_name: { label: "Company name",      type: "text",     placeholder: "Registered legal name" },
  address:      { label: "Registered address", type: "address",  placeholder: "" },
  office_phone: { label: "Office telephone",   type: "text",     placeholder: "+7 ..." },
  mobile:       { label: "Mobile number",      type: "text",     placeholder: "+7 ..." },
  email:        { label: "Login email",        type: "email",    placeholder: "name@company.com" },
};

// v53a — masters-driven structured address: country → state/county → city
// cascades from the geography masters; address1/address2 stay free text.
const EMPTY_ADDR = { address1: "", address2: "", city: "", state: "", state_code: "", country: "KZ", zip: "" };

export default function VendorAccountE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  const [profile, setProfile] = useState(null);
  const [pending, setPending] = useState([]);
  const [recent, setRecent] = useState([]);
  const [editing, setEditing] = useState(null); // field name
  const [draft, setDraft] = useState("");
  const [reason, setReason] = useState("");
  const [phoneCountry, setPhoneCountry] = useState("KZ");
  const [phoneLocal, setPhoneLocal] = useState("");
  const [phoneError, setPhoneError] = useState("");
  const [addrParts, setAddrParts] = useState(EMPTY_ADDR);
  const [addrError, setAddrError] = useState("");
  const [addrStates, setAddrStates] = useState([]);
  const [addrCities, setAddrCities] = useState([]);
  const [cityQ, setCityQ] = useState("");
  const [countries, setCountries] = useState([]);
  const [saving, setSaving] = useState(false);
  const [revoking, setRevoking] = useState(false);
  // v51t — evidence upload (incorporation cert for company_name, etc.)
  const [evidence, setEvidence] = useState(null); // { key, filename, size_bytes }
  const [uploadingEvidence, setUploadingEvidence] = useState(false);

  const load = useCallback(async () => {
    try {
      const [p, r] = await Promise.all([
        vendorApi.getProfile(),
        vendorApi.listProfileRequests(),
      ]);
      setProfile(p);
      setPending(r.pending || []);
      setRecent(r.recent || []);
    } catch (e) { showApiError(e); }
  }, []);

  useEffect(() => {
    if (!isE) return;
    load();
    // v53a — FULL country master (250) for the address cascade, instead of
    // publicApi.countries() which only returns the ~30 licence-mapped ones.
    mastersApi.listCountriesPublic().then((rows) => {
      const list = (Array.isArray(rows) ? rows : (rows?.items || []))
        .map((c) => ({ code: String(c.code || c.iso2 || "").toUpperCase(),
                        name: String(c.name || c.code || "").trim() }))
        .filter((c) => c.code);
      setCountries(list);
    }).catch(() => setCountries([]));
  }, [isE, load]);

  // v53a — cascade: country → states → cities, all from the masters.
  useEffect(() => {
    if (!addrParts.country) { setAddrStates([]); return; }
    mastersApi.listStates(addrParts.country).then(setAddrStates).catch(() => setAddrStates([]));
  }, [addrParts.country]);
  useEffect(() => {
    if (!addrParts.country || !addrParts.state_code) { setAddrCities([]); return; }
    mastersApi.listCities(addrParts.country, addrParts.state_code, cityQ, 200)
      .then(setAddrCities).catch(() => setAddrCities([]));
  }, [addrParts.country, addrParts.state_code, cityQ]);

  const openEdit = (field) => {
    setEditing(field);
    // Start with an empty draft so the Submit button only enables once the
    // user has actually typed a NEW value (prevents a 400 round-trip when
    // nothing has changed).
    setDraft("");
    setReason("");
    setEvidence(null);
    // v50n — phone fields get a country-code dropdown auto-prefilled with
    // the vendor's registered country and a digit-count rule per country.
    if (field === "mobile" || field === "office_phone") {
      const vendorCountry = (profile?.country || "KZ").toUpperCase();
      const spec = phoneSpecFor(vendorCountry);
      setPhoneCountry(spec.code);
      setPhoneLocal("");
      setPhoneError("");
    }
    // v50o — address is a structured set of fields, not a free-text blob.
    if (field === "address") {
      setAddrParts({ ...EMPTY_ADDR, country: (profile?.country || "KZ").toUpperCase() });
      setCityQ("");
      setAddrError("");
    }
  };
  const closeEdit = () => { setEditing(null); setDraft(""); setReason(""); setPhoneError(""); setAddrError(""); setEvidence(null); };

  const uploadEvidence = async (file) => {
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
      toast.error("Supporting document must be under 5 MB.");
      return;
    }
    setUploadingEvidence(true);
    try {
      const pres = await (await import("@/lib/api")).api.post("/api/v1/uploads/presign", {
        file_name: file.name,
        content_type: file.type || "application/octet-stream",
        scope: "vendor-docs",
        size_bytes: file.size,
      });
      const fd = new FormData();
      fd.append("key", pres.data.key);
      fd.append("file", file);
      const r = await (await import("@/lib/api")).api.post(pres.data.direct_url, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      // v54l — use the canonical presign key (always present). In the S3
      // phase the direct-upload response has no JSON `key`, so `r.data.key`
      // was undefined → evidence_key went out null → backend returned 400
      // "A supporting document is required" even though a file was attached.
      setEvidence({ key: pres.data.key, filename: file.name, size_bytes: (r?.data?.size_bytes ?? file.size) });
      toast.success(`Uploaded: ${file.name}`);
    } catch (e) {
      showApiError(e, { fallbackTitle: "Upload failed" });
    } finally {
      setUploadingEvidence(false);
    }
  };

  const submit = async () => {
    let valueToSend = draft.trim();
    let parts = null;
    if (editing === "mobile" || editing === "office_phone") {
      // v50n — country-aware phone validation. Local digits are checked
      // against the selected country's digit rule before the request is sent.
      const err = validatePhoneForCountry(phoneCountry, phoneLocal);
      if (err) {
        setPhoneError(err);
        return;
      }
      const spec = phoneSpecFor(phoneCountry);
      valueToSend = `+${spec.dial}${phoneLocal.replace(/\D/g, "")}`;
    }
    if (editing === "address") {
      // v53a — structured address from masters: country → state/county →
      // city cascade. address1, city, country, zip mandatory; state required
      // only when the master has states for the chosen country; address2
      // optional.
      const missing = [];
      if (!addrParts.country) missing.push("Country");
      if (addrStates.length > 0 && !addrParts.state_code) missing.push("State / county");
      if (!addrParts.city.trim()) missing.push("City");
      if (!addrParts.address1.trim()) missing.push("Address line 1");
      if (!addrParts.zip.trim()) missing.push("ZIP / postal code");
      if (missing.length) {
        setAddrError(`Please fill in: ${missing.join(", ")}`);
        return;
      }
      if (!/^[A-Za-z0-9\-\s]{3,12}$/.test(addrParts.zip.trim())) {
        setAddrError("ZIP / postal code must be 3–12 letters or digits.");
        return;
      }
      const countryLabel = (countries.find((x) => x.code === addrParts.country) || {}).name || addrParts.country;
      const cityState = [addrParts.city.trim(), addrParts.state.trim()].filter(Boolean).join(", ");
      valueToSend = [addrParts.address1.trim(), addrParts.address2.trim(), cityState, `${addrParts.zip.trim()}`, countryLabel]
        .filter(Boolean).join(", ");
      parts = { ...addrParts, country_label: countryLabel };
    }
    if (!valueToSend) {
      toast.error("Please enter a new value.");
      return;
    }
    // v51t — company_name requires a supporting incorporation document.
    if (editing === "company_name" && !evidence?.key) {
      toast.error("Please upload a certificate of incorporation or change-of-name certificate.");
      return;
    }
    setSaving(true);
    try {
      await vendorApi.requestProfileChange(editing, valueToSend, reason.trim() || null, parts,
        evidence ? { evidence_key: evidence.key, evidence_filename: evidence.filename } : null);
      toast.success(
        editing === "email"
          ? "Request sent. Confirm the new address from the verification email we just sent, then wait for admin approval."
          : (editing === "mobile" || editing === "office_phone")
            ? "Request sent. Check your current inbox for the confirmation link, click it, then wait for admin approval."
            : "Request submitted. A PMC administrator will review and approve shortly.",
        { duration: 8000 },
      );
      closeEdit();
      load();
    } catch (e) { showApiError(e, { fallbackTitle: "Could not submit change" }); }
    finally { setSaving(false); }
  };

  const revokeAll = async () => {
    if (!window.confirm("Sign out of every other device? You'll stay signed in on this one.")) return;
    setRevoking(true);
    try {
      await vendorApi.revokeOtherSessions();
      toast.success("All other sessions have been signed out.");
    } catch (e) { showApiError(e); }
    finally { setRevoking(false); }
  };

  const pendingForField = (f) => pending.find((p) => p.field === f);

  if (!isE && Legacy) return <Legacy />;
  if (!isE) return null;

  return (
    <div data-testid="vendor-account-e" data-pmc-e-page="vendor-account-e">
      <VendorPortalChrome active="/vendor/account">
        <div className="sp-head">
          <div>
            <div className="pmc-eyebrow">Account &amp; security</div>
            <h1>Your account</h1>
          </div>
        </div>

        <section className="pmc-panel" data-testid="vacc-profile-panel">
          <div className="pmc-panel__head">
            <h2 className="pmc-panel__title">Company contact details</h2>
            <span className="pmc-pill">Changes need admin approval</span>
          </div>
          <div className="pmc-panel__body" style={{ display: "grid", gap: 14, fontSize: 14 }}>
            {profile?.partner_code && <div data-testid="vacc-partner-code">Your PMC partner: <b>{profile.partner_name}</b> ({profile.partner_code})</div>}
            {["company_name", "address", "office_phone", "mobile", "email"].map((field) => {
              const meta = FIELD_META[field];
              const current = profile?.[field];
              const req = pendingForField(field);
              return (
                <div key={field} data-testid={`vacc-row-${field}`}
                     style={{ display: "flex", justifyContent: "space-between",
                              alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
                  <div style={{ minWidth: 240 }}>
                    <b>{meta.label}</b>
                    <div className="pmc-muted" style={{ fontSize: 13, whiteSpace: "pre-wrap" }}
                         data-testid={`vacc-current-${field}`}>
                      {current || <em>Not set</em>}
                    </div>
                    {req && (
                      <div className="pmc-muted"
                           style={{ fontSize: 12, color: "var(--brass-text, #B08E4A)", marginTop: 6 }}
                           data-testid={`vacc-pending-${field}`}>
                        Pending approval: <b>{req.new_value}</b>
                        {field === "email" && (
                          <> · {req.email_verified ? "Email verified" : "Awaiting email verification"}</>
                        )}
                      </div>
                    )}
                  </div>
                  <button type="button" onClick={() => openEdit(field)}
                          disabled={!!req}
                          className="pmc-btn pmc-btn--secondary pmc-btn--sm"
                          data-testid={`vacc-edit-${field}`}>
                    {req ? "Pending…" : "Request change"}
                  </button>
                </div>
              );
            })}
          </div>
        </section>

        {editing && (
          <div className="pmc-drawer-scrim" onClick={closeEdit} style={{ display: "block" }} />
        )}
        {editing && (
          <div role="dialog" aria-modal="true"
               data-testid="vacc-edit-dialog"
               style={{
                 position: "fixed", top: "50%", left: "50%", transform: "translate(-50%,-50%)",
                 width: "min(520px, 92vw)", background: "var(--surface, #fff)",
                 border: "1px solid var(--line, #0001)", borderRadius: "var(--radius-md, 6px)",
                 padding: 24, zIndex: 60, boxShadow: "0 20px 50px rgba(0,0,0,.25)",
               }}>
            <div className="pmc-eyebrow">Request change</div>
            <h2 style={{ margin: "6px 0 16px" }}>{FIELD_META[editing].label}</h2>
            <div style={{ fontSize: 13 }} className="pmc-muted">
              Current: <b>{profile?.[editing] || "Not set"}</b>
            </div>
            {editing === "email" && (
              <div style={{ marginTop: 8, padding: 10,
                            background: "var(--warning-soft, #fef9e7)",
                            fontSize: 12, lineHeight: "18px" }}
                   data-testid="vacc-email-notice">
                <b>Email changes need extra verification.</b>{" "}
                We'll send a confirmation link to the new address. After you click it, an
                administrator still has to approve before your login email is updated.
              </div>
            )}
            {editing === "company_name" && (
              <div style={{ marginTop: 8, padding: 10,
                            background: "var(--warning-soft, #fef9e7)",
                            fontSize: 12, lineHeight: "18px" }}
                   data-testid="vacc-company-notice">
                <b>Company name changes need supporting evidence.</b>{" "}
                Please attach a scanned copy of your <b>certificate of incorporation</b> or
                a <b>change-of-name certificate</b> issued by the registrar. PMC Managers
                will verify this document before approving the change.
              </div>
            )}
            {(editing === "mobile" || editing === "office_phone") && (
              <div style={{ marginTop: 8, padding: 10,
                            background: "var(--warning-soft, #fef9e7)",
                            fontSize: 12, lineHeight: "18px" }}
                   data-testid="vacc-phone-notice">
                <b>Phone-number changes need confirmation.</b>{" "}
                We'll send a confirmation link to your <b>current email</b> ({profile?.email || "your inbox"}).
                Click it to prove this request is from you. An administrator will then review
                and approve. (Attach a recent phone bill below if you have one — it speeds up approval.)
              </div>
            )}
            <label style={{ display: "block", marginTop: 14 }}>
              <span className="pmc-eyebrow">
                {editing === "email" ? "New email" : "New value"}
              </span>
              {editing === "address" ? (
                <div style={{ display: "grid", gap: 10, marginTop: 4 }}
                     data-testid="vacc-address-form">
                  {/* v53a — masters cascade: Country → State/County → City,
                      then free-text Address line 1 / 2 and ZIP. */}
                  <select value={addrParts.country}
                          onChange={(e) => setAddrParts({ ...addrParts, country: e.target.value, state: "", state_code: "", city: "" })}
                          className="pmc-input" style={{ width: "100%" }}
                          data-testid="vacc-addr-country">
                    {countries.length === 0 && (
                      <option value={addrParts.country}>{addrParts.country}</option>
                    )}
                    {countries.map((c) => (
                      <option key={c.code} value={c.code}>{c.name} ({c.code})</option>
                    ))}
                  </select>
                  {addrStates.length > 0 ? (
                    <select value={addrParts.state_code}
                            onChange={(e) => {
                              const st = addrStates.find((s) => s.state_code === e.target.value);
                              setAddrParts({ ...addrParts, state_code: e.target.value, state: st?.name || "", city: "" });
                              setCityQ("");
                            }}
                            className="pmc-input" style={{ width: "100%" }}
                            data-testid="vacc-addr-state">
                      <option value="">State / county…</option>
                      {addrStates.map((s) => (
                        <option key={s.state_code} value={s.state_code}>{s.name}</option>
                      ))}
                    </select>
                  ) : (
                    <input value={addrParts.state}
                           onChange={(e) => setAddrParts({ ...addrParts, state: e.target.value, state_code: "" })}
                           placeholder="State / county"
                           className="pmc-input" style={{ width: "100%" }}
                           data-testid="vacc-addr-state" />
                  )}
                  <input value={addrParts.city}
                         onChange={(e) => { setAddrParts({ ...addrParts, city: e.target.value }); setCityQ(e.target.value); }}
                         placeholder="City — type to search the masters list"
                         list="vacc-city-list"
                         className="pmc-input" style={{ width: "100%" }}
                         data-testid="vacc-addr-city" />
                  <datalist id="vacc-city-list">
                    {addrCities.map((c, i) => <option key={`${c.name}-${i}`} value={c.name} />)}
                  </datalist>
                  <input value={addrParts.address1}
                         onChange={(e) => setAddrParts({ ...addrParts, address1: e.target.value })}
                         placeholder="Address line 1 (building, street)"
                         className="pmc-input" style={{ width: "100%" }}
                         data-testid="vacc-addr-line1" />
                  <input value={addrParts.address2}
                         onChange={(e) => setAddrParts({ ...addrParts, address2: e.target.value })}
                         placeholder="Address line 2 (area, district — optional)"
                         className="pmc-input" style={{ width: "100%" }}
                         data-testid="vacc-addr-line2" />
                  <input value={addrParts.zip}
                         onChange={(e) => setAddrParts({ ...addrParts, zip: e.target.value })}
                         placeholder="ZIP / postal code"
                         className="pmc-input" style={{ width: "100%" }}
                         data-testid="vacc-addr-zip" />
                  {addrError && (
                    <div style={{ fontSize: 12, color: "var(--danger,#b91c1c)" }}
                         data-testid="vacc-addr-error">{addrError}</div>
                  )}
                </div>
              ) : editing === "mobile" || editing === "office_phone" ? (
                <div style={{ display: "flex", gap: 6, marginTop: 4 }}>
                  <select value={phoneCountry}
                          onChange={(e) => { setPhoneCountry(e.target.value); setPhoneError(""); setPhoneLocal(""); }}
                          className="pmc-input"
                          style={{ width: 200, flexShrink: 0 }}
                          data-testid="vacc-phone-country">
                    {COUNTRY_PHONE.map((c) => (
                      <option key={c.code} value={c.code}>
                        +{c.dial} {c.name}
                      </option>
                    ))}
                  </select>
                  <div style={{ position: "relative", flex: 1 }}>
                    <span style={{ position: "absolute", left: 10, top: "50%",
                                   transform: "translateY(-50%)",
                                   color: "var(--ink-muted)", fontWeight: 600,
                                   pointerEvents: "none" }}
                          data-testid="vacc-phone-prefix">
                      +{phoneSpecFor(phoneCountry).dial}
                    </span>
                    <input
                      type="tel"
                      inputMode="numeric"
                      value={phoneLocal}
                      onChange={(e) => {
                        const v = e.target.value.replace(/\D/g, "");
                        setPhoneLocal(v);
                        // v53d — validatePhoneForCountry returns NULL on success;
                        // store "" so the submit-button check (phoneError !== "")
                        // doesn't read null as an error and stay disabled forever.
                        setPhoneError(v ? (validatePhoneForCountry(phoneCountry, v) || "") : "");
                      }}
                      placeholder={`${phoneSpecFor(phoneCountry).digits} digits`}
                      maxLength={phoneSpecFor(phoneCountry).digits}
                      className="pmc-input"
                      style={{ width: "100%", paddingLeft: 42 }}
                      data-testid="vacc-phone-local" />
                  </div>
                </div>
              ) : FIELD_META[editing].type === "textarea" ? (
                <textarea value={draft} onChange={(e) => setDraft(e.target.value)}
                          placeholder={FIELD_META[editing].placeholder}
                          rows={3}
                          className="pmc-input"
                          style={{ width: "100%", marginTop: 4 }}
                          data-testid="vacc-draft-input" />
              ) : (
                <input type={FIELD_META[editing].type}
                       value={draft} onChange={(e) => setDraft(e.target.value)}
                       placeholder={FIELD_META[editing].placeholder}
                       className="pmc-input"
                       style={{ width: "100%", marginTop: 4 }}
                       data-testid="vacc-draft-input" />
              )}
            </label>
            {(editing === "mobile" || editing === "office_phone") && (
              <div style={{ marginTop: 6, fontSize: 12,
                            color: phoneError ? "var(--danger,#b91c1c)" : "var(--ink-muted,#5a5a57)" }}
                   data-testid="vacc-phone-hint">
                {phoneError
                  ? phoneError
                  : `${phoneSpecFor(phoneCountry).name} numbers are exactly ${phoneSpecFor(phoneCountry).digits} digits.`}
              </div>
            )}
            <label style={{ display: "block", marginTop: 12 }}>
              <span className="pmc-eyebrow">Reason for the change (optional)</span>
              <input value={reason} onChange={(e) => setReason(e.target.value)}
                     placeholder="Why are you changing this?"
                     className="pmc-input"
                     style={{ width: "100%", marginTop: 4 }}
                     data-testid="vacc-reason-input" />
            </label>
            {(editing === "company_name" || editing === "mobile" || editing === "office_phone" || editing === "address") && (
              <div style={{ marginTop: 12 }} data-testid="vacc-evidence-block">
                <span className="pmc-eyebrow">
                  Supporting document {editing === "company_name" ? "(required)" : "(optional)"}
                </span>
                {evidence ? (
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
                                gap: 8, marginTop: 6, padding: "10px 12px",
                                background: "var(--surface-sunken,#f6f2e9)",
                                border: "1px solid var(--line,#e2dccd)",
                                borderRadius: 6, fontSize: 13 }}
                       data-testid="vacc-evidence-current">
                    <span style={{ overflow: "hidden", textOverflow: "ellipsis",
                                   whiteSpace: "nowrap", minWidth: 0 }}>
                      📎 {evidence.filename}
                      {evidence.size_bytes != null && (
                        <span className="pmc-muted" style={{ marginLeft: 6, fontSize: 12 }}>
                          ({Math.round(evidence.size_bytes / 1024)} KB)
                        </span>
                      )}
                    </span>
                    <button type="button"
                            onClick={() => setEvidence(null)}
                            className="pmc-btn pmc-btn--ghost pmc-btn--sm"
                            data-testid="vacc-evidence-remove"
                            style={{ color: "var(--danger,#b91c1c)" }}>Remove</button>
                  </div>
                ) : (
                  <label htmlFor="vacc-evidence-file" style={{
                    display: "block", marginTop: 6,
                    padding: "14px", border: "2px dashed var(--brass-text,#B08E4A)",
                    background: "var(--warning-soft,#fef9e7)",
                    borderRadius: 6, textAlign: "center", cursor: "pointer",
                    fontSize: 13,
                  }} data-testid="vacc-evidence-label">
                    {uploadingEvidence ? "Uploading…" : "Click to upload (PDF, PNG, JPG — up to 5 MB)"}
                    <input id="vacc-evidence-file" type="file" hidden
                           accept="application/pdf,image/*"
                           onChange={(e) => e.target.files?.[0] && uploadEvidence(e.target.files[0])}
                           data-testid="vacc-evidence-file" />
                  </label>
                )}
              </div>
            )}
            <div style={{ marginTop: 20, display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button type="button" onClick={closeEdit}
                      className="pmc-btn pmc-btn--secondary"
                      data-testid="vacc-cancel-btn">Cancel</button>
              <button type="button" onClick={submit}
                      disabled={
                        saving ||
                        phoneError !== "" ||
                        addrError !== "" ||
                        (editing === "company_name" && !evidence?.key) ||
                        (editing === "address"
                          ? !(addrParts.address1.trim() && addrParts.city.trim() && addrParts.country && addrParts.zip.trim() && (addrStates.length === 0 || addrParts.state_code))
                          : (editing === "mobile" || editing === "office_phone")
                            ? phoneLocal.replace(/\D/g, "").length !== phoneSpecFor(phoneCountry).digits
                            : (!draft.trim() || draft.trim() === (profile?.[editing] || "")))
                      }
                      className="pmc-btn pmc-btn--primary"
                      data-testid="vacc-submit-btn">
                {saving ? "Submitting…" : "Submit request"}
              </button>
            </div>
          </div>
        )}

        {recent.length > 0 && (
          <section className="pmc-panel" style={{ marginTop: 16 }}
                   data-testid="vacc-recent-panel">
            <div className="pmc-panel__head">
              <h2 className="pmc-panel__title">Recent change requests</h2>
            </div>
            <table className="pmc-table">
              <thead>
                <tr><th>Field</th><th>New value</th><th>Status</th><th>Decided</th><th>Note</th></tr>
              </thead>
              <tbody>
                {recent.map((r) => (
                  <tr key={r.id} data-testid={`vacc-recent-${r.id}`}>
                    <td style={{ fontWeight: 600 }}>{FIELD_META[r.field]?.label || r.field}</td>
                    <td>{r.new_value}</td>
                    <td>
                      <span className={"pmc-pill " + (r.status === "approved"
                        ? "pmc-pill--success" : "pmc-pill--danger")}>
                        {r.status}
                      </span>
                    </td>
                    <td className="pmc-muted" style={{ fontSize: 13 }}>
                      {r.decided_at ? r.decided_at.slice(0, 10) : "—"}
                    </td>
                    <td className="pmc-muted" style={{ fontSize: 13 }}>
                      {r.decision_notes || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}

        <section className="pmc-panel" style={{ marginTop: 16 }}
                 data-testid="vacc-security-panel">
          <div className="pmc-panel__head">
            <h2 className="pmc-panel__title">Sign-in &amp; security</h2>
          </div>
          <div className="pmc-panel__body" style={{ display: "grid", gap: 14, fontSize: 14 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
              <div style={{ flex: "1 1 180px", minWidth: 0 }}>
                <b>Password</b>
                <div className="pmc-muted" style={{ fontSize: 13 }}>
                  Change your login password.
                </div>
              </div>
              <Link to="/vendor/change-password"
                    className="pmc-btn pmc-btn--secondary pmc-btn--sm"
                    style={{ flex: "0 0 auto" }}
                    data-testid="vacc-change-password-link">Change</Link>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
              <div style={{ flex: "1 1 180px", minWidth: 0 }}>
                <b>Other devices</b>
                <div className="pmc-muted" style={{ fontSize: 13 }}>
                  Sign out of every other browser and mobile session.
                </div>
              </div>
              <button type="button" onClick={revokeAll} disabled={revoking}
                      className="pmc-btn pmc-btn--secondary pmc-btn--sm"
                      style={{ flex: "0 0 auto" }}
                      data-testid="vacc-revoke-sessions-btn">
                {revoking ? "Signing out…" : "Sign out everywhere else"}
              </button>
            </div>
          </div>
        </section>
      </VendorPortalChrome>
    </div>
  );
}
