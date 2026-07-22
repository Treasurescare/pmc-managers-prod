import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import ProtectedRoute from "@/components/app/ProtectedRoute";

import Landing from "@/pages/Landing";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import VendorDashboard from "@/pages/VendorDashboard";
import VendorProfile from "@/pages/VendorProfile";
import MyBids from "@/pages/MyBids";
import BuyerDashboard from "@/pages/BuyerDashboard";
import CreateTender from "@/pages/CreateTender";
import TenderList from "@/pages/TenderList";
import TenderDetail from "@/pages/TenderDetail";
import AdminDashboard from "@/pages/AdminDashboard";
import AdminVendors from "@/pages/AdminVendors";
import AdminUsers from "@/pages/AdminUsers";
import Notifications from "@/pages/Notifications";

function RootRedirect() {
  const { user, checking } = useAuth();
  if (checking) return <div className="pmc-progress" />;
  if (!user) return <Landing />;
  if (user.role === "admin") return <Navigate to="/admin" replace />;
  if (user.role === "buyer") return <Navigate to="/buyer" replace />;
  return <Navigate to="/vendor" replace />;
}

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <Toaster richColors position="top-right" />
          <Routes>
            <Route path="/" element={<RootRedirect />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            <Route path="/vendor" element={<ProtectedRoute roles={["vendor"]}><VendorDashboard /></ProtectedRoute>} />
            <Route path="/vendor/profile" element={<ProtectedRoute roles={["vendor"]}><VendorProfile /></ProtectedRoute>} />
            <Route path="/vendor/bids" element={<ProtectedRoute roles={["vendor"]}><MyBids /></ProtectedRoute>} />

            <Route path="/buyer" element={<ProtectedRoute roles={["buyer"]}><BuyerDashboard /></ProtectedRoute>} />
            <Route path="/buyer/create" element={<ProtectedRoute roles={["buyer", "admin"]}><CreateTender /></ProtectedRoute>} />

            <Route path="/admin" element={<ProtectedRoute roles={["admin"]}><AdminDashboard /></ProtectedRoute>} />
            <Route path="/admin/vendors" element={<ProtectedRoute roles={["admin"]}><AdminVendors /></ProtectedRoute>} />
            <Route path="/admin/users" element={<ProtectedRoute roles={["admin"]}><AdminUsers /></ProtectedRoute>} />

            <Route path="/tenders" element={<ProtectedRoute><TenderList /></ProtectedRoute>} />
            <Route path="/tenders/:id" element={<ProtectedRoute><TenderDetail /></ProtectedRoute>} />

            <Route path="/notifications" element={<ProtectedRoute><Notifications /></ProtectedRoute>} />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </div>
  );
}

export default App;
