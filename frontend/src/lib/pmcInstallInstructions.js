/**
 * pmc-install-instructions.js — browser-specific "Install to home screen"
 * copy. Used by the mobile hamburger "Install app" button and the auto
 * PWA banner so every browser has an actionable path, even when
 * `beforeinstallprompt` never fires (Samsung Internet, Firefox mobile,
 * iOS Safari, Chrome desktop before engagement heuristic).
 *
 * Detection is UA-based because Client Hints coverage is inconsistent.
 * Order matters — most specific browsers first.
 */

export function detectPmcBrowser() {
  const ua = (navigator.userAgent || "").toLowerCase();
  const platform = navigator.platform || "";
  const maxTouch = navigator.maxTouchPoints || 0;

  // iPadOS 13+ reports as MacIntel — treat as iOS.
  const isIos = /iphone|ipad|ipod/i.test(ua)
    || (platform === "MacIntel" && maxTouch > 1);
  const isMac = /macintosh|mac os x/i.test(ua) && maxTouch === 0;
  const isAndroid = /android/i.test(ua);
  const isWindows = /windows/i.test(ua);

  let browser = "other";
  if (/samsungbrowser/i.test(ua)) browser = "samsung";
  else if (/fxios|firefox/i.test(ua)) browser = "firefox";
  else if (/opr\/|opera/i.test(ua)) browser = "opera";
  else if (/edg\//i.test(ua)) browser = "edge";
  else if (isIos && /crios/i.test(ua)) browser = "chrome-ios";
  else if (isIos && !/crios|fxios/i.test(ua) && /safari/i.test(ua)) browser = "safari-ios";
  else if (!isIos && /chrome\//i.test(ua)) browser = "chrome";
  else if (!isIos && /safari/i.test(ua)) browser = "safari-desktop";

  return { browser, isIos, isAndroid, isWindows, isMac };
}

/**
 * Step-by-step home-screen install instructions per browser.
 * Each step is a plain string; render with line breaks.
 */
export function pmcInstallSteps() {
  const { browser, isIos, isAndroid } = detectPmcBrowser();

  if (browser === "safari-ios") {
    return {
      title: "Add PMC to your iPhone",
      icon: "share",
      steps: [
        "Tap the Share icon at the bottom of Safari",
        'Scroll and tap "Add to Home Screen"',
        'Tap "Add" — the PMC crest appears on your home screen',
      ],
    };
  }
  if (browser === "chrome-ios") {
    return {
      title: "Add PMC on Chrome for iPhone",
      icon: "share",
      steps: [
        "Tap the ••• menu in the Chrome bar",
        'Tap "Add to Home Screen"',
        "Tap Add to confirm",
      ],
    };
  }
  if (browser === "samsung") {
    return {
      title: "Add PMC on Samsung Internet",
      icon: "menu",
      steps: [
        "Tap the ☰ (Tools) icon at the bottom right of Samsung Internet",
        'Tap "Add page to"',
        'Choose "Home screen" — if you only see "Bookmarks / Saved pages / Quick access", tap the ⋮ menu at the top of the tab and pick "Add page to" → "Home screen"',
        "On Samsung Internet 4+, the Home screen option only appears after you have scrolled or tapped around the site once — refresh once if it is missing",
        "Confirm — PMC appears on your home screen with the PMC icon",
      ],
    };
  }
  if (browser === "firefox" && isAndroid) {
    return {
      title: "Add PMC on Firefox for Android",
      icon: "menu",
      steps: [
        "Tap the ⋮ menu top right",
        'Tap "Install" (or "Add to Home Screen")',
        "Confirm on the prompt",
      ],
    };
  }
  if (browser === "opera" && isAndroid) {
    return {
      title: "Add PMC on Opera for Android",
      icon: "menu",
      steps: [
        "Tap the ☰ menu bottom bar",
        'Tap "Add to…" → "Home screen"',
        "Confirm the install prompt",
      ],
    };
  }
  if (browser === "chrome" && isAndroid) {
    return {
      title: "Add PMC on Chrome",
      icon: "menu",
      steps: [
        'If a banner appears, tap "Install"',
        "Otherwise tap the ⋮ menu top right",
        'Tap "Install app" (or "Add to Home Screen")',
        "Confirm the install prompt",
      ],
    };
  }
  if (browser === "edge" && isAndroid) {
    return {
      title: "Add PMC on Edge",
      icon: "menu",
      steps: [
        "Tap the ⋮ menu bottom bar",
        'Tap "Add to phone" or "Install"',
        "Confirm the install prompt",
      ],
    };
  }
  // Desktop Chrome / Edge / Brave
  if (browser === "chrome" || browser === "edge" || browser === "opera") {
    return {
      title: `Install PMC on ${browser === "edge" ? "Edge" : browser === "opera" ? "Opera" : "Chrome"}`,
      icon: "download",
      steps: [
        'Click the "Install" icon (⤓) in the address bar, or',
        "Open the ⋮ menu top right",
        'Choose "Install PMC…"',
        "Confirm the install prompt",
      ],
    };
  }
  if (browser === "firefox") {
    return {
      title: "Firefox desktop can't install PWAs",
      icon: "info",
      steps: [
        "Firefox for desktop does not support installing web apps.",
        "Bookmark the site or open PMC on your phone (iOS Safari / Android Chrome) to install to home screen.",
      ],
    };
  }
  if (browser === "safari-desktop") {
    return {
      title: "Install PMC on macOS",
      icon: "share",
      steps: [
        "In Safari, click File → Add to Dock… (macOS Sonoma or newer)",
        'Or open the Share menu and choose "Add to Dock"',
        "PMC will open like a native macOS app",
      ],
    };
  }

  // Fallback catch-all
  return {
    title: "Install PMC to your home screen",
    icon: "info",
    steps: [
      "Open your browser's menu (usually ⋮ or ☰)",
      'Look for "Install app", "Add to Home Screen" or "Add page to home screen"',
      "Follow the browser's prompt to confirm",
      "If you don't see the option, open PMC in Chrome, Edge, Samsung Internet or Safari.",
    ],
  };
}
