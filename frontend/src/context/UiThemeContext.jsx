/**
 * PMC v48a — Option E UI Theme Toggle
 *
 * Opt-in only. Legacy "Tender-Hub" (v47h) UI remains the default.
 *
 * How to activate Option E ("forest green / gold / cream"):
 *   - Append `?ui=e` to any URL (sticks in localStorage)
 *   - Or run in devtools: localStorage.setItem('pmc_ui_theme','e')
 *
 * How to revert to legacy at any time:
 *   - Append `?ui=default` to any URL, or
 *   - Run: localStorage.removeItem('pmc_ui_theme')
 *
 * Design guardrail:
 *   When Option E is on, we set `data-ui="e"` on <body> for ALL non-admin routes.
 *   That makes every public/vendor/staff/registration screen inherit the Option E
 *   palette automatically via CSS overrides scoped under `[data-ui="e"]`.
 *   Admin routes (`/admin/*`) intentionally leave <body> unthemed — the admin
 *   Overview panel opts itself in via a local `data-ui="e"` wrapper, keeping the
 *   admin shell/topbar/tabs looking exactly like legacy.
 */
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";

const STORAGE_KEY = "pmc_ui_theme";
const UiThemeContext = createContext({ isE: false });

function readInitial() {
  try {
    const params = new URLSearchParams(window.location.search);
    const q = params.get("ui");
    if (q === "e") {
      window.localStorage.setItem(STORAGE_KEY, "e");
      return "e";
    }
    if (q === "default" || q === "legacy" || q === "off") {
      window.localStorage.removeItem(STORAGE_KEY);
      return "default";
    }
    return window.localStorage.getItem(STORAGE_KEY) === "e" ? "e" : "default";
  } catch {
    return "default";
  }
}

export function UiThemeProvider({ children }) {
  const [theme, setTheme] = useState(readInitial);

  useEffect(() => {
    const sync = () => setTheme(readInitial());
    window.addEventListener("popstate", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("popstate", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  const value = useMemo(() => ({ isE: theme === "e", theme, setTheme }), [theme]);
  return <UiThemeContext.Provider value={value}>{children}</UiThemeContext.Provider>;
}

export function useUiTheme() {
  return useContext(UiThemeContext);
}

/**
 * Router-aware applier — mounts inside <BrowserRouter> and toggles
 * body.dataset.ui based on both the flag and the current pathname.
 * Admin routes NEVER receive body-level theming (per design constraint).
 */
export function UiThemeApplier() {
  const { isE } = useUiTheme();
  const location = useLocation();
  useEffect(() => {
    if (isE) {
      document.body.setAttribute("data-ui", "e");
    } else {
      document.body.removeAttribute("data-ui");
    }
  }, [isE, location.pathname, location.search]);
  return null;
}

