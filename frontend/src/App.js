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

// Wave 1 — Staff Portal (multi-role: Escrow/Certifier/Legal/Accounting/Committee)
import StaffLogin from "@/apps/staff-portal/StaffLogin";
import StaffDashboard from "@/apps/staff-portal/StaffDashboard";

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
            <Route path="/admin" element={<AdminDashboard />} />
            <Route path="/admin/*" element={<AdminDashboard />} />

            {/* Vendor Portal */}
            <Route path="/vendor/login" element={<VendorLogin />} />
            <Route path="/vendor/change-password" element={<VendorChangePassword />} />
            <Route path="/vendor" element={<VendorDashboard />} />
            <Route path="/vendor/bid/new/:noticeRef" element={<BidSubmit />} />
            <Route path="/vendor/payment/success" element={<PaymentResult outcome="success" />} />
            <Route path="/vendor/payment/cancel" element={<PaymentResult outcome="cancel" />} />

            {/* Staff Portal */}
            <Route path="/staff/login" element={<StaffLogin />} />
            <Route path="/staff" element={<StaffDashboard />} />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </I18nProvider>
    </div>
  );
}
