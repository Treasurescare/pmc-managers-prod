import "@/App.css";
import "@/pmc-theme-e.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { I18nProvider } from "@/context/I18nContext";
import { UiThemeProvider, UiThemeApplier } from "@/context/UiThemeContext";
import ErrorBoundary from "@/components/ErrorBoundary";
import PwaInstallPrompt from "@/components/PwaInstallPrompt";
import PmcIconSprite from "@/components/PmcIconSprite";
import PmcHelpDrawer from "@/components/PmcHelpDrawer";

// App 4 — Public Tender Notice Board
import NoticeBoardHome from "@/apps/notice-board/NoticeBoardHome";
import NoticeDetail from "@/apps/notice-board/NoticeDetail";

// App 3 — Pre-Tender Registration Portal
import RegistrationStart from "@/apps/registration-portal/RegistrationStart";
import RegistrationResume from "@/apps/registration-portal/RegistrationResume";
import RegistrationStatus from "@/apps/registration-portal/RegistrationStatus";

// App 2 — Admin Console
import AdminLogin from "@/apps/admin-console/AdminLogin";
import AdminDashboard from "@/apps/admin-console/AdminDashboard";

// Wave 1 — Vendor Portal
import VendorLogin from "@/apps/vendor-portal/VendorLogin";
import VendorChangePassword from "@/apps/vendor-portal/VendorChangePassword";
import VendorDashboard from "@/apps/vendor-portal/VendorDashboard";
import BidSubmit from "@/apps/vendor-portal/BidSubmit";
import PaymentResult from "@/apps/vendor-portal/PaymentResult";
import BidPayRedirect from "@/apps/vendor-portal/BidPayRedirect";
import SandboxCheckout from "@/apps/vendor-portal/SandboxCheckout";
import VendorVerifyEmail from "@/apps/vendor-portal/VendorVerifyEmail";

// Wave 1 — Staff Portal (multi-role: Escrow/Certifier/Legal/Accounting/Committee)
import StaffLogin from "@/apps/staff-portal/StaffLogin";
import StaffDashboard from "@/apps/staff-portal/StaffDashboard";

// Wave 9 — External Committee Invite
import CommitteeAccept from "@/apps/committee-portal/CommitteeAccept";

// Wave 12 — Mobile (PWA + Capacitor)
import MobileLogin from "@/apps/mobile/MobileLogin";

// Wave 14 — Unified web login + Admin creates full vendor
import UnifiedLogin from "@/apps/shared/UnifiedLogin";
import AdminVendorCreate from "@/apps/admin-console/AdminVendorCreate";
import AdminBidDetailPage from "@/apps/admin-console/bidding/AdminBidDetailPage";

// Wave 35/36/37 — Revenue surfaces + billing result + public roadmap + escrow magic-link
import ClientPurchase from "@/apps/client-portal/ClientPurchase";
import VendorPurchase from "@/apps/vendor-portal/VendorPurchase";
import BillingResult from "@/apps/shared/BillingResult";
import EscrowOfficerSign from "@/apps/shared/EscrowOfficerSign";
import PublicRoadmap from "@/apps/shared/PublicRoadmap";
import PublicVendorProfile from "@/apps/shared/PublicVendorProfile";
import PublicAuctionRoom from "@/apps/shared/PublicAuctionRoom";

// Wave 40 — Reverse-auction live room
import AuctionRoom from "@/apps/vendor-portal/AuctionRoom";
import AuctionInviteAccept from "@/apps/vendor-portal/AuctionInviteAccept";

// Wave 41 — Meeting room (Jitsi embed via magic-link)
import MeetingRoom from "@/apps/shared/MeetingRoom";

// v46i — editorial public pages + live/completed tender lists
import AboutUs from "@/apps/notice-board/AboutUs";
import VisionMission from "@/apps/notice-board/VisionMission";
import TendersList from "@/apps/notice-board/TendersList";

