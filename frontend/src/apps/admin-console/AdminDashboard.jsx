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
import TenderBuilderPanel from "./TenderBuilderPanel";
import EscrowPanel from "./EscrowPanel";
import ReportsPanel from "./ReportsPanel";
import ProductCatalogPanel from "./ProductCatalogPanel";
import EngagementsPanel from "./EngagementsPanel";
import CorrigendaPanel from "./CorrigendaPanel";
import AwardsPanel from "./AwardsPanel";
import LiveAuctionsPanel from "./LiveAuctionsPanel";
import MeetingsPanel from "./MeetingsPanel";
import L1ComparisonPanel from "./L1ComparisonPanel";
import useTenantSkin from "@/apps/shared/useTenantSkin";

function TabBar({ tab, setTab }) {
  const { t } = useI18n();
  const tabs = [
    ["analytics", t("admin.tab_dashboard")],
    ["registrations", t("admin.tab_registrations")],
    ["vendors", t("admin.tab_vendors")],
    ["notices", t("admin.tab_notices")],
    ["corrigenda", t("admin.tab_corrigenda")],
    ["tender-builder", t("admin.tab_tender_builder")],
    ["bidding", t("admin.tab_bidding")],
    ["escrow", t("admin.tab_escrow")],
    ["evaluation", t("admin.tab_evaluation")],
    ["awards", t("admin.tab_awards")],
    ["auctions", t("admin.tab_auctions")],
    ["meetings", t("admin.tab_meetings")],
    ["l1", t("admin.tab_l1")],
    ["boq", t("admin.tab_boq")],
    ["vintel", t("admin.tab_vintel")],
    ["masters", t("admin.tab_masters")],
    ["permissions", t("admin.tab_permissions")],
    ["packages", t("admin.tab_packages")],
    ["audit", t("admin.tab_audit")],
    ["catalog", t("admin.tab_catalog")],
    ["engagements", t("admin.tab_engagements")],
    ["reports", t("admin.tab_reports")],
  ];
  return (
    <>
      {/* Mobile: single-select dropdown so 22 tabs don't overflow */}
      <div className="md:hidden" data-testid="admin-tabs-mobile">
        <label className="pmc-label block mb-1">{t("admin.dash_kicker")}</label>
        <select
          value={tab}
          onChange={(e) => setTab(e.target.value)}
          data-testid="admin-tabs-select"
          className="w-full px-4 py-3 border border-brand-navy/20 bg-white text-brand-navy text-sm font-semibold uppercase tracking-widest"
        >
          {tabs.map(([code, label]) => (
            <option key={code} value={code}>{label}</option>
          ))}
        </select>
      </div>
      {/* Desktop: wrapped chip buttons */}
      <div className="hidden md:flex flex-wrap gap-2" data-testid="admin-tabs">
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
    </>
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

  const logout = async () => { await adminApi.logout(); navigate("/"); };

  if (!me) return <div className="min-h-screen bg-brand-pale flex items-center justify-center text-brand-navy/60">{t("common.loading")}</div>;

  return (
    <div className="min-h-screen bg-brand-pale flex flex-col">
      <TopBar />
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-10 py-6 sm:py-10">
        <div className="flex items-start sm:items-baseline justify-between flex-wrap gap-3 sm:gap-4">
          <div className="min-w-0">
            <div className="pmc-label">{t("admin.dash_kicker")}</div>
            <h1 className="font-display text-2xl sm:text-3xl lg:text-4xl mt-2 text-brand-navy leading-tight">{t("admin.dash_title")}</h1>
          </div>
          <div className="flex items-center flex-wrap gap-2 sm:gap-4 w-full sm:w-auto justify-end">
            {tenant && (
              <div className="text-[10px] sm:text-xs px-2 py-1 border border-brand-navy/20 text-brand-navy/70"
                   data-testid="admin-tenant-chip">
                Portal · {tenant.name}
              </div>
            )}
            <NotificationBell />
            <AuditCopilotButton />
            <button type="button" onClick={() => setMfaOpen(true)} data-testid="admin-mfa-open"
              className="px-2 sm:px-3 py-1.5 text-[10px] sm:text-[11px] uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5">
              {t("admin.header_security")}
            </button>
            <div className="text-right hidden sm:block">
              <div className="pmc-label">{t("admin.header_signed_in")}</div>
              <div className="text-sm text-brand-navy truncate max-w-[180px]">{me.email}</div>
            </div>
            <button type="button" onClick={logout} data-testid="admin-logout"
              className="px-3 sm:px-4 py-2 text-[10px] sm:text-[11px] font-semibold uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5">{t("admin.header_signout")}</button>
          </div>
          <MFASetupModal open={mfaOpen} onClose={() => setMfaOpen(false)} />
        </div>

        <div className="mt-6 sm:mt-8"><TabBar tab={tab} setTab={setTab} /></div>

        <div className="mt-6 sm:mt-8 overflow-x-auto">
          {tab === "analytics" && <AnalyticsPanel />}
          {tab === "registrations" && <RegistrationsPanel />}
          {tab === "vendors" && <VendorsPanel />}
          {tab === "notices" && <NoticesPanel />}
          {tab === "corrigenda" && <CorrigendaPanel />}
          {tab === "tender-builder" && <TenderBuilderPanel />}
          {tab === "bidding" && <BiddingOpsPanel />}
          {tab === "escrow" && <EscrowPanel />}
          {tab === "evaluation" && <EvaluationPanel />}
          {tab === "awards" && <AwardsPanel />}
          {tab === "auctions" && <LiveAuctionsPanel />}
          {tab === "meetings" && <MeetingsPanel />}
          {tab === "l1" && <L1ComparisonPanel />}
          {tab === "boq" && <BOQContractsPanel />}
          {tab === "vintel" && <VendorIntelPanel />}
          {tab === "masters" && <MastersPanel />}
          {tab === "permissions" && <PermissionsPanel />}
          {tab === "packages" && <PackagesPanel />}
          {tab === "audit" && <AuditPanel />}
          {tab === "catalog" && <ProductCatalogPanel />}
          {tab === "engagements" && <EngagementsPanel />}
          {tab === "reports" && <ReportsPanel />}
        </div>
      </main>
    </div>
  );
}
