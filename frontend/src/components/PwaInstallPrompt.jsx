import { useEffect, useState } from "react";

/**
 * PwaInstallPrompt — floating "Install App" affordance.
 *
 * Android (Chrome/Edge/Samsung Internet): captures the `beforeinstallprompt`
 * event and replays it on demand — Chrome's auto banner fires unpredictably,
 * so an explicit button is the only reliable way users find the install flow.
 *
 * iOS Safari: `beforeinstallprompt` never fires; we show Share → Add to Home
 * Screen instructions instead.
 *
 * Hidden entirely when the app is already running in standalone display-mode.
 * Dismissal persists for 7 days (localStorage).
 */
const DISMISS_KEY = "pmc_install_dismissed_at";
const DISMISS_TTL_MS = 7 * 24 * 3600 * 1000;

function isIos() {
  return /iphone|ipad|ipod/i.test(window.navigator.userAgent)
      || (window.navigator.platform === "MacIntel" && window.navigator.maxTouchPoints > 1);
}

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
  const [iosHelp, setIosHelp] = useState(false);

  useEffect(() => {
    if (isStandalone() || dismissedRecently()) return;

    const onBeforeInstall = (e) => {
      e.preventDefault();
      setDeferred(e);
      setShow(true);
    };
    window.addEventListener("beforeinstallprompt", onBeforeInstall);

    // iOS never fires beforeinstallprompt — show the button after a short
    // delay so the landing content renders first.
    let t;
    if (isIos()) {
      t = setTimeout(() => setShow(true), 2500);
    }
    return () => {
      window.removeEventListener("beforeinstallprompt", onBeforeInstall);
      if (t) clearTimeout(t);
    };
  }, []);

  const dismiss = () => {
    try { localStorage.setItem(DISMISS_KEY, String(Date.now())); } catch {}
    setShow(false);
    setIosHelp(false);
  };

  const install = async () => {
    if (deferred) {
      try {
        await deferred.prompt();
        const choice = await deferred.userChoice;
        if (choice?.outcome === "accepted") {
          setShow(false);
          setDeferred(null);
          return;
        }
      } catch { /* fall through to keep the banner */ }
    }
    if (isIos()) setIosHelp(true);
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
              {isIos()
                ? "Tap Share, then “Add to Home Screen” for the full app experience."
                : "One-tap access, offline shell, and push alerts once installed."}
            </div>
            {iosHelp && (
              <div className="mt-2 text-[12px] bg-white/10 p-2 leading-relaxed" data-testid="pwa-install-ios-steps">
                1. Tap the <b>Share</b> icon in Safari<br />
                2. Scroll and tap <b>Add to Home Screen</b><br />
                3. Tap <b>Add</b> — the PMC crest appears on your home screen
              </div>
            )}
            <div className="mt-3 flex items-center gap-2">
              <button type="button" onClick={install}
                      data-testid="pwa-install-now"
                      className="px-4 py-2 bg-brand-gold text-brand-navy text-[11px] font-bold uppercase tracking-widest hover:bg-white transition-colors">
                {isIos() ? "How to install" : "Install app"}
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
