/**
 * PMC v50 — Option E is now the ONLY UI.
 *
 * `isE` is always true; the legacy Navy UI has been retired.
 * The context is kept so downstream code that still reads `useUiTheme()`
 * continues to work without any changes.
 */
import { createContext, useContext, useEffect } from "react";
import { useLocation } from "react-router-dom";

const UiThemeContext = createContext({ isE: true, theme: "e" });

export function UiThemeProvider({ children }) {
  return <UiThemeContext.Provider value={{ isE: true, theme: "e" }}>{children}</UiThemeContext.Provider>;
}

export function useUiTheme() {
  return useContext(UiThemeContext);
}

/**
 * Router-aware applier — sets `data-ui="e"` on <body> globally.
 */
export function UiThemeApplier() {
  const location = useLocation();
  useEffect(() => {
    document.body.setAttribute("data-ui", "e");
  }, [location.pathname]);
  return null;
}
