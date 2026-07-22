import { AVAILABLE_LANGS, useI18n } from "@/context/I18nContext";

export default function LangSwitcher({ variant = "light", testid = "lang-switcher" }) {
  const { lang, setLang } = useI18n();
  const isDark = variant === "dark";
  return (
    <div data-testid={testid} className={`inline-flex items-center border ${isDark ? "border-white/30" : "border-input"}`}>
      {AVAILABLE_LANGS.map((l) => (
        <button
          key={l.code}
          onClick={() => setLang(l.code)}
          data-testid={`lang-${l.code}`}
          className={`px-2 py-1 text-[11px] font-mono transition-colors ${
            lang === l.code
              ? (isDark ? "bg-white text-black" : "bg-primary text-white")
              : (isDark ? "text-white/60 hover:text-white" : "text-muted-foreground hover:text-foreground")
          }`}
        >
          {l.label}
        </button>
      ))}
    </div>
  );
}
