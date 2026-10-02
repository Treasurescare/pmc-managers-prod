import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { useUiTheme } from "@/context/UiThemeContext";
import { vendorApi, showApiError } from "@/lib/api";
import VendorPortalChrome from "./VendorPortalChrome";

const FIELD_META = {
  address:      { label: "Registered address", type: "textarea", placeholder: "Street, city, country" },
  office_phone: { label: "Office telephone",   type: "text",     placeholder: "+7 ..." },
  mobile:       { label: "Mobile number",      type: "text",     placeholder: "+7 ..." },
  email:        { label: "Login email",        type: "email",    placeholder: "name@company.com" },
};

export default function VendorAccountE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  const [profile, setProfile] = useState(null);
  const [pending, setPending] = useState([]);
  const [recent, setRecent] = useState([]);
  const [editing, setEditing] = useState(null); // field name
  const [draft, setDraft] = useState("");
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [revoking, setRevoking] = useState(false);

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

  useEffect(() => { if (isE) load(); }, [isE, load]);

  const openEdit = (field) => {
    setEditing(field);
    // Start with an empty draft so the Submit button only enables once the
    // user has actually typed a NEW value (prevents a 400 round-trip when
    // nothing has changed).
    setDraft("");
    setReason("");
  };
  const closeEdit = () => { setEditing(null); setDraft(""); setReason(""); };

  const submit = async () => {
    if (!draft.trim()) {
      toast.error("Please enter a new value.");
      return;
    }
    setSaving(true);
    try {
      await vendorApi.requestProfileChange(editing, draft.trim(), reason.trim() || null);
      toast.success(
        editing === "email"
          ? "Request sent. Confirm the new address from the verification email we just sent, then wait for admin approval."
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
            {["address", "office_phone", "mobile", "email"].map((field) => {
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
            <label style={{ display: "block", marginTop: 14 }}>
              <span className="pmc-eyebrow">New value</span>
              {FIELD_META[editing].type === "textarea" ? (
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
            <label style={{ display: "block", marginTop: 12 }}>
              <span className="pmc-eyebrow">Reason (optional)</span>
              <input value={reason} onChange={(e) => setReason(e.target.value)}
                     placeholder="Why are you changing this?"
                     className="pmc-input"
                     style={{ width: "100%", marginTop: 4 }}
                     data-testid="vacc-reason-input" />
            </label>
            <div style={{ marginTop: 20, display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button type="button" onClick={closeEdit}
                      className="pmc-btn pmc-btn--secondary"
                      data-testid="vacc-cancel-btn">Cancel</button>
              <button type="button" onClick={submit}
                      disabled={saving || !draft.trim() || draft.trim() === (profile?.[editing] || "")}
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
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <b>Password</b>
                <div className="pmc-muted" style={{ fontSize: 13 }}>
                  Change your login password.
                </div>
              </div>
              <Link to="/vendor/change-password"
                    className="pmc-btn pmc-btn--secondary pmc-btn--sm"
                    data-testid="vacc-change-password-link">Change</Link>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <b>Other devices</b>
                <div className="pmc-muted" style={{ fontSize: 13 }}>
                  Sign out of every other browser and mobile session.
                </div>
              </div>
              <button type="button" onClick={revokeAll} disabled={revoking}
                      className="pmc-btn pmc-btn--secondary pmc-btn--sm"
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
