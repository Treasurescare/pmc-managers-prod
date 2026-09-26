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
 *   Components decide WHERE Option E applies. This hook only reports the flag.
 *   Public / vendor screens wrap their root with `data-ui={isE ? 'e' : undefined}`.
 *   Admin shell stays legacy — only the Overview panel wraps itself with data-ui.
 */
import { createContext, useContext, useEffect, useMemo, useState } from "react";

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

  // Re-evaluate on popstate + storage events so the flag stays consistent across tabs
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
