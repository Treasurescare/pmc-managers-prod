import { useEffect, useState } from "react";
import { useNavigate, useLocation, Navigate } from "react-router-dom";
import { adminApi } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import ProfileModal from "@/apps/shared/ProfileModal";
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
import ProductCatalogPanel from "./ProductCatalogPanel";
import EngagementsPanel from "./EngagementsPanel";
import CorrigendaPanel from "./CorrigendaPanel";
import AwardsPanel from "./AwardsPanel";
import LiveAuctionsPanel from "./LiveAuctionsPanel";  // v52bz: dead code, kept only for legacy /admin tab route (AdminAuctionsE is the live surface).
import MeetingsPanel from "./MeetingsPanel";
import L1ComparisonPanel from "./L1ComparisonPanel";
import DocuSignPanel from "./DocuSignPanel";
import HelpPanel from "./HelpPanel";
import BillingTransactionsPanel from "./BillingTransactionsPanel";
import AdminShell from "./AdminShell";
import useTenantSkin from "@/apps/shared/useTenantSkin";

export default function AdminDashboard() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const location = useLocation();
  const [me, setMe] = useState(null);
  const initialTab = (() => {
    try { return new URLSearchParams(location.search).get("tab") || "analytics"; }
    catch { return "analytics"; }
  })();
  const [tab, setTabRaw] = useState(initialTab);
  // Sync tab switches back into the URL query string so links can be shared /
  // bookmarked / hit browser-back. Preserves any other query params (e.g. ?ui=e).
  const setTab = (next) => {
    setTabRaw(next);
    try {
      const params = new URLSearchParams(location.search);
      if (next && next !== "analytics") params.set("tab", next);
      else params.delete("tab");
      const q = params.toString();
      navigate(`${location.pathname}${q ? "?" + q : ""}`, { replace: false });
    } catch {}
  };
  const [mfaOpen, setMfaOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const tenant = useTenantSkin();

  useEffect(() => {
    adminApi.me().then(setMe).catch(() => { navigate("/login"); });
  }, [navigate, location.pathname]);

  useEffect(() => {
    try {
      const p = new URLSearchParams(location.search).get("tab");
      if (p) setTab(p);
    } catch { /* noop */ }
  }, [location.search]);

  const logout = async () => { await adminApi.logout(); navigate("/login"); };

  if (!me) return <div className="min-h-screen bg-brand-pale flex items-center justify-center text-brand-navy/60">{t("common.loading")}</div>;
  // Legacy tab console → redirect every tab that has an Option-E page.
  // Tabs without an E equivalent (auctions, meetings, masters, help) stay here.
  const E_TAB_ROUTES = {
    analytics: "/admin/e/dashboard", audit: "/admin/e/audit",
    notices: "/admin/e/notices", corrigenda: "/admin/e/corrigenda",
    "tender-builder": "/admin/e/tender-builder", boq: "/admin/e/boq",
    packages: "/admin/e/work-packages", catalog: "/admin/e/catalog",
    vendors: "/admin/e/vendors", registrations: "/admin/e/registrations",
    vintel: "/admin/e/vendor-intel", engagements: "/admin/e/engagements",
    bidding: "/admin/e/bidding", escrow: "/admin/e/escrow",
    billing: "/admin/e/billing", evaluation: "/admin/e/evaluation",
    l1: "/admin/e/l1-award", awards: "/admin/e/awards",
    docusign: "/admin/e/docusign", permissions: "/admin/e/permissions",
    events: "/admin/e/events", masters: "/admin/e/masters",
  };
  if (E_TAB_ROUTES[tab]) return <Navigate to={E_TAB_ROUTES[tab]} replace />;

  const header = (
    <>
      {tenant && (
        <div className="text-[10px] px-2 py-1 border border-brand-navy/20 text-brand-navy/70 hidden lg:block"
             data-testid="admin-tenant-chip">
          Portal · {tenant.name}
        </div>
      )}
      <NotificationBell />
      <AuditCopilotButton />
      <button type="button" onClick={() => setMfaOpen(true)} data-testid="admin-mfa-open"
        className="hidden sm:block px-3 py-1.5 text-[11px] uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5">
        {t("admin.header_security")}
      </button>
      <button type="button" onClick={() => setProfileOpen(true)} data-testid="admin-profile-open"
        className="w-9 h-9 rounded-full overflow-hidden border border-brand-navy/20 hover:ring-2 hover:ring-brand-navy/30 flex items-center justify-center bg-brand-navy/5">
        {me.avatar_data_url
          ? <img src={me.avatar_data_url} alt="avatar" className="w-full h-full object-cover" />
          : <span className="font-display text-sm text-brand-navy">{(me.email || "?").slice(0, 1).toUpperCase()}</span>}
      </button>
      <button type="button" onClick={logout} data-testid="admin-logout"
        className="px-3 py-2 text-[11px] font-semibold uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5">
        {t("admin.header_signout")}
      </button>
    </>
  );

  return (
    <AdminShell tab={tab} setTab={setTab} header={header}>
      <MFASetupModal open={mfaOpen} onClose={() => setMfaOpen(false)} />
      <ProfileModal open={profileOpen} onClose={() => setProfileOpen(false)}
                    role="admin" me={me} onChange={setMe} />
      <div className="overflow-x-auto min-w-0">
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
          {tab === "docusign" && <DocuSignPanel />}
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
          {tab === "billing" && <BillingTransactionsPanel />}
          {tab === "help" && <HelpPanel />}
      </div>
    </AdminShell>
  );
}
