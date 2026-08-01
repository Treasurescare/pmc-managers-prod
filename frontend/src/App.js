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

// App 2 — Admin Console (Package Tracker + Registration Review)
import AdminLogin from "@/apps/admin-console/AdminLogin";
import AdminDashboard from "@/apps/admin-console/AdminDashboard";

export default function App() {
  return (
    <div className="App">
      <I18nProvider>
        <BrowserRouter>
          <Toaster richColors position="top-right" theme="light" />
          <Routes>
            {/* App 4 — Public Notice Board (default landing) */}
            <Route path="/" element={<NoticeBoardHome />} />
            <Route path="/notices" element={<NoticeBoardHome />} />
            <Route path="/notices/:noticeRef" element={<NoticeDetail />} />

            {/* App 3 — Registration Portal */}
            <Route path="/register" element={<RegistrationStart />} />
            <Route path="/register/resume" element={<RegistrationResume />} />
            <Route path="/register/status" element={<RegistrationStatus />} />

            {/* App 2 — Admin Console */}
            <Route path="/admin/login" element={<AdminLogin />} />
            <Route path="/admin" element={<AdminDashboard />} />
            <Route path="/admin/*" element={<AdminDashboard />} />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </I18nProvider>
    </div>
  );
}
