import { useEffect, useState } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { adminApi } from "@/lib/api";

/**
 * Admin-console route guard.
 *
 * The /admin and /admin/e/* pages are the full procurement back-office. Only
 * `admin` and `reviewer` roles may use them. Every other staff role
 * (escrow_agent, certifier, legal_counsel, accounting, committee_member,
 * auditor, support, …) belongs on the specialist /staff dashboard — so a
 * signed-in escrow signer who navigates to /admin is bounced to /staff
 * instead of seeing the full admin UI.
 *
 * On 401 (no valid session) we send them to the unified login.
 */
const ADMIN_CONSOLE_ROLES = ["admin", "reviewer"];

export default function RequireAdmin() {
  const [state, setState] = useState("checking"); // checking | allowed | wrong-role | guest
  const location = useLocation();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const me = await adminApi.me();
        if (cancelled) return;
        const role = me?.active_role || me?.role;
        setState(ADMIN_CONSOLE_ROLES.includes(role) ? "allowed" : "wrong-role");
      } catch {
        if (!cancelled) setState("guest");
      }
    })();
    return () => { cancelled = true; };
  }, [location.pathname]);

  if (state === "checking") {
    return (
      <div data-testid="require-admin-loading"
        style={{ minHeight: "60vh", display: "grid", placeItems: "center", color: "#5B6B63", fontSize: "14px" }}>
        Checking access…
      </div>
    );
  }
  if (state === "guest") {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }
  if (state === "wrong-role") {
    return <Navigate to="/staff" replace />;
  }
  return <Outlet />;
}
