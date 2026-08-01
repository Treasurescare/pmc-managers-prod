import { Link } from "react-router-dom";
import PmcLogo from "./PmcLogo";
import LangSwitcher from "./LangSwitcher";
import { useI18n } from "@/context/I18nContext";

export default function TopBar({ dark = false }) {
  const { t } = useI18n();
  const base = dark
    ? "bg-brand-navy text-white border-white/10"
    : "bg-white text-brand-navy border-brand-navy/10";
  return (
    <header className={`w-full border-b ${base}`}>
      <div className="max-w-7xl mx-auto px-6 lg:px-10 py-4 flex items-center justify-between gap-6">
        <Link to="/" className="flex items-center gap-3" data-testid="topbar-brand">
          <PmcLogo size={40} inverse={dark} />
          <div>
            <div className="pmc-label" style={{ color: dark ? "rgba(255,255,255,0.6)" : undefined }}>
              {t("brand.name")}
            </div>
            <div className={`font-display text-lg leading-none tracking-tight ${dark ? "text-white" : "text-brand-navy"}`}>
              {t("brand.tagline")}
            </div>
          </div>
        </Link>

        <nav className="hidden md:flex items-center gap-6 text-[13px] tracking-wide">
          <Link to="/notices" data-testid="nav-notices" className={dark ? "text-white/80 hover:text-white" : "text-brand-navy/70 hover:text-brand-navy"}>
            {t("nav.notices")}
          </Link>
          <Link to="/register" data-testid="nav-register" className={dark ? "text-white/80 hover:text-white" : "text-brand-navy/70 hover:text-brand-navy"}>
            {t("nav.register")}
          </Link>
          <Link to="/register/status" data-testid="nav-status" className={dark ? "text-white/80 hover:text-white" : "text-brand-navy/70 hover:text-brand-navy"}>
            {t("nav.status")}
          </Link>
          <Link to="/admin/login" data-testid="nav-admin" className={dark ? "text-white/50 hover:text-white/80" : "text-brand-navy/40 hover:text-brand-navy/70"}>
            {t("nav.admin")}
          </Link>
        </nav>

        <LangSwitcher dark={dark} />
      </div>
    </header>
  );
}
