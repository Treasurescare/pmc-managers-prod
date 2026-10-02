import AdminAvatarMenu from "./AdminAvatarMenu";

// Shared Option E admin shell (sidebar + top bar) so E pages can mount the
// fully-wired legacy panels without duplicating chrome markup.
export default function AdminEShell({ active, crumb, children }) {
  const items = [
    ["Overview", null, null],
    ["Dashboard", "/admin/e/dashboard", "i-home"],
    ["Audit ledger", "/admin/e/audit", "i-link"],
    ["Procurement", null, null],
    ["Notices", "/admin/e/notices", "i-file"],
    ["Tender builder", "/admin/e/tender-builder", "i-spark"],
    ["Corrigenda", "/admin/e/corrigenda", "i-flag"],
    ["BOQ & contracts", "/admin/e/boq", "i-layers"],
    ["Work packages", "/admin/e/work-packages", "i-box"],
    ["Catalog", "/admin/e/catalog", "i-layers"],
    ["Market", null, null],
    ["Vendors", "/admin/e/vendors", "i-users"],
    ["Registrations", "/admin/e/registrations", "i-file"],
    ["Vendor intel", "/admin/e/vendor-intel", "i-eye"],
    ["Engagements", "/admin/e/engagements", "i-chat"],
    ["Money & compliance", null, null],
    ["Bidding ops", "/admin/e/bidding", "i-gavel"],
    ["Escrow / EMD", "/admin/e/escrow", "i-coin"],
    ["Billing", "/admin/e/billing", "i-file"],
    ["Evaluation", "/admin/e/evaluation", "i-check"],
    ["L1 comparison", "/admin/e/l1-award", "i-chart"],
    ["Awards", "/admin/e/awards", "i-flag"],
    ["Reverse auctions", "/admin/e/auctions", "i-gavel"],
    ["DocuSign", "/admin/e/docusign", "i-sign"],
    ["Permissions", "/admin/e/permissions", "i-lock"],
    ["Masters", "/admin/e/masters", "i-layers"],
    ["Events", null, null],
    ["Events & alerts", "/admin/e/events", "i-clock"],
    ["Stakeholder reports", "/admin/e/stakeholder-reports", "i-chart"],
  ];
  return (
    <div className="pmc-adm">
      <aside className="pmc-side" aria-label="Admin">
        <div className="pmc-side__brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Admin console</span></div>
        {items.map(([label, href, icon]) => href ? (
          <a key={label} href={href} className="pmc-side__item" aria-current={active === label ? "page" : undefined} data-testid={`side-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
            <svg className="pmc-ico" aria-hidden="true"><use href={`#${icon}`} /></svg>{label}
          </a>
        ) : (
          <div key={label} className="pmc-side__group">{label}</div>
        ))}
      </aside>
      <div>
        <header className="pmc-atop">
          <div className="crumb">{crumb}</div>
          <label className="pmc-search"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Search tenders, bids, vendors, ledger events…" data-testid="shell-search-input" /><span className="pmc-kbd">Ctrl K</span></label>
          <div className="pmc-atop__r">
            <button className="pmc-btn pmc-btn--secondary" data-help-open="" data-testid="shell-help-btn"><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> Help</button>
            <button className="pmc-ib pmc-bell" aria-label="Alerts" data-testid="shell-bell-btn"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg></button>
            <AdminAvatarMenu />
          </div>
        </header>
        <main className="pmc-amain">{children}</main>
      </div>
    </div>
  );
}
