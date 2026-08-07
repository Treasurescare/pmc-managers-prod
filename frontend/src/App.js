import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { I18nProvider } from "@/context/I18nContext";

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

// Wave 35/36/37 — Revenue surfaces + billing result + public roadmap + escrow magic-link
import ClientPurchase from "@/apps/client-portal/ClientPurchase";
import VendorPurchase from "@/apps/vendor-portal/VendorPurchase";
import BillingResult from "@/apps/shared/BillingResult";
import EscrowOfficerSign from "@/apps/shared/EscrowOfficerSign";
import PublicRoadmap from "@/apps/shared/PublicRoadmap";

// Wave 40 — Reverse-auction live room
import AuctionRoom from "@/apps/vendor-portal/AuctionRoom";

// Wave 41 — Meeting room (Jitsi embed via magic-link)
import MeetingRoom from "@/apps/shared/MeetingRoom";

export default function App() {
  return (
    <div className="App">
      <I18nProvider>
        <BrowserRouter>
          <Toaster richColors position="top-right" theme="light" />
          <Routes>
            <Route path="/" element={<NoticeBoardHome />} />
            <Route path="/notices" element={<NoticeBoardHome />} />
            <Route path="/notices/:noticeRef" element={<NoticeDetail />} />

            <Route path="/register" element={<RegistrationStart />} />
            <Route path="/register/resume" element={<RegistrationResume />} />
            <Route path="/register/status" element={<RegistrationStatus />} />

            <Route path="/admin/login" element={<AdminLogin />} />
            <Route path="/admin/vendors/new" element={<AdminVendorCreate />} />
            <Route path="/admin" element={<AdminDashboard />} />
            <Route path="/admin/*" element={<AdminDashboard />} />

            {/* Vendor Portal */}
            <Route path="/vendor/login" element={<VendorLogin />} />
            <Route path="/vendor/change-password" element={<VendorChangePassword />} />
            <Route path="/vendor" element={<VendorDashboard />} />
            <Route path="/vendor/bid/new/:noticeRef" element={<BidSubmit />} />
            <Route path="/vendor/payment/success" element={<PaymentResult outcome="success" />} />
            <Route path="/vendor/payment/cancel" element={<PaymentResult outcome="cancel" />} />
            <Route path="/vendor/payment/sandbox" element={<SandboxCheckout />} />
            <Route path="/vendor/verify/:token" element={<VendorVerifyEmail />} />

            {/* Staff Portal */}
            <Route path="/staff/login" element={<StaffLogin />} />
            <Route path="/staff" element={<StaffDashboard />} />

            {/* External Committee accept/decline */}
            <Route path="/committee/accept/:token" element={<CommitteeAccept />} />

            {/* Mobile — unified login (PWA / Capacitor) */}
            <Route path="/m" element={<MobileLogin />} />
            <Route path="/m/login" element={<MobileLogin />} />

            {/* Web — unified sign-in (parallel to /m) */}
            <Route path="/login" element={<UnifiedLogin />} />

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
        </BrowserRouter>
      </I18nProvider>
    </div>
  );
}
