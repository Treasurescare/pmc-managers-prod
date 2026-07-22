import { NavLink, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { LayoutDashboard, FileStack, Gavel, Users, Bell, LogOut, Building2, PlusSquare, ShieldCheck, CreditCard, ClipboardList } from "lucide-react";
import PmcLogo from "./PmcLogo";
import LangSwitcher from "./LangSwitcher";
import { useAuth } from "@/context/AuthContext";
import api from "@/lib/api";

function navFor(role) {
  if (role === "admin")
    return [
      { to: "/admin", label: "Overview", icon: LayoutDashboard, testid: "nav-admin-overview" },
      { to: "/admin/vendors", label: "Vendor Approvals", icon: ShieldCheck, testid: "nav-admin-vendors" },
      { to: "/admin/rfp-rfq", label: "RFP / RFQ", icon: ClipboardList, testid: "nav-admin-rfp-rfq" },
      { to: "/tenders", label: "All Tenders", icon: FileStack, testid: "nav-admin-tenders" },
      { to: "/admin/users", label: "Users", icon: Users, testid: "nav-admin-users" },
      { to: "/notifications", label: "Notifications", icon: Bell, testid: "nav-notifications" },
    ];
  if (role === "buyer")
    return [
      { to: "/buyer", label: "Overview", icon: LayoutDashboard, testid: "nav-buyer-overview" },
      { to: "/buyer/create", label: "New Tender", icon: PlusSquare, testid: "nav-buyer-create" },
      { to: "/buyer/create?type=rfp", label: "New RFP", icon: ClipboardList, testid: "nav-buyer-new-rfp" },
      { to: "/buyer/create?type=rfq", label: "New RFQ", icon: ClipboardList, testid: "nav-buyer-new-rfq" },
      { to: "/tenders?mine=1", label: "My Tenders", icon: FileStack, testid: "nav-buyer-mine" },
      { to: "/notifications", label: "Notifications", icon: Bell, testid: "nav-notifications" },
    ];
  return [
    { to: "/vendor", label: "Overview", icon: LayoutDashboard, testid: "nav-vendor-overview" },
    { to: "/vendor/profile", label: "Company Profile", icon: Building2, testid: "nav-vendor-profile" },
    { to: "/vendor/payment", label: "Registration Fee", icon: CreditCard, testid: "nav-vendor-payment" },
    { to: "/tenders", label: "Open Tenders", icon: FileStack, testid: "nav-vendor-tenders" },
    { to: "/vendor/bids", label: "My Bids", icon: Gavel, testid: "nav-vendor-bids" },
    { to: "/notifications", label: "Notifications", icon: Bell, testid: "nav-notifications" },
  ];
}

export default function DashboardLayout({ children, title, subtitle, actions }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const { data } = await api.get("/notifications");
        if (mounted) setUnread(data.filter((n) => !n.read).length);
      } catch {}
    };
    load();
    const iv = setInterval(load, 20000);
    return () => { mounted = false; clearInterval(iv); };
  }, []);

  const doLogout = async () => { await logout(); navigate("/login"); };
  const items = navFor(user?.role);

  return (
    <div className="min-h-screen grid grid-cols-1 lg:grid-cols-[280px_1fr] bg-background">
      {/* Sidebar */}
      <aside className="hidden lg:flex flex-col bg-[#050505] text-white border-r border-white/10">
        <div className="p-6 border-b border-white/10">
          <PmcLogo variant="dark" />
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {items.map((it) => (
            <NavLink
              key={it.to}
              to={it.to}
              end
              data-testid={it.testid}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 text-sm border-l-2 transition-colors ${
                  isActive ? "border-primary bg-white/5 text-white" : "border-transparent text-white/70 hover:text-white hover:bg-white/5"
                }`
              }
            >
              <it.icon className="h-4 w-4" />
              <span className="font-medium">{it.label}</span>
              {it.to === "/notifications" && unread > 0 && (
                <span className="ml-auto font-mono text-[10px] bg-primary text-white px-2 py-0.5">{unread}</span>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-white/10 space-y-2">
          <div className="text-xs text-white/60">Signed in as</div>
          <div className="text-sm text-white truncate" data-testid="sidebar-user-email">{user?.email}</div>
          <div className="pmc-label text-white/50">{user?.role}</div>
          <button
            data-testid="logout-btn"
            onClick={doLogout}
            className="mt-3 w-full flex items-center justify-center gap-2 border border-white/20 py-2 text-xs hover:bg-white/10 transition-colors"
          >
            <LogOut className="h-3.5 w-3.5" /> Log out
          </button>
        </div>
      </aside>

      {/* Content */}
      <div className="flex flex-col">
        {/* Mobile top nav */}
        <div className="lg:hidden flex items-center justify-between border-b bg-white px-4 py-3">
          <PmcLogo />
          <button data-testid="mobile-logout-btn" onClick={doLogout} className="text-xs border px-3 py-2">Log out</button>
        </div>

        <header className="bg-white/70 backdrop-blur-xl border-b sticky top-0 z-30 px-6 lg:px-10 py-6">
          <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
            <div>
              <div className="pmc-label mb-2">{user?.role?.toUpperCase() || ""} · PMC Global Board</div>
              <h1 className="font-serif text-3xl md:text-4xl tracking-tight">{title}</h1>
              {subtitle && <p className="text-sm text-muted-foreground mt-2 max-w-2xl">{subtitle}</p>}
            </div>
            {actions && <div className="flex flex-wrap gap-2 items-center">{actions}<LangSwitcher testid="header-lang" /></div>}
            {!actions && <LangSwitcher testid="header-lang" />}
          </div>
        </header>

        <main className="flex-1 p-6 lg:p-10 min-w-0">{children}</main>
      </div>
    </div>
  );
}
