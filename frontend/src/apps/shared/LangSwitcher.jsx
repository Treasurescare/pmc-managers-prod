import { useI18n } from "@/context/I18nContext";

const LANGS = [
  { code: "en", label: "EN" },
  { code: "ru", label: "RU" },
  { code: "kk", label: "KK" },
];

export default function LangSwitcher({ dark = false }) {
  const { lang, setLang } = useI18n();
  return (
    <div className={`flex items-center gap-0 border ${dark ? "border-white/20" : "border-brand-navy/20"}`} data-testid="lang-switcher">
      {LANGS.map((l) => {
        const active = lang === l.code;
        return (
          <button
            key={l.code}
            type="button"
            onClick={() => setLang(l.code)}
            data-testid={`lang-${l.code}`}
            className={
              "px-3 py-1.5 text-[11px] font-semibold tracking-widest uppercase transition-colors " +
              (active
                ? (dark ? "bg-white text-brand-navy" : "bg-brand-navy text-white")
                : (dark ? "text-white/70 hover:bg-white/10" : "text-brand-navy/60 hover:bg-brand-navy/5"))
            }
          >
            {l.label}
          </button>
        );
      })}
    </div>
  );
}