// v49a — Option E design overhaul (routes exposed when ?ui=e is active)
import HomeE from "@/apps/notice-board-e/HomeE";
import TendersListE from "@/apps/notice-board-e/TendersListE";
import NoticeDetailE from "@/apps/notice-board-e/NoticeDetailE";
import AwardsPublicE from "@/apps/notice-board-e/AwardsPublicE";
import AboutVisionE from "@/apps/notice-board-e/AboutVisionE";
import TrustSecurityE from "@/apps/notice-board-e/TrustSecurityE";
import RegistrationE from "@/apps/registration-e/RegistrationE";
import SignInE from "@/apps/auth-e/SignInE";
import HelpCentreE from "@/apps/help-centre/HelpCentreE";
import HelpArticleE from "@/apps/help-centre/HelpArticleE";
import VendorHomeE from "@/apps/vendor-portal-e/VendorHomeE";
import VendorMyBidsE from "@/apps/vendor-portal-e/VendorMyBidsE";
import VendorBidWorkspaceE from "@/apps/vendor-portal-e/VendorBidWorkspaceE";
import VendorEmdE from "@/apps/vendor-portal-e/VendorEmdE";
import VendorSignaturesE from "@/apps/vendor-portal-e/VendorSignaturesE";
import VendorCompanyKycE from "@/apps/vendor-portal-e/VendorCompanyKycE";
import VendorAccountE from "@/apps/vendor-portal-e/VendorAccountE";
import AdminDashboardE from "@/apps/admin-console-e/AdminDashboardE";
import AdminAuditE from "@/apps/admin-console-e/AdminAuditE";
import AdminNoticesE from "@/apps/admin-console-e/AdminNoticesE";
import AdminTenderBuilderE from "@/apps/admin-console-e/AdminTenderBuilderE";
import AdminBoqContractsE from "@/apps/admin-console-e/AdminBoqContractsE";
import AdminVendorIntelE from "@/apps/admin-console-e/AdminVendorIntelE";
import AdminVendorKycE from "@/apps/admin-console-e/AdminVendorKycE";
import AdminBiddingOpsE from "@/apps/admin-console-e/AdminBiddingOpsE";
import AdminEscrowE from "@/apps/admin-console-e/AdminEscrowE";
import AdminEvaluationE from "@/apps/admin-console-e/AdminEvaluationE";
import AdminL1AwardE from "@/apps/admin-console-e/AdminL1AwardE";
import AdminDocuSignE from "@/apps/admin-console-e/AdminDocuSignE";
import AdminPermissionsE from "@/apps/admin-console-e/AdminPermissionsE";
// v49b — complete 55-template set (new pages)
import ForSuppliersE from "@/apps/notice-board-e/ForSuppliersE";
import ForBuyersE from "@/apps/notice-board-e/ForBuyersE";
import ContactE from "@/apps/notice-board-e/ContactE";
import PrivacyTermsE from "@/apps/notice-board-e/PrivacyTermsE";
import VendorFindTendersE from "@/apps/vendor-portal-e/VendorFindTendersE";
import VendorAlertsE from "@/apps/vendor-portal-e/VendorAlertsE";
import VendorReviewsE from "@/apps/vendor-portal-e/VendorReviewsE";
import AdminProgrammeE from "@/apps/admin-console-e/AdminProgrammeE";
import AdminCorrigendaE from "@/apps/admin-console-e/AdminCorrigendaE";
import AdminWorkPackagesE from "@/apps/admin-console-e/AdminWorkPackagesE";
import AdminCatalogE from "@/apps/admin-console-e/AdminCatalogE";
import AdminVendorsE from "@/apps/admin-console-e/AdminVendorsE";
import AdminRegistrationsE from "@/apps/admin-console-e/AdminRegistrationsE";
import AdminEngagementsE from "@/apps/admin-console-e/AdminEngagementsE";
import AdminBillingE from "@/apps/admin-console-e/AdminBillingE";
import AdminEvaluationListE from "@/apps/admin-console-e/AdminEvaluationListE";
import AdminAwardsE from "@/apps/admin-console-e/AdminAwardsE";
import AdminEventsE from "@/apps/admin-console-e/AdminEventsE";
import DialogsE from "@/apps/reference-e/DialogsE";
import StatesE from "@/apps/reference-e/StatesE";
import EmailsE from "@/apps/reference-e/EmailsE";
import PrintablesE from "@/apps/reference-e/PrintablesE";
import MobileSupplierE from "@/apps/mobile-e/MobileSupplierE";
import MobilePublicE from "@/apps/mobile-e/MobilePublicE";

