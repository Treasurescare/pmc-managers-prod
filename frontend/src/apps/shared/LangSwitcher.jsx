import { useEffect, useRef, useState } from "react";
import { useI18n } from "@/context/I18nContext";

export const LANGS = [
  { code: "en", label: "English", flag: "us" }, { code: "ru", label: "Русский", flag: "ru" }, { code: "kk", label: "Қазақша", flag: "kz" },
  { code: "zh-Hans", label: "简体中文 (普通话)", flag: "cn" }, { code: "zh-Hant", label: "繁體中文 (粵語)", flag: "hk" },
  { code: "es", label: "Español", flag: "es" }, { code: "fr", label: "Français", flag: "fr" }, { code: "de", label: "Deutsch", flag: "de" },
  { code: "hi", label: "हिन्दी", flag: "in" }, { code: "ms", label: "Bahasa Melayu", flag: "my" }, { code: "id", label: "Bahasa Indonesia", flag: "id" },
  { code: "ko", label: "한국어", flag: "kr" }, { code: "ja", label: "日本語", flag: "jp" }, { code: "ar", label: "العربية", flag: "sa" },
];

const Flag = ({ c }) => <img src={`/flags/${c}.svg`} alt="" width={20} height={14} style={{ width: 20, height: 14, objectFit: "cover", borderRadius: 2, boxShadow: "0 0 0 1px rgba(0,0,0,.12)" }} />;

export default function LangSwitcher({ dark = false }) {
  const { lang, setLang } = useI18n();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const cur = LANGS.find((l) => l.code === lang) || LANGS[0];
  useEffect(() => {
    const close = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);
  return (
    <div className="relative notranslate" ref={ref} translate="no" data-testid="lang-switcher">
      <button type="button" onClick={() => setOpen((o) => !o)} aria-label="Change language" data-testid="lang-toggle"
        className={`inline-flex items-center gap-2 px-2.5 py-1.5 text-xs font-semibold border ${dark ? "border-white/30 text-white hover:bg-white/10" : "border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5"}`}>
        <Flag c={cur.flag} /><span>{cur.code.split("-")[0].toUpperCase()}</span><span aria-hidden="true">▾</span>
      </button>
      {open && (
        <ul className="absolute right-0 top-full mt-1 min-w-[210px] max-h-[70vh] overflow-y-auto bg-white border border-black/15 shadow-lg z-[80] text-left" role="listbox" data-testid="lang-menu">
          {LANGS.map((l) => (
            <li key={l.code}>
              <button type="button" onClick={() => { setLang(l.code); setOpen(false); }} data-testid={`lang-${l.code}`}
                className={`w-full flex items-center gap-2 px-3 py-2 text-sm text-[#162921] hover:bg-black/5 ${l.code === lang ? "font-semibold bg-black/5" : ""}`}>
                <Flag c={l.flag} />{l.label}
              </button>
            </li>))}
        </ul>)}
    </div>);
}
