import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { adminApi } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import TopBar from "@/apps/shared/TopBar";
import VendorsPanel from "./VendorsPanel";
import BiddingOpsPanel from "./BiddingOpsPanel";
import EvaluationPanel from "./EvaluationPanel";
import BOQContractsPanel from "./BOQContractsPanel";
import VendorIntelPanel from "./VendorIntelPanel";
import MastersPanel from "./MastersPanel";
import AnalyticsPanel from "./AnalyticsPanel";
import NotificationBell from "./NotificationBell";
import MFASetupModal from "./MFASetupModal";
import AuditCopilotButton from "./AuditCopilotButton";
import PermissionsPanel from "./PermissionsPanel";
import RegistrationsPanel from "./RegistrationsPanel";
import NoticesPanel from "./NoticesPanel";
import AuditPanel from "./AuditPanel";
import PackagesPanel from "./PackagesPanel";
import useTenantSkin from "@/apps/shared/useTenantSkin";

function TabBar({ tab, setTab }) {
  const tabs = [
    ["analytics", "Dashboard"],
    ["registrations", "Registrations"],
    ["vendors", "Vendors"],
    ["notices", "Notices"],
    ["bidding", "Bidding Ops"],
    ["evaluation", "Evaluation"],
    ["boq", "BOQ & Contracts"],
    ["vintel", "Vendor Intel"],
    ["masters", "Masters"],
    ["permissions", "Permissions"],
    ["packages", "Packages"],
    ["audit", "Audit"],
  ];
  return (
    <div className="flex flex-wrap gap-2" data-testid="admin-tabs">
      {tabs.map(([code, label]) => (
        <button
          key={code}
          type="button"
          onClick={() => setTab(code)}
          data-testid={`admin-tab-${code}`}
          className={
            "px-5 py-2 text-[11px] font-semibold uppercase tracking-widest border " +
            (tab === code
              ? "bg-brand-navy text-white border-brand-navy"
              : "bg-white text-brand-navy/70 border-brand-navy/20 hover:border-brand-navy-soft/60")
          }
        >
          {label}
        </button>
      ))}
    </div>
  );
}

export default function AdminDashboard() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const location = useLocation();
  const [me, setMe] = useState(null);
  const [tab, setTab] = useState("analytics");
  const [mfaOpen, setMfaOpen] = useState(false);
  const tenant = useTenantSkin();

  useEffect(() => {
    adminApi.me()
      .then(setMe)
      .catch(() => { navigate("/admin/login"); });
  }, [navigate, location.pathname]);

  const logout = async () => { await adminApi.logout(); navigate("/admin/login"); };

  if (!me) return <div className="min-h-screen bg-brand-pale flex items-center justify-center text-brand-navy/60">{t("common.loading")}</div>;

  return (
    <div className="min-h-screen bg-brand-pale flex flex-col">
      <TopBar />
      <main className="flex-1 max-w-7xl mx-auto w-full px-6 lg:px-10 py-10">
        <div className="flex items-baseline justify-between flex-wrap gap-4">
          <div>
            <div className="pmc-label">{t("admin.dash_kicker")}</div>
            <h1 className="font-display text-3xl lg:text-4xl mt-2 text-brand-navy">{t("admin.dash_title")}</h1>
          </div>
          <div className="flex items-center gap-4">
            {tenant && (
              <div className="text-xs px-2 py-1 border border-brand-navy/20 text-brand-navy/70"
                   data-testid="admin-tenant-chip">
                Portal · {tenant.name}
              </div>
            )}
            <NotificationBell />
            <AuditCopilotButton />
            <button type="button" onClick={() => setMfaOpen(true)} data-testid="admin-mfa-open"
              className="px-3 py-1.5 text-[11px] uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5">
              Security · 2FA
            </button>
            <div className="text-right">
              <div className="pmc-label">Signed in</div>
              <div className="text-sm text-brand-navy">{me.email}</div>
            </div>
            <button type="button" onClick={logout} data-testid="admin-logout"
              className="px-4 py-2 text-[11px] font-semibold uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5">Sign out</button>
          </div>
          <MFASetupModal open={mfaOpen} onClose={() => setMfaOpen(false)} />
        </div>

        <div className="mt-8"><TabBar tab={tab} setTab={setTab} /></div>

        <div className="mt-8">
          {tab === "analytics" && <AnalyticsPanel />}
          {tab === "registrations" && <RegistrationsPanel />}
          {tab === "vendors" && <VendorsPanel />}
          {tab === "notices" && <NoticesPanel />}
          {tab === "bidding" && <BiddingOpsPanel />}
          {tab === "evaluation" && <EvaluationPanel />}
          {tab === "boq" && <BOQContractsPanel />}
          {tab === "vintel" && <VendorIntelPanel />}
          {tab === "masters" && <MastersPanel />}
          {tab === "permissions" && <PermissionsPanel />}
          {tab === "packages" && <PackagesPanel />}
          {tab === "audit" && <AuditPanel />}
        </div>
      </main>
    </div>
  );
}
