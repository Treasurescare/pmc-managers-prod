import { useEffect, useRef, useState } from "react";
import { useLocation, Link } from "react-router-dom";
import { marketingApi, cacheCsrf, showApiError } from "@/lib/api";

// Google returns here with ?code=…&state=…; we swap it for a PMC session (existing accounts only).
export default function GoogleAuthCallback() {
  const location = useLocation();
  const done = useRef(false);
  const [err, setErr] = useState(null);
  useEffect(() => {
    if (done.current) return;
    done.current = true;
    const q = new URLSearchParams(location.search);
    const code = q.get("code");
    const state = q.get("state");
    window.history.replaceState(null, "", location.pathname);
    if (!code || !state) { setErr("Google sign-in was cancelled."); return; }
    marketingApi.googleExchange({ code, state })
      .then((r) => {
        if (r.csrf_token) { cacheCsrf(r.csrf_token); }
        window.location.replace(r.next);
      })
      .catch((e) => {
        const d = e?.response?.data?.detail;
        setErr(typeof d === "string" && d ? d : "Google sign-in failed. Please try again.");
      });
  }, [location]);
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

export const startGoogleLogin = async (portal) => {
  // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
  const redirectUri = window.location.origin + "/auth/google/callback";
  try {
    const r = await marketingApi.googleStart({ portal, redirect_uri: redirectUri });
    window.location.href = r.url;
  } catch (e) { showApiError(e); }
};
