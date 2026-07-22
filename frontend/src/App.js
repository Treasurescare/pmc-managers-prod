import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { I18nProvider } from "@/context/I18nContext";
import ProtectedRoute from "@/components/app/ProtectedRoute";

import Landing from "@/pages/Landing";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import AuthCallback from "@/pages/AuthCallback";
import ChooseRole from "@/pages/ChooseRole";
import VendorDashboard from "@/pages/VendorDashboard";
import VendorProfile from "@/pages/VendorProfile";
import VendorPayment from "@/pages/VendorPayment";
import MyBids from "@/pages/MyBids";
import BuyerDashboard from "@/pages/BuyerDashboard";
import CreateTender from "@/pages/CreateTender";
import TenderList from "@/pages/TenderList";
import TenderDetail from "@/pages/TenderDetail";
import AdminDashboard from "@/pages/AdminDashboard";
import AdminVendors from "@/pages/AdminVendors";
import AdminUsers from "@/pages/AdminUsers";
import AdminRfpRfq from "@/pages/AdminRfpRfq";
import AdminOrgs from "@/pages/AdminOrgs";
import AdminAudit from "@/pages/AdminAudit";
import AdminSbd from "@/pages/AdminSbd";
import VendorKpi from "@/pages/VendorKpi";
import Notifications from "@/pages/Notifications";

function RootRedirect() {
  const { user, checking } = useAuth();
  if (checking) return <div className="pmc-progress" />;
  if (!user) return <Landing />;
  if (user.role === "admin") return <Navigate to="/admin" replace />;
  if (user.role === "buyer") return <Navigate to="/buyer" replace />;
  return <Navigate to="/vendor" replace />;
}

function GoogleRedirectGate({ children }) {
  const location = useLocation();
  // Handle Google OAuth session_id in URL fragment before anything else runs
  if (location.hash?.includes("session_id=")) return <AuthCallback />;
  return children;
}

function App() {
  return (
    <div className="App">
      <I18nProvider>
        <AuthProvider>
          <BrowserRouter>
            <Toaster richColors position="top-right" />
            <GoogleRedirectGate>
              <Routes>
                <Route path="/" element={<RootRedirect />} />
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
                <Route path="/auth/callback" element={<AuthCallback />} />
                <Route path="/auth/choose-role" element={<ChooseRole />} />

                <Route path="/vendor" element={<ProtectedRoute roles={["vendor"]}><VendorDashboard /></ProtectedRoute>} />
                <Route path="/vendor/profile" element={<ProtectedRoute roles={["vendor"]}><VendorProfile /></ProtectedRoute>} />
                <Route path="/vendor/payment" element={<ProtectedRoute roles={["vendor"]}><VendorPayment /></ProtectedRoute>} />
                <Route path="/vendor/payment/success" element={<ProtectedRoute roles={["vendor"]}><VendorPayment /></ProtectedRoute>} />
                <Route path="/vendor/payment/cancel" element={<ProtectedRoute roles={["vendor"]}><VendorPayment /></ProtectedRoute>} />
                <Route path="/vendor/bids" element={<ProtectedRoute roles={["vendor"]}><MyBids /></ProtectedRoute>} />
                <Route path="/vendor/kpi" element={<ProtectedRoute roles={["vendor"]}><VendorKpi /></ProtectedRoute>} />

                <Route path="/buyer" element={<ProtectedRoute roles={["buyer"]}><BuyerDashboard /></ProtectedRoute>} />
                <Route path="/buyer/create" element={<ProtectedRoute roles={["buyer", "admin"]}><CreateTender /></ProtectedRoute>} />

                <Route path="/admin" element={<ProtectedRoute roles={["admin"]}><AdminDashboard /></ProtectedRoute>} />
                <Route path="/admin/vendors" element={<ProtectedRoute roles={["admin"]}><AdminVendors /></ProtectedRoute>} />
                <Route path="/admin/users" element={<ProtectedRoute roles={["admin"]}><AdminUsers /></ProtectedRoute>} />
                <Route path="/admin/rfp-rfq" element={<ProtectedRoute roles={["admin"]}><AdminRfpRfq /></ProtectedRoute>} />
                <Route path="/admin/rfp-rfq/new" element={<ProtectedRoute roles={["admin"]}><CreateTender /></ProtectedRoute>} />
                <Route path="/admin/orgs" element={<ProtectedRoute roles={["admin"]}><AdminOrgs /></ProtectedRoute>} />
                <Route path="/admin/audit" element={<ProtectedRoute roles={["admin"]}><AdminAudit /></ProtectedRoute>} />
                <Route path="/admin/sbd" element={<ProtectedRoute roles={["admin"]}><AdminSbd /></ProtectedRoute>} />

                <Route path="/tenders" element={<ProtectedRoute><TenderList /></ProtectedRoute>} />
                <Route path="/tenders/:id" element={<ProtectedRoute><TenderDetail /></ProtectedRoute>} />

                <Route path="/notifications" element={<ProtectedRoute><Notifications /></ProtectedRoute>} />

                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </GoogleRedirectGate>
          </BrowserRouter>
        </AuthProvider>
      </I18nProvider>
    </div>
  );
}

export default App;
