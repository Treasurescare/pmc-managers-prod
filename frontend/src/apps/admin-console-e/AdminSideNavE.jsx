/**
 * Shared Option-E admin sidebar. Single source of truth for the admin left
 * nav so every page shows the same items in the same order.
 *
 * Previously six pages hard-coded their own aside HTML with a stale/short
 * item list (missing Masters, Escrow institutions, Vendor requests,
 * Profile changes, Reverse auctions). Navigating between those pages and
 * AdminEShell-wrapped pages made the sidebar flip between the short list
 * and the full list, which is what the user saw as "menus not showing on
 * the first attempt / inconsistent Market section".
 */
export default function AdminSideNavE({ active }) {
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
    ["Vendor requests", "/admin/e/vendor-requests", "i-tag"],
    ["Profile changes", "/admin/e/profile-changes", "i-settings"],
    ["Money & compliance", null, null],
    ["Bidding ops", "/admin/e/bidding", "i-gavel"],
    ["Escrow / EMD", "/admin/e/escrow", "i-coin"],
    ["Escrow institutions", "/admin/e/escrow-institutions", "i-shield"],
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
    <aside className="pmc-side" aria-label="Admin">
      <div className="pmc-side__brand">
        <span className="pmc-brand__n">PMC Managers</span>
        <span className="pmc-brand__s">Admin console</span>
      </div>
      {items.map(([label, href, icon]) =>
        href ? (
          <a key={label} href={href}
             className="pmc-side__item"
             aria-current={active === label ? "page" : undefined}
             data-testid={`side-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
            <svg className="pmc-ico" aria-hidden="true"><use href={`#${icon}`} /></svg>
            {label}
          </a>
        ) : (
          <div key={label} className="pmc-side__group">{label}</div>
        )
      )}
    </aside>
  );
}
