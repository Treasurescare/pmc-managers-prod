/**
 * PortalSideNavE — generic Option-E dark sidebar shared by the staff and
 * escrow portals. Mirrors AdminSideNavE's markup/classes (.pmc-side) so it
 * inherits the exact same desktop-fixed / mobile-drawer responsive behaviour
 * the admin console already ships. Unlike the admin nav (href links) this one
 * drives in-page tab state via onSelect(key).
 */
export default function PortalSideNavE({ brand, items, activeKey, onSelect, testId }) {
  return (
    <aside className="pmc-side" aria-label={brand?.sub || "Navigation"} data-testid={testId}>
      <div className="pmc-side__brand">
        <span className="pmc-brand__n">{brand?.title}</span>
        {brand?.sub ? <span className="pmc-brand__s">{brand.sub}</span> : null}
      </div>
      {items.map((it, i) =>
        it.group ? (
          <div key={`g-${i}`} className="pmc-side__group">{it.label}</div>
        ) : (
          <button
            key={it.key}
            type="button"
            onClick={() => onSelect(it.key)}
            className={"pmc-side__item" + (activeKey === it.key ? " pmc-side__item--active" : "")}
            aria-current={activeKey === it.key ? "page" : undefined}
            data-testid={it.testid}
            style={{ border: "none", width: "auto", cursor: "pointer", textAlign: "left" }}
          >
            {it.icon ? <svg className="pmc-ico" aria-hidden="true"><use href={`#${it.icon}`} /></svg> : null}
            {it.label}
            {it.badge ? <span className="pmc-side__count">{it.badge}</span> : null}
          </button>
        )
      )}
    </aside>
  );
}
