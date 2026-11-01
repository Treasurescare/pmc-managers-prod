import { useEffect, useState } from "react";

/**
 * SwUpdateBanner — v50j.
 *
 * Permanent fix for the "I deployed but can't see it" problem that caused
 * both the stale-shell confusion AND the Masters-sidebar-flicker-on-first-
 * login symptom.
 *
 * Listens for the global `pmc:sw-update-available` event (dispatched from
 * index.js when a new service worker finishes installing while another one
 * still controls the page). Shows a non-blocking "New version available"
 * banner. Clicking Refresh posts a SKIP_WAITING message to the waiting SW,
 * which triggers controllerchange → full page reload with the fresh bundle.
 */
export default function SwUpdateBanner() {
  const [reg, setReg] = useState(null);

  useEffect(() => {
    const onAvail = (e) => setReg(e.detail?.registration || null);
    window.addEventListener("pmc:sw-update-available", onAvail);
    return () => window.removeEventListener("pmc:sw-update-available", onAvail);
  }, []);

  // Reload exactly once when the new SW takes control.
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;
    let reloaded = false;
    const hadController = !!navigator.serviceWorker.controller;
    const handler = () => {
      if (reloaded || !hadController) return;
      reloaded = true;
      window.location.reload();
    };
    navigator.serviceWorker.addEventListener("controllerchange", handler);
    return () => navigator.serviceWorker.removeEventListener("controllerchange", handler);
  }, []);

  if (!reg) return null;

  const applyUpdate = () => {
    try {
      const target = reg.waiting || reg.installing;
      if (target) target.postMessage({ type: "SKIP_WAITING" });
      else window.location.reload();
    } catch (_) {
      window.location.reload();
    }
  };

  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="sw-update-banner"
      style={{
        position: "fixed", left: "50%", bottom: 20, transform: "translateX(-50%)",
        zIndex: 10000, maxWidth: 460, width: "92%",
        background: "#0B1A14", color: "#fff",
        border: "1px solid #B08E4A",
        padding: "12px 16px",
        display: "flex", alignItems: "center", gap: 12,
        boxShadow: "0 10px 30px rgba(0,0,0,0.25)",
        fontFamily: "inherit",
      }}>
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 600, fontSize: 13, letterSpacing: ".02em" }}>
          New version available
        </div>
        <div style={{ fontSize: 11, color: "#F6F0DC", opacity: 0.85, marginTop: 2 }}>
          Tap Refresh to load the latest menus, pages and fixes.
        </div>
      </div>
      <button
        type="button"
        onClick={applyUpdate}
        data-testid="sw-update-refresh"
        style={{
          background: "#B08E4A", color: "#0B1A14",
          border: "none", padding: "8px 14px",
          fontSize: 11, fontWeight: 700, letterSpacing: ".08em",
          textTransform: "uppercase", cursor: "pointer",
        }}>
        Refresh
      </button>
      <button
        type="button"
        onClick={() => setReg(null)}
        aria-label="Dismiss"
        data-testid="sw-update-dismiss"
        style={{
          background: "transparent", color: "#F6F0DC",
          border: "none", fontSize: 18, cursor: "pointer", lineHeight: 1,
        }}>×</button>
    </div>
  );
}
