import { useEffect, useRef, useState } from "react";
import { useI18n } from "@/context/I18nContext";

const LANGS = [
  { code: "en", label: "English",  short: "EN" },
  { code: "ru", label: "Русский",  short: "RU" },
  { code: "kk", label: "Қазақша",  short: "KK" },
];

export default function LangSwitcher({ dark = false }) {
  const { lang, setLang } = useI18n();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const onDown = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, []);

  const current = LANGS.find((l) => l.code === lang) || LANGS[0];
  const btnBase = "inline-flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-widest border transition-colors";
  const btnColor = dark
    ? "bg-transparent border-white/25 text-white hover:bg-white/10"
    : "bg-white border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5";

  return (
    <div ref={ref} className="relative" data-testid="lang-switcher">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        data-testid="lang-toggle"
        aria-haspopup="listbox"
        aria-expanded={open}
        className={`${btnBase} ${btnColor}`}
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2" />
          <path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18" stroke="currentColor" strokeWidth="1.5" />
        </svg>
        <span>{current.short}</span>
        <svg width="8" height="6" viewBox="0 0 8 6" fill="none" aria-hidden="true">
          <path d="M1 1l3 3 3-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="square" />
        </svg>
      </button>
      {open && (
        <ul
          role="listbox"
          data-testid="lang-menu"
          className="absolute right-0 top-full mt-1 min-w-[140px] bg-white border border-brand-navy/15 shadow-lg z-40"
        >
          {LANGS.map((l) => {
            const active = l.code === lang;
            return (
              <li key={l.code} role="option" aria-selected={active}>
                <button
                  type="button"
                  onClick={() => { setLang(l.code); setOpen(false); }}
                  data-testid={`lang-${l.code}`}
                  className={
                    "w-full text-left px-3 py-2 text-sm flex items-center justify-between " +
                    (active
                      ? "bg-brand-navy text-white"
                      : "text-brand-navy hover:bg-brand-navy/5")
                  }
                >
                  <span>{l.label}</span>
                  <span className="text-[10px] font-semibold tracking-widest opacity-70">{l.short}</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
