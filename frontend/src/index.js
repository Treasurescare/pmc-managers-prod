import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";
import { Toaster } from "sonner";

createRoot(document.getElementById("root")).render(
  <>
    <App />
    <Toaster position="top-right" richColors closeButton />
  </>
);

// Register service worker for PWA / offline / push
if ("serviceWorker" in navigator && process.env.NODE_ENV === "production") {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/service-worker.js").catch((err) => {
      if (process.env.NODE_ENV !== "production") console.warn("SW registration failed:", err);
    });
  });
}
