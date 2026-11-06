/**
 * Shared Option-E admin sidebar. Single source of truth for the admin left
 * nav so every page shows the same items in the same order.
 *
 * v52cf — the `active` prop was previously the ONLY way a page highlighted
 * its menu item, but half the pages forgot to pass it (Billing, Escrow/EMD,
 * Evaluation, Audit…). The active row was also a subtle brass-stripe that
 * users said they couldn't see. Now the active item is auto-detected from
 * `window.location.pathname` and rendered as a solid primary pill with bold
 * white text, so you can always tell where you are.
 */
export default function AdminSideNavE({ active }) {
  const path = typeof window !== "undefined" ? window.location.pathname : "";
  const items = [
    ["Overview", null, null],
    ["Dashboard", "/admin/e/dashboard", "i-home"],
    ["Audit ledger", "/admin/e/audit", "i-link"],
    ["Procurement", null, null],
    ["Notices", "/admin/e/notices", "i-file"],
    ["Taxonomy backfill", "/admin/e/taxonomy-backfill", "i-tag"],
    ["Tender builder", "/admin/e/tender-builder", "i-spark"],
    ["Criteria master", "/admin/e/criteria-master", "i-check"],
    ["Corrigenda", "/admin/e/corrigenda", "i-flag"],
    ["Bid challenges", "/admin/e/challenges", "i-flag"],
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
    ["Marketing", "/admin/e/marketing", "i-mail"],
    ["Partners", "/admin/e/partners", "i-user"],
    ["Growth", "/admin/e/growth", "i-chart"],
    ["Money & compliance", null, null],
    ["Bidding ops", "/admin/e/bidding", "i-gavel"],
    ["Escrow / EMD", "/admin/e/escrow", "i-coin"],
    ["Escrow institutions", "/admin/e/escrow-institutions", "i-shield"],
    ["Billing", "/admin/e/billing", "i-file"],
    ["Evaluation", "/admin/e/evaluation", "i-check"],
    ["L1 comparison", "/admin/e/l1-award", "i-chart"],
    ["Awards", "/admin/e/awards", "i-flag"],
    ["Awarded auctions", "/admin/e/awarded-auctions", "i-flag"],
    ["Reverse auctions", "/admin/e/auctions", "i-gavel"],
    ["DocuSign", "/admin/e/docusign", "i-sign"],
    ["Permissions", "/admin/e/permissions", "i-lock"],
    ["Governance & integrity", "/admin/e/governance", "i-shield"],
    ["Tender review", "/admin/e/tender-review", "i-gavel"],
    ["Masters", "/admin/e/masters", "i-layers"],
    ["Suggested banks", "/admin/e/suggested-banks", "i-layers"],
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
             className={"pmc-side__item" + (
               // v52cf — treat the prop as a hard override, but auto-match
               // by pathname so pages that forgot the prop still highlight.
               (active ? active === label : href === path) ? " pmc-side__item--active" : ""
             )}
             aria-current={(active ? active === label : href === path) ? "page" : undefined}
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
