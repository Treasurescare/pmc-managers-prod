import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { vendorApi } from "@/lib/api";

/**
 * Target page for the confirmation link emailed to a vendor's NEW address
 * when they request an email change. Confirms the token with the backend
 * and shows a success / failure state.
 */
export default function VendorVerifyEmailChange() {
  const { token } = useParams();
  const [state, setState] = useState({ loading: true });

  useEffect(() => {
    vendorApi.confirmEmailChange(token)
      .then((res) => setState({ loading: false, ok: true, new_email: res.new_email,
                                already: res.already }))
      .catch((e) => setState({ loading: false, ok: false,
                               detail: e?.response?.data?.detail || "Verification failed." }));
  }, [token]);

  return (
    <div data-testid="vendor-verify-email-change-page"
         style={{ minHeight: "100vh", display: "grid", placeItems: "center",
                  background: "var(--surface-sunken, #f6f0dc)", padding: 20 }}>
      <div className="pmc-panel"
           style={{ maxWidth: 520, width: "100%", padding: 32, textAlign: "center" }}>
        <div className="pmc-eyebrow">PMC Managers · Supplier portal</div>
        <h1 style={{ margin: "10px 0" }}>Confirming your new email</h1>

        {state.loading && (
          <p data-testid="vemail-loading" className="pmc-muted">Checking link…</p>
        )}

        {!state.loading && state.ok && (
          <>
            <p data-testid="vemail-success" style={{ color: "var(--success, #047857)" }}>
              <b>Confirmed.</b> {state.new_email && <>Your new email <b>{state.new_email}</b> has been verified. </>}
              A PMC administrator will now review the change and approve it. You'll receive another email once your login email has been updated.
            </p>
            <Link to="/vendor/account" className="pmc-btn pmc-btn--primary"
                  style={{ marginTop: 20 }}
                  data-testid="vemail-return-link">Back to account</Link>
          </>
        )}

        {!state.loading && !state.ok && (
          <>
            <p data-testid="vemail-error" style={{ color: "var(--danger, #b91c1c)" }}>
              <b>{state.detail}</b>
            </p>
            <p className="pmc-muted" style={{ fontSize: 13 }}>
              Try submitting a new email change request from your account page.
            </p>
            <Link to="/vendor/account" className="pmc-btn pmc-btn--secondary"
                  style={{ marginTop: 20 }}
                  data-testid="vemail-return-link">Back to account</Link>
          </>
        )}
      </div>
    </div>
  );
}
