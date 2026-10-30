import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate, useParams, Link } from "react-router-dom";
import { marketingApi, cacheCsrf } from "@/lib/api";

// Google returns here with #session_id=…; we swap it for a PMC session (existing accounts only).
export default function GoogleAuthCallback() {
  const { portal } = useParams();
  const location = useLocation();
  const nav = useNavigate();
  const done = useRef(false);
  const [err, setErr] = useState(null);
  useEffect(() => {
    if (done.current) return;
    done.current = true;
    const sid = new URLSearchParams((location.hash || "").replace(/^#/, "")).get("session_id");
    window.history.replaceState(null, "", location.pathname);
    if (!sid) { setErr("Google sign-in was cancelled."); return; }
    marketingApi.googleExchange({ session_id: sid, portal })
      .then((r) => {
        if (r.csrf_token) { cacheCsrf(r.csrf_token); }
        window.location.replace(r.next);
      })
      .catch((e) => setErr(e?.response?.data?.detail || "Google sign-in failed. Please try again."));
  }, [location, portal, nav]);
  return (
    <div style={{ minHeight: "60vh", display: "grid", placeItems: "center", padding: "24px" }} data-testid="google-callback">
      {err ? (
        <div style={{ maxWidth: "460px", textAlign: "center" }}>
          <p data-testid="google-callback-error" style={{ marginBottom: "16px" }}>{err}</p>
          <Link to="/login" className="pmc-btn pmc-btn--primary" data-testid="google-callback-back">Back to sign in</Link>
          <Link to="/register" className="pmc-btn" style={{ marginLeft: "8px" }}>Register</Link>
        </div>
      ) : <p>Signing you in…</p>}
    </div>
  );
}

export const startGoogleLogin = (portal) => {
  // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
  const redirectUrl = window.location.origin + `/auth/google/${portal}`;
  window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
};
