/**
 * EscrowAccountVerify — v52d. One-click email verification landing page.
 * Hits GET /api/v1/escrow-accounts/verify/{token}; on success routes to
 * /escrow/login with a success banner, on failure explains why.
 */
import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "@/lib/api";

export default function EscrowAccountVerify() {
  const { token } = useParams();
  const [state, setState] = useState("loading");
  const [detail, setDetail] = useState("");

  useEffect(() => {
    if (!token) return;
    api.get(`/api/v1/escrow-accounts/verify/${token}`)
      .then(() => setState("ok"))
      .catch((e) => {
        setDetail(e?.response?.data?.detail || "Link invalid or expired");
        setState("err");
      });
  }, [token]);

  return (
    <div className="max-w-xl mx-auto px-6 py-16 text-center"
         data-testid={`escrow-verify-${state}`}>
      {state === "loading" && (
        <p className="text-brand-navy/60">Verifying your email…</p>
      )}
      {state === "ok" && (
        <>
          <div className="inline-block text-5xl text-emerald-700 mb-4">✓</div>
          <h1 className="font-serif text-3xl text-brand-navy">Email verified</h1>
          <p className="mt-3 text-sm text-brand-navy/70">
            Your account is now active. Sign in to continue filling out
            the five registration sections — your progress is saved to
            your account every time you save a draft.
          </p>
          <Link to="/escrow/login?verified=1"
                data-testid="escrow-verify-signin"
                className="inline-block mt-6 px-6 py-3 text-[11px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
            Sign in
          </Link>
        </>
      )}
      {state === "err" && (
        <>
          <div className="inline-block text-5xl text-red-700 mb-4">✕</div>
          <h1 className="font-serif text-3xl text-brand-navy">Link not valid</h1>
          <p className="mt-3 text-sm text-brand-navy/70">{String(detail)}</p>
          <Link to="/escrow/register"
                className="inline-block mt-6 px-6 py-3 text-[11px] uppercase tracking-widest border border-brand-navy/40 text-brand-navy hover:bg-brand-navy hover:text-white">
            Start again
          </Link>
        </>
      )}
    </div>
  );
}
