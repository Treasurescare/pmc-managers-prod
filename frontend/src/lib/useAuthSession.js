import { useEffect, useState } from "react";
import { api } from "./api";

/**
 * useAuthSession — probes all three auth realms (admin, staff, vendor) and
 * resolves to the first signed-in identity (if any). Public pages such as
 * `/notices/:ref` use this so they can swap the public "Sign in / Register"
 * header for a dashboard-style avatar + "Open dashboard" button when the
 * visitor is already authenticated.
 *
 * The probes carry `_skipAuthRedirect: true` so a 401 on the public page
 * never trips the global session-expiry redirect.
 *
 * Returns:
 *   { role: 'admin'|'staff'|'vendor'|null, me, dashboardPath, loading }
 */
const probe = (url) =>
  api.get(url, { _skipAuthRedirect: true }).then((r) => r.data);

export function useAuthSession() {
  const [state, setState] = useState({ role: null, me: null, dashboardPath: null, loading: true });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [a, s, v] = await Promise.allSettled([
        probe("/api/v1/admin/auth/me"),
        probe("/api/v1/staff/auth/me"),
        probe("/api/v1/vendor/auth/me"),
      ]);
      if (cancelled) return;
      if (a.status === "fulfilled" && a.value) {
        setState({ role: "admin", me: a.value, dashboardPath: "/admin", loading: false });
      } else if (s.status === "fulfilled" && s.value) {
        setState({ role: "staff", me: s.value, dashboardPath: "/staff", loading: false });
      } else if (v.status === "fulfilled" && v.value) {
        setState({ role: "vendor", me: v.value, dashboardPath: "/vendor", loading: false });
      } else {
        setState({ role: null, me: null, dashboardPath: null, loading: false });
      }
    })();
    return () => { cancelled = true; };
  }, []);

  return state;
}

export default useAuthSession;
