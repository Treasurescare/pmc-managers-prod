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
      .catch(() => { /* HTTPS-only in prod; silently no-op if it fails */ });
  });
}
