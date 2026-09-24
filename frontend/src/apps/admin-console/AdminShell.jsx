import { useEffect, useMemo, useState } from "react";
import { InfoDot } from "@/components/InfoDot";

/** AdminShell — collapsible left sidebar (desktop) + hamburger drawer (mobile).
 *
 *  Groups the 24 admin panels into 5 sections. Users can flip between
 *  three navigation modes via the toggle in the sidebar footer:
 *    - "full"      — icon + label rail (default)
 *    - "icons"     — icon-only rail (space-saving)
 *    - "hamburger" — desktop-hidden drawer, opens from top-left button
 *
 *  Mode is persisted in localStorage so admins keep their preference.
 */

// Section groups — order = display order
const GROUPS = [
  { code: "overview",   title: "Overview",
    tabs: [["analytics", "Dashboard", "M3 3h7v9H3z m11 0h7v5h-7z m0 9h7v7h-7z m-11-2h7v9H3z"],
            ["audit",     "Audit log", "M5 3h14v18H5z M9 8h6M9 12h6M9 16h4"]] },
  { code: "procurement", title: "Procurement",
    tabs: [["notices",         "Notices",         "M4 5h16v14H4z M8 9h8M8 13h8M8 17h5"],
            ["corrigenda",      "Corrigenda",      "M12 5v14M5 12h14"],
            ["tender-builder",  "Tender Builder",  "M4 4h16v6H4z M4 14h10v6H4z M17 14h3v6h-3z"],
            ["boq",             "BOQ & Contracts", "M4 6h16v3H4z M4 11h16v3H4z M4 16h10v3H4z"],
            ["packages",        "Work packages",   "M12 3l9 5v8l-9 5-9-5V8z"],
            ["catalog",         "Catalog",         "M4 4h7v7H4z M13 4h7v7h-7z M4 13h7v7H4z M13 13h7v7h-7z"]] },
  { code: "market", title: "Market",
    tabs: [["vendors",       "Vendors",         "M6 20a6 6 0 0 1 12 0 M12 4a4 4 0 1 1 0 8 4 4 0 0 1 0-8"],
            ["registrations", "Registrations",   "M6 4h9l3 3v13H6z M9 9h6M9 13h6M9 17h4"],
            ["vintel",        "Vendor intel",    "M4 4h16v14l-4-4H4z"],
            ["engagements",   "Engagements",     "M4 6h16v12H4z M8 6v12M16 6v12"]] },
  { code: "money", title: "Money & Compliance",
    tabs: [["escrow",     "Escrow / EMD",   "M4 8h16v10H4z M8 8V6a4 4 0 0 1 8 0v2"],
            ["billing",    "Billing",        "M4 6h16v3H4z M4 13h16v5H4z M8 15h4"],
            ["evaluation", "Evaluation",     "M4 6h16v14H4z M9 12l2 2 4-4"],
            ["l1",         "L1 comparison",  "M4 20V6M10 20v-8M16 20V4M22 20H2"],
            ["awards",     "Awards",         "M12 3l3 6 6 1-4.5 4 1 6-5.5-3-5.5 3 1-6L3 10l6-1z"],
            ["docusign",   "DocuSign",       "M4 4h16v14H4z M8 9h8M8 13h5"],
            ["permissions","Permissions",    "M4 8v10a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8 M8 8V6a4 4 0 0 1 8 0v2"]] },
  { code: "events", title: "Events",
    tabs: [["auctions", "Reverse auctions", "M4 20l16-16 M14 4h6v6 M10 10l4-4M14 20l6-6"],
            ["meetings", "Meetings",        "M4 6h16v14H4z M4 10h16M9 3v4M15 3v4"],
            ["masters",  "Masters",         "M4 4h6v6H4z M14 4h6v6h-6z M4 14h6v6H4z M14 14h6v6h-6z"],
            ["help",     "Help",            "M12 3a9 9 0 1 1 0 18 9 9 0 0 1 0-18z M12 17h.01 M9.5 9a2.5 2.5 0 1 1 3.5 2.3v2.2"]] },
];

function Icon({ path, active }) {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16"
         fill="none" stroke="currentColor" strokeWidth="1.7"
         strokeLinecap="round" strokeLinejoin="round"
         className={active ? "text-brand-gold" : "text-white/70"}>
      <path d={path} />
    </svg>
  );
}

