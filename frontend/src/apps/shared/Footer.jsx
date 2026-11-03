import { useEffect, useState } from "react";
import { useI18n } from "@/context/I18nContext";
import { api } from "@/lib/api";
import { BUILD_VERSION, BUILD_DATE } from "@/lib/buildStamp";

export default function Footer() {
  const { t } = useI18n();
  // v54g — read the backend version too, so support can see at a glance
  // whether the frontend and backend bundles are in sync (and whether
  // CloudFront is serving a stale JS build vs. a new EB upload).
  const [be, setBe] = useState(null);
  useEffect(() => {
    api.get("/api/v1/_version")
      .then((r) => setBe(r.data))
      .catch(() => setBe({ version: "unreachable" }));
  }, []);
  return (
    <footer className="mt-24 border-t border-brand-navy/10 bg-brand-navy text-white">
      <div className="max-w-7xl mx-auto px-6 lg:px-10 py-10 grid gap-6 md:grid-cols-3">
        <div>
          <div className="pmc-label" style={{ color: "rgba(255,255,255,0.5)" }}>{t("brand.name")}</div>
          <div className="font-display text-2xl mt-2">{t("brand.tagline")}</div>
          <div className="text-white/60 text-sm mt-3 max-w-sm">
            Public tender notice board for the Kazakhstan Integrated Development Programme. Managed by PMC Managers Limited.
          </div>
        </div>
        <div>
          <div className="pmc-label" style={{ color: "rgba(255,255,255,0.5)" }}>Contact</div>
          <div className="text-white/80 text-sm mt-2 space-y-1">
            <div>tenders@pmcmanagers.com</div>
            <div>PMC Procurement Office</div>
          </div>
        </div>
        <div className="text-xs text-white/40 md:text-right md:self-end" data-testid="build-stamp">
          © {new Date().getFullYear()} PMC Managers Limited · Global Tender Grid
          <div className="mt-1 font-mono">
            Frontend <b className="text-white/70">{BUILD_VERSION}</b> · {BUILD_DATE}
            {" · "}
            Backend <b className="text-white/70">{be?.version || "…"}</b>
          </div>
        </div>
      </div>
    </footer>
  );
}
