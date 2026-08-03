import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { STRINGS } from "@/lib/i18n-strings";

const I18nContext = createContext({ lang: "en", setLang: () => {}, t: (k) => k });

export function I18nProvider({ children }) {
  const [lang, setLangState] = useState(() => {
    try {
      return localStorage.getItem("pmc_lang") || "en";
    } catch {
      return "en";
    }
  });

  const setLang = (v) => {
    setLangState(v);
    try { localStorage.setItem("pmc_lang", v); }
    catch (err) {
      if (process.env.NODE_ENV !== "production") console.warn("Could not persist language preference:", err);
    }
  };

  useEffect(() => {
    document.documentElement.setAttribute("lang", lang);
  }, [lang]);

  const value = useMemo(() => {
    const bundle = STRINGS[lang] || STRINGS.en;
    return {
      lang, setLang,
      t: (key, fallback) => {
        const parts = key.split(".");
        let cur = bundle;
        for (const p of parts) {
          if (cur && typeof cur === "object" && p in cur) cur = cur[p];
          else return fallback ?? key;
        }
        return typeof cur === "string" ? cur : (fallback ?? key);
      },
    };
    // `STRINGS` is a module-level constant and `bundle`/`parts`/`cur` are
    // locals inside the memo — only `lang` needs to trigger a rebuild.
  }, [lang]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  return useContext(I18nContext);
}