export default function AdminShell({ tab, setTab, header, children }) {
  const [mode, setMode] = useState(
    typeof window !== "undefined"
      ? (localStorage.getItem("pmc_admin_nav") || "full")
      : "full");
  const [drawerOpen, setDrawerOpen] = useState(false);
  useEffect(() => {
    try { localStorage.setItem("pmc_admin_nav", mode); } catch {}
  }, [mode]);

  // Find which section owns the current tab (for auto-open)
  const activeGroup = useMemo(
    () => GROUPS.find((g) => g.tabs.some(([t]) => t === tab))?.code || GROUPS[0].code,
    [tab]);
  const [openGroup, setOpenGroup] = useState(activeGroup);
  useEffect(() => { setOpenGroup(activeGroup); }, [activeGroup]);

  const isDrawer = mode === "hamburger";
  const isIcons  = mode === "icons";

  const railWidth = isIcons ? "w-16" : "w-64";

  const NavList = ({ compact }) => (
    <nav className={"flex-1 overflow-y-auto py-4 " + (compact ? "" : "px-3")}
         data-testid="admin-sidebar-nav">
      {GROUPS.map((g) => {
        const isOpen = openGroup === g.code;
        return (
          <div key={g.code} className="mb-1">
            {!compact && (
              <button type="button" onClick={() => setOpenGroup(isOpen ? "" : g.code)}
                      data-testid={`admin-sb-group-${g.code}`}
                      className="w-full flex items-center justify-between px-3 py-2 text-[10px] uppercase tracking-widest text-white/50 hover:text-white/90">
                {g.title}
                <span className="text-white/40">{isOpen ? "▾" : "▸"}</span>
              </button>
            )}
            {(compact || isOpen) && g.tabs.map(([code, label, path]) => (
              <button key={code} type="button"
                onClick={() => { setTab(code); setDrawerOpen(false); }}
                data-testid={`admin-tab-${code}`}
                title={compact ? label : undefined}
                className={"w-full flex items-center gap-3 py-2 text-left transition-colors " +
                  (compact ? "justify-center px-0" : "px-3") + " " +
                  (tab === code
                    ? "bg-white/10 text-white border-l-2 border-brand-gold"
                    : "text-white/80 hover:bg-white/5 hover:text-white border-l-2 border-transparent")}>
                <Icon path={path} active={tab === code} />
                {!compact && <span className="text-sm">{label}</span>}
              </button>
            ))}
          </div>
        );
      })}
    </nav>
  );

  return (
    <div className="min-h-screen bg-brand-pale flex" data-testid="admin-shell">
      {/* Desktop sidebar */}
      {!isDrawer && (
        <aside className={"hidden md:flex flex-col bg-brand-navy text-white " + railWidth}
               data-testid={`admin-sidebar-${mode}`}>
          <div className="px-4 py-5 border-b border-white/10 flex items-center gap-2">
            <div className="w-7 h-7 bg-brand-gold flex items-center justify-center font-display text-brand-navy">P</div>
            {!isIcons && <div className="font-display text-lg">PMC Admin</div>}
          </div>
          <NavList compact={isIcons} />
          <div className="border-t border-white/10 p-2 flex justify-around text-[10px]" data-testid="admin-sidebar-mode-toggle">
            {[["full","≡"], ["icons","▤"], ["hamburger","☰"]].map(([m, sym]) => (
              <button key={m} type="button" onClick={() => setMode(m)}
                      data-testid={`admin-sidebar-mode-${m}`}
                      title={"Nav mode: " + m}
                      className={"px-2 py-1 " + (mode === m
                        ? "bg-brand-gold text-brand-navy"
                        : "text-white/60 hover:text-white")}>{sym}</button>
            ))}
          </div>
        </aside>
      )}

      {/* Drawer (mobile always, or desktop when mode=hamburger) */}
      {(isDrawer || drawerOpen) && (
        <>
          <div className={"fixed inset-0 bg-brand-navy/50 z-40 " + (drawerOpen ? "block" : "hidden md:block md:hidden")}
               onClick={() => setDrawerOpen(false)} />
          <aside className={"fixed inset-y-0 left-0 z-50 w-72 bg-brand-navy text-white flex flex-col " +
                             (drawerOpen ? "block" : "hidden") + " md:" + (isDrawer && drawerOpen ? "flex" : "hidden")}
                 data-testid="admin-sidebar-drawer">
            <div className="px-4 py-5 border-b border-white/10 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 bg-brand-gold flex items-center justify-center font-display text-brand-navy">P</div>
                <div className="font-display text-lg">PMC Admin</div>
              </div>
              <button type="button" onClick={() => setDrawerOpen(false)} data-testid="admin-drawer-close"
                      className="text-white/70 hover:text-white text-xl">×</button>
            </div>
            <NavList compact={false} />
            <div className="border-t border-white/10 p-2 flex justify-around text-[10px]">
              {[["full","≡"], ["icons","▤"], ["hamburger","☰"]].map(([m, sym]) => (
                <button key={m} type="button" onClick={() => setMode(m)}
                        title={"Nav mode: " + m}
                        className={"px-2 py-1 " + (mode === m
                          ? "bg-brand-gold text-brand-navy"
                          : "text-white/60 hover:text-white")}>{sym}</button>
              ))}
            </div>
          </aside>
        </>
      )}

      {/* Main column */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="bg-white border-b border-brand-navy/10 sticky top-0 z-30">
          <div className="px-4 lg:px-8 h-14 flex items-center gap-3">
            {Boolean(isDrawer || true) && (
              <button type="button" onClick={() => setDrawerOpen(true)}
                      data-testid="admin-hamburger"
                      className={"p-2 border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5 " + (isDrawer ? "" : "md:hidden")}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M3 6h18M3 12h18M3 18h18" />
                </svg>
              </button>
            )}
            <div className="font-display text-brand-navy text-lg truncate">
              {GROUPS.flatMap((g) => g.tabs).find(([c]) => c === tab)?.[1] || "Admin"}
            </div>
            <div className="flex-1" />
            {header}
          </div>
        </header>
        <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-10 py-6 lg:py-10 min-w-0">
          {children}
        </main>
      </div>
    </div>
  );
}
