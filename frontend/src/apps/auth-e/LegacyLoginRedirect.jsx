import { Navigate, useLocation } from "react-router-dom";

// Old per-portal sign-in URLs now open the unified /login page with the right role preselected.
export default function LegacyLoginRedirect({ role, keepIf, children }) {
  const loc = useLocation();
  const p = new URLSearchParams(loc.search);
  if (keepIf && keepIf.some((k) => p.get(k))) return children;
  const next = loc.state?.next || p.get("next") || p.get("redirect") || "";
  const q = new URLSearchParams({ role });
  if (next) q.set("next", next);
  return <Navigate to={`/login?${q.toString()}`} replace />;
}
