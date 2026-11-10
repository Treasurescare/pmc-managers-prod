import { useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { vendorApi } from "@/lib/api";

/**
 * v49l — Vendor route guard.
 *
 * The Option-E vendor pages are static HTML mockups with live-data hooks that
 * silently swallow API 401s. When a signed-out visitor lands on /vendor/*
 * they saw the mockup with placeholder data ("EC · Emerald Corporates") and
 * concluded the app was broken. This guard calls /vendor/auth/me once on
 * mount and bounces to /login on 401 — showing a small placeholder in the
 * meantime so the mockup never flashes.
 */
export default function RequireVendor({ children }) {
  const [state, setState] = useState("checking"); // "checking" | "authed" | "guest"
  const location = useLocation();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      // Only a real 401 means signed out; a brief server hiccup (502/504/network) is retried, not treated as logout.
      for (let attempt = 0; attempt < 6; attempt += 1) {
        try {
          await vendorApi.me();
          if (!cancelled) setState("authed");
          return;
        } catch (e) {
          if (e?.response?.status === 401) { if (!cancelled) setState("guest"); return; }
          await new Promise((r) => setTimeout(r, 2500 * (attempt + 1)));
          if (cancelled) return;
        }
      }
      if (!cancelled) setState("authed");
    })();
    return () => { cancelled = true; };
  }, [location.pathname]);

  if (state === "checking") {
    return (
      <div data-testid="require-vendor-loading"
        style={{ minHeight: "60vh", display: "grid", placeItems: "center", color: "#5B6B63", fontSize: "14px" }}>
        Signing you in…
      </div>
    );
  }
  if (state === "guest") {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }
  return children;
}
