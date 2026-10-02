import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";
import "./pmc-responsive";
import { Toaster } from "sonner";

createRoot(document.getElementById("root")).render(
  <>
    <App />
          <Toaster
            richColors
            expand
            closeButton
            position="top-right"
            theme="light"
            duration={6000}
            visibleToasts={6}
            toastOptions={{
              classNames: {
                error: "border-l-4 border-l-red-600 min-w-[380px] max-w-[560px] shadow-lg",
                success: "border-l-4 border-l-emerald-600 min-w-[320px]",
                warning: "border-l-4 border-l-amber-500 min-w-[320px]",
                info: "border-l-4 border-l-brand-navy min-w-[320px]",
                title: "font-semibold",
                description: "text-[13px] leading-relaxed whitespace-pre-line",
                closeButton: "!bg-white !border !border-brand-navy/20",
              },
            }}
          />
  </>
);

// v46p — PWA service worker re-enabled with a safe strategy:
//   - shell (HTML/JS/CSS/fonts/crest) is stale-while-revalidate
//   - navigation requests are network-first with shell fallback
//   - /api/* is bypassed entirely (never cached) → no repeat of the v46d
//     regression where stale bundles masked login fixes
// This unlocks Android + iOS install-to-homescreen and keeps the app
// usable during transient network drops.
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/service-worker.js", { scope: "/" })
      .then((registration) => {
        if (!registration) return;
        // Fire an update check immediately after each cold load.
        try { registration.update(); } catch (_) {}

        // If a waiting worker is already present (new SW installed on a
        // previous visit but never activated), notify the UI right away.
        if (registration.waiting && navigator.serviceWorker.controller) {
          window.dispatchEvent(new CustomEvent("pmc:sw-update-available", { detail: { registration } }));
        }

        // Watch for an updatefound → new SW installed in the background.
        registration.addEventListener("updatefound", () => {
          const installing = registration.installing;
          if (!installing) return;
          installing.addEventListener("statechange", () => {
            if (installing.state === "installed" && navigator.serviceWorker.controller) {
              // Fresh SW installed and an old one is still in control → prompt the user.
              window.dispatchEvent(new CustomEvent("pmc:sw-update-available", { detail: { registration } }));
            }
          });
        });

        // Also run update() every 30 min for long-lived tabs so the user
        // doesn't need to close/reopen to pick up a fix.
        setInterval(() => { try { registration.update(); } catch (_) {} }, 30 * 60 * 1000);
      })
      .catch(() => { /* HTTPS-only in prod; silently no-op if it fails */ });
  });
}
