import { useEffect, useState } from "react";
import { pmcInstallSteps, detectPmcBrowser } from "@/lib/pmcInstallInstructions";

/**
 * PwaInstallPrompt — floating "Install App" affordance.
 *
 * Android/Chromium (Chrome, Edge, Brave, Opera): captures the
 * `beforeinstallprompt` event and replays it on demand — Chrome's auto
 * banner fires unpredictably, so an explicit button is the only reliable
 * way users find the install flow.
 *
 * iOS Safari: `beforeinstallprompt` never fires. We show Share → Add to
 * Home Screen instructions.
 *
 * Samsung Internet / Firefox Android / other Chromium forks:
 * `beforeinstallprompt` is often present but calling `.prompt()` no-ops
 * silently on some builds. When "How to install" is tapped we ALWAYS
 * render browser-specific step-by-step instructions via `pmcInstallSteps()`
 * so no browser leaves the user stuck.
 *
 * Hidden entirely when the app is already running in standalone
 * display-mode. Dismissal persists for 7 days (localStorage).
 */
const DISMISS_KEY = "pmc_install_dismissed_at";
const DISMISS_TTL_MS = 7 * 24 * 3600 * 1000;

function isStandalone() {
  return window.matchMedia?.("(display-mode: standalone)").matches
      || window.navigator.standalone === true;
}

function dismissedRecently() {
  try {
    const at = Number(localStorage.getItem(DISMISS_KEY) || 0);
    return at && Date.now() - at < DISMISS_TTL_MS;
  } catch { return false; }
}

export default function PwaInstallPrompt() {
  const [deferred, setDeferred] = useState(null);
  const [show, setShow] = useState(false);
  const [steps, setSteps] = useState(null);

  useEffect(() => {
    // Allow other components (e.g. the mobile hamburger "Install app"
    // button) to force-show the banner even after a previous dismiss.
    const forceShow = () => {
      try { localStorage.removeItem(DISMISS_KEY); } catch (_) { /* noop */ }
      setShow(true);
    };
    window.addEventListener("pmc:show-install-prompt", forceShow);

    const { browser, isIos } = detectPmcBrowser();

    if (isStandalone() || dismissedRecently()) {
      return () => window.removeEventListener("pmc:show-install-prompt", forceShow);
    }

    const onBeforeInstall = (e) => {
      e.preventDefault();
      // Cache globally so the mobile menu "Install app" button can replay it
      window.__pmcInstallPromptEvent = e;
      setDeferred(e);
      setShow(true);
    };
    window.addEventListener("beforeinstallprompt", onBeforeInstall);

    // iOS + Samsung Internet + Firefox never fire a reliable
    // beforeinstallprompt — show the banner after a short delay so the
    // landing content renders first.
    let t;
    if (isIos || browser === "samsung" || browser === "firefox") {
      t = setTimeout(() => setShow(true), 2500);
    }
    return () => {
      window.removeEventListener("beforeinstallprompt", onBeforeInstall);
      window.removeEventListener("pmc:show-install-prompt", forceShow);
      if (t) clearTimeout(t);
    };
  }, []);

  const dismiss = () => {
    try { localStorage.setItem(DISMISS_KEY, String(Date.now())); } catch {}
    setShow(false);
    setSteps(null);
  };

  const install = async () => {
    if (deferred) {
      try {
        await deferred.prompt();
        const choice = await deferred.userChoice;
        window.__pmcInstallPromptEvent = null;
        setDeferred(null);
        if (choice?.outcome === "accepted") {
          setShow(false);
          return;
        }
        // User explicitly dismissed the native prompt — respect that.
        setShow(false);
        return;
      } catch { /* fall through to manual steps */ }
    }
    setSteps(pmcInstallSteps());
  };

  if (!show) return null;

  return (
    <div className="fixed z-[80] right-4 left-4 sm:left-auto sm:right-6 sm:w-[340px]"
         style={{ bottom: "calc(env(safe-area-inset-bottom, 0px) + 16px)" }}
         data-testid="pwa-install-prompt">
      <div className="bg-brand-navy text-white shadow-2xl border border-brand-gold/40">
        <div className="flex items-start gap-3 p-4">
          <img src="/pmc-logo.png" alt="PMC" className="w-10 h-10 shrink-0" />
          <div className="min-w-0 flex-1">
            <div className="text-[10px] uppercase tracking-[0.2em] text-brand-gold font-semibold">
              PMC Tenders App
            </div>
            <div className="text-sm font-semibold mt-0.5">Install on your phone</div>
            <div className="text-[12px] text-white/70 mt-1 leading-snug">
              {steps
                ? "Follow the steps below to add PMC to your home screen."
                : "One-tap access, offline shell, and push alerts once installed."}
            </div>
            {steps && (
              <div className="mt-2 text-[12px] bg-white/10 p-2 leading-relaxed" data-testid="pwa-install-steps">
                <div className="font-bold text-brand-gold mb-1">{steps.title}</div>
                <ol className="list-decimal pl-4 space-y-1">
                  {steps.steps.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ol>
              </div>
            )}
            <div className="mt-3 flex items-center gap-2">
              <button type="button" onClick={install}
                      data-testid="pwa-install-now"
                      className="px-4 py-2 bg-brand-gold text-brand-navy text-[11px] font-bold uppercase tracking-widest hover:bg-white transition-colors">
                {steps ? "Got it" : "Install app"}
              </button>
              <button type="button" onClick={dismiss}
                      data-testid="pwa-install-dismiss"
                      className="px-3 py-2 text-[11px] uppercase tracking-widest text-white/60 hover:text-white">
                Not now
              </button>
            </div>
          </div>
          <button type="button" onClick={dismiss} aria-label="Close install prompt"
                  data-testid="pwa-install-close"
                  className="text-white/50 hover:text-white text-lg leading-none shrink-0">×</button>
        </div>
      </div>
    </div>
  );
}
