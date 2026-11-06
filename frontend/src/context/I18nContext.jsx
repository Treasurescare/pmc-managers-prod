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

  const [extra, setExtra] = useState({});

  useEffect(() => {
    document.documentElement.setAttribute("lang", lang);
    if (STRINGS[lang] || extra[lang]) return;
    fetch(`/i18n/${lang}.json`).then((r) => (r.ok ? r.json() : null))
      .then((j) => { if (j) setExtra((x) => ({ ...x, [lang]: j })); }).catch(() => {});
  }, [lang, extra]);

  const value = useMemo(() => {
    const bundle = STRINGS[lang] || extra[lang] || STRINGS.en;
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
  }, [lang, extra]); <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  return useContext(I18nContext);
}
