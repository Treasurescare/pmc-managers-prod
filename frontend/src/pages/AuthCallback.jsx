import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";
import { toast } from "sonner";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH

function homeForRole(role) {
  if (role === "admin") return "/admin";
  if (role === "buyer") return "/buyer";
  return "/vendor";
}

export default function AuthCallback() {
  const navigate = useNavigate();
  const done = useRef(false);

  useEffect(() => {
    if (done.current) return;
    done.current = true;
    const hash = window.location.hash || "";
    const m = hash.match(/session_id=([^&]+)/);
    const sessionId = m ? m[1] : null;
    if (!sessionId) { navigate("/login"); return; }

    // Check if this is a pending role selection stored in sessionStorage
    const pendingRole = sessionStorage.getItem("pmc_pending_role");
    api.post("/auth/google-callback", { session_id: sessionId, role: pendingRole || undefined })
      .then(({ data }) => {
        // Clear hash immediately
        window.history.replaceState({}, "", window.location.pathname);
        if (data.needs_role) {
          sessionStorage.setItem("pmc_google_pending", JSON.stringify({ session_id: sessionId, email: data.email, name: data.name }));
          navigate("/auth/choose-role");
          return;
        }
        sessionStorage.removeItem("pmc_pending_role");
        sessionStorage.removeItem("pmc_google_pending");
        toast.success(`Welcome, ${data.name}`);
        window.location.href = homeForRole(data.role);
      })
      .catch((err) => {
        toast.error(formatApiError(err));
        navigate("/login");
      });
  }, [navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="pmc-progress" />
      <div className="pmc-label">Completing sign-in…</div>
    </div>
  );
}
