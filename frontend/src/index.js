import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";
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

// v46d — Service worker REMOVED. The offline-first SW precached the app shell
// and kept serving stale JS bundles across deploys (caused two production
// login incidents: cross-origin preview bundle + SameSite=Lax cookie bounce
// persisted after fixes shipped). A self-destructing /service-worker.js is
// deployed instead; existing browsers will clear caches and unregister on
// next visit.
