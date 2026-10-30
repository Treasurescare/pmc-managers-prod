import { useEffect, useState } from "react";
import { toast } from "sonner";
import { marketingApi } from "@/lib/api";

const API = process.env.REACT_APP_BACKEND_URL;

// Shows "Continue with LinkedIn" once the LinkedIn app keys are configured; surfaces ?li_error from the callback.
export default function LinkedInSignIn({ role }) {
  const [on, setOn] = useState(false);
  useEffect(() => {
    marketingApi.linkedinStatus().then((r) => setOn(!!r.signin_enabled)).catch(() => {});
    const err = new URLSearchParams(window.location.search).get("li_error");
    if (err) { toast.error(err); }
  }, []);
  if (!on || role === "escrow") return null;
  return (
    <a href={`${API}/api/v1/auth/linkedin/start?portal=${role}`} className="pmc-btn pmc-btn--secondary pmc-btn--lg"
       style={{ width: "100%", display: "inline-flex", justifyContent: "center", gap: "8px" }} data-testid="signin-linkedin">
      <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path fill="#0A66C2" d="M20.45 20.45h-3.56v-5.57c0-1.33-.03-3.04-1.85-3.04-1.86 0-2.14 1.45-2.14 2.94v5.67H9.35V9h3.41v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28zM5.34 7.43a2.06 2.06 0 1 1 0-4.13 2.06 2.06 0 0 1 0 4.13zM7.12 20.45H3.56V9h3.56v11.45zM22.22 0H1.77C.79 0 0 .77 0 1.73v20.54C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.73V1.73C24 .77 23.2 0 22.22 0z"/></svg>
      Continue with LinkedIn
    </a>
  );
}