export default function App() {
  return (
    <div className="App">
      <ErrorBoundary>
      <UiThemeProvider>
      <I18nProvider>
        <BrowserRouter>
          <UiThemeApplier />
          <Toaster
            richColors
            expand
            closeButton
            position="top-right"
            theme="light"
            duration={6000}
            visibleToasts={6}
            toastOptions={{
              // Errors get a longer default and larger footprint so long
              // backend detail messages (e.g. escrow governance remediation)
              // are readable at a glance instead of clipped.
              classNames: {
                error: "border-l-4 border-l-red-600 min-w-[380px] max-w-[560px] shadow-lg",
                success: "border-l-4 border-l-emerald-600 min-w-[320px]",
                warning: "border-l-4 border-l-amber-500 min-w-[320px]",
                info: "border-l-4 border-l-brand-navy min-w-[320px]",
                title: "font-semibold",
                description: "text-[13px] leading-relaxed whitespace-pre-line",
                closeButton: "!bg-white !border !border-brand-navy/20",
              },
            }}
          />
          <PmcIconSprite />
          <PmcHelpDrawer />
          <Routes>
            <Route path="/" element={<HomeE legacy={NoticeBoardHome} />} />
            <Route path="/notices" element={<HomeE legacy={NoticeBoardHome} />} />
            <Route path="/notices/:noticeRef" element={<NoticeDetailE legacy={NoticeDetail} />} />
            <Route path="/about" element={<AboutVisionE legacy={AboutUs} />} />
            <Route path="/vision" element={<AboutVisionE legacy={VisionMission} />} />
            <Route path="/tenders" element={<Navigate to="/tenders/live" replace />} />
            <Route path="/tenders/live" element={<TendersListE legacy={TendersList} />} />
            <Route path="/tenders/completed" element={<AwardsPublicE legacy={TendersList} />} />
            <Route path="/tenders/:mode" element={<TendersList />} />
            <Route path="/trust" element={<TrustSecurityE />} />
            <Route path="/help" element={<HelpCentreE />} />
            <Route path="/help/:slug" element={<HelpArticleE />} />
            {/* v49b — new public Option-E pages */}
            <Route path="/suppliers" element={<ForSuppliersE />} />
            <Route path="/buyers" element={<ForBuyersE />} />
            <Route path="/contact" element={<ContactE />} />
            <Route path="/privacy" element={<PrivacyTermsE />} />
            <Route path="/terms" element={<PrivacyTermsE />} />
            {/* v49b — design reference showcases */}
            <Route path="/design/dialogs" element={<DialogsE />} />
            <Route path="/design/states" element={<StatesE />} />
            <Route path="/design/emails" element={<EmailsE />} />
            <Route path="/design/printables" element={<PrintablesE />} />
            {/* v49b — mobile Option-E shells */}
            <Route path="/m/e/supplier" element={<MobileSupplierE />} />
            <Route path="/m/e/public" element={<MobilePublicE />} />
            <Route path="/vendors/:vendorRef" element={<PublicVendorProfile />} />
            <Route path="/auctions/:aid/live" element={<PublicAuctionRoom />} />

            <Route path="/register" element={<RegistrationE legacy={RegistrationStart} />} />
            <Route path="/register/resume" element={<RegistrationResume />} />
            <Route path="/register/status" element={<RegistrationStatus />} />

            <Route path="/admin/login" element={<AdminLogin />} />
            <Route path="/admin/vendors/new" element={<AdminVendorCreate />} />
            <Route path="/admin/bids/:bidId" element={<AdminBidDetailPage />} />
            {/* Admin Option-E multi-page routes (active when ?ui=e) */}
            <Route path="/admin/e/dashboard" element={<AdminDashboardE />} />
            <Route path="/admin/e/programme" element={<AdminProgrammeE />} />
            <Route path="/admin/e/audit" element={<AdminAuditE />} />
            <Route path="/admin/e/notices" element={<AdminNoticesE />} />
            <Route path="/admin/e/tender-builder" element={<AdminTenderBuilderE />} />
            <Route path="/admin/e/corrigenda" element={<AdminCorrigendaE />} />
            <Route path="/admin/e/work-packages" element={<AdminWorkPackagesE />} />
            <Route path="/admin/e/catalog" element={<AdminCatalogE />} />
            <Route path="/admin/e/boq" element={<AdminBoqContractsE />} />
            <Route path="/admin/e/vendors" element={<AdminVendorsE />} />
            <Route path="/admin/e/registrations" element={<AdminRegistrationsE />} />
            <Route path="/admin/e/engagements" element={<AdminEngagementsE />} />
            <Route path="/admin/e/vendor-intel" element={<AdminVendorIntelE />} />
            <Route path="/admin/e/vendor-kyc" element={<AdminVendorKycE />} />
            <Route path="/admin/e/bidding" element={<AdminBiddingOpsE />} />
            <Route path="/admin/e/escrow" element={<AdminEscrowE />} />
            <Route path="/admin/e/billing" element={<AdminBillingE />} />
            <Route path="/admin/e/evaluations" element={<AdminEvaluationListE />} />
            <Route path="/admin/e/evaluation" element={<AdminEvaluationE />} />
            <Route path="/admin/e/l1-award" element={<AdminL1AwardE />} />
            <Route path="/admin/e/awards" element={<AdminAwardsE />} />
            <Route path="/admin/e/docusign" element={<AdminDocuSignE />} />
            <Route path="/admin/e/permissions" element={<AdminPermissionsE />} />
            <Route path="/admin/e/events" element={<AdminEventsE />} />
            <Route path="/admin" element={<AdminDashboard />} />
            <Route path="/admin/*" element={<AdminDashboard />} />

            {/* Vendor Portal */}
            <Route path="/vendor/login" element={<VendorLogin />} />
            <Route path="/vendor/change-password" element={<VendorChangePassword />} />
            <Route path="/vendor" element={<VendorHomeE legacy={VendorDashboard} />} />
            {/* Vendor Option-E multi-page routes */}
            <Route path="/vendor/mybids" element={<VendorMyBidsE />} />
            <Route path="/vendor/tenders" element={<VendorFindTendersE />} />
            <Route path="/vendor/workspace/:bidId" element={<VendorBidWorkspaceE />} />
            <Route path="/vendor/emd" element={<VendorEmdE />} />
            <Route path="/vendor/signatures" element={<VendorSignaturesE />} />
            <Route path="/vendor/alerts" element={<VendorAlertsE />} />
            <Route path="/vendor/reviews" element={<VendorReviewsE />} />
            <Route path="/vendor/company" element={<VendorCompanyKycE />} />
            <Route path="/vendor/account" element={<VendorAccountE />} />
            <Route path="/vendor/bid/new/:noticeRef" element={<BidSubmit />} />
            <Route path="/vendor/bids/:bidId/pay" element={<BidPayRedirect />} />
            <Route path="/vendor/payment/success" element={<PaymentResult outcome="success" />} />
            <Route path="/vendor/payment/cancel" element={<PaymentResult outcome="cancel" />} />
            <Route path="/vendor/payment/sandbox" element={<SandboxCheckout />} />
            <Route path="/vendor/verify/:token" element={<VendorVerifyEmail />} />
            <Route path="/vendor/auction/invite/:token" element={<AuctionInviteAccept />} />

            {/* Staff Portal */}
            <Route path="/staff/login" element={<StaffLogin />} />
            <Route path="/staff" element={<StaffDashboard />} />

            {/* External Committee accept/decline */}
            <Route path="/committee/accept/:token" element={<CommitteeAccept />} />

            {/* Mobile — unified login (PWA / Capacitor) */}
            <Route path="/m" element={<MobileLogin />} />
            <Route path="/m/login" element={<MobileLogin />} />

            {/* Web — unified sign-in (parallel to /m) */}
            <Route path="/login" element={<SignInE legacy={UnifiedLogin} />} />

            {/* Wave 36/37 — Purchase surfaces */}
            <Route path="/services" element={<ClientPurchase />} />
            <Route path="/vendor/services" element={<VendorPurchase />} />

            {/* Wave 35 — Stripe checkout result pages */}
            <Route path="/billing/success" element={<BillingResult outcome="success" />} />
            <Route path="/billing/cancel" element={<BillingResult outcome="cancel" />} />

            {/* Escrow magic-link portal — non-PMC officer signs via emailed link */}
            <Route path="/escrow/officer/:token" element={<EscrowOfficerSign />} />

            {/* Live public roadmap */}
            <Route path="/roadmap" element={<PublicRoadmap />} />

            <Route path="/vendor/auction/:aid" element={<AuctionRoom />} />

            {/* Wave 41 — Meeting magic-link (Jitsi embed) */}
            <Route path="/meet/:token" element={<MeetingRoom />} />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          <PwaInstallPrompt />
        </BrowserRouter>
      </I18nProvider>
      </UiThemeProvider>
      </ErrorBoundary>
    </div>
  );
}
