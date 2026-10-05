import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { vendorApi } from "@/lib/api";

/**
 * Target page for the confirmation link emailed to the vendor's CURRENT
 * email when they request a mobile / office-phone change. Confirms the
 * token with the backend and shows a success / failure state. Admin
 * approval is still required to activate the change.
 */
export default function VendorVerifyPhoneChange() {
  const { token } = useParams();
  const [state, setState] = useState({ loading: true });

  useEffect(() => {
    vendorApi.confirmPhoneChange(token)
      .then((res) => setState({ loading: false, ok: true, field: res.field,
                                new_value: res.new_value, already: res.already }))
      .catch((e) => setState({ loading: false, ok: false,
                               detail: e?.response?.data?.detail || "Verification failed." }));
  }, [token]);

  const fieldLabel = state.field === "mobile" ? "mobile number"
                   : state.field === "office_phone" ? "office telephone"
                   : "phone-number change";

  return (
    <div data-testid="vendor-verify-phone-change-page"
         style={{ minHeight: "100vh", display: "grid", placeItems: "center",
                  background: "var(--surface-sunken, #f6f0dc)", padding: 20 }}>
      <div className="pmc-panel"
           style={{ maxWidth: 520, width: "100%", padding: 32, textAlign: "center" }}>
        <div className="pmc-eyebrow">PMC Managers · Supplier portal</div>
        <h1 style={{ margin: "10px 0" }}>Confirming your {fieldLabel}</h1>

        {state.loading && (
          <p data-testid="vphone-loading" className="pmc-muted">Checking link…</p>
        )}

        {!state.loading && state.ok && (
          <>
            <p data-testid="vphone-success" style={{ color: "var(--success, #047857)" }}>
              <b>Confirmed.</b>{" "}
              {state.new_value && <>Your request to change your {fieldLabel} to <b>{state.new_value}</b> is now confirmed. </>}
              A PMC administrator will review and approve the change. You'll receive another
              email once it's active on your account.
            </p>
            <Link to="/vendor/account" className="pmc-btn pmc-btn--primary"
                  style={{ marginTop: 20 }}
                  data-testid="vphone-return-link">Back to account</Link>
          </>
        )}

        {!state.loading && !state.ok && (
          <>
            <p data-testid="vphone-error" style={{ color: "var(--danger, #b91c1c)" }}>
              <b>{state.detail}</b>
            </p>
            <p className="pmc-muted" style={{ fontSize: 13 }}>
              Try submitting a new change request from your account page.
            </p>
            <Link to="/vendor/account" className="pmc-btn pmc-btn--secondary"
                  style={{ marginTop: 20 }}
                  data-testid="vphone-return-link">Back to account</Link>
          </>
        )}
      </div>
    </div>
  );
}
