import { useState } from "react";

export default function PackageCard({ pkg, onDragStart, fmt }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <div
        draggable
        onDragStart={(e) => onDragStart(e, pkg)}
        onClick={() => setOpen(true)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setOpen(true); } }}
        data-testid={`pkg-card-${pkg.package_ref}`}
        className="border border-brand-navy/15 bg-white p-3 cursor-pointer active:cursor-grabbing hover:border-brand-navy-soft/60 hover:shadow-sm transition-all"
      >
        <div className="text-[9px] font-mono uppercase tracking-widest text-brand-navy-soft">{pkg.package_ref}</div>
        <div className="text-[13px] font-semibold text-brand-navy mt-1 leading-tight">{pkg.title}</div>
        <div className="text-[11px] text-brand-navy/60 mt-1">{pkg.category}</div>
        <div className="flex items-center justify-between mt-2 text-[10px] font-mono">
          <span className="text-brand-navy/70">{fmt(pkg.value, pkg.currency)}</span>
          {pkg.float_target_date && <span className="text-brand-navy/50">{pkg.float_target_date.slice(0, 10)}</span>}
        </div>
      </div>
      {open && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-start justify-center p-6 overflow-auto"
             onClick={() => setOpen(false)}
             data-testid={`pkg-detail-modal-${pkg.package_ref}`}>
          <div className="bg-white max-w-2xl w-full mt-16 p-8 shadow-xl border border-brand-navy/20"
               onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-xs font-mono uppercase tracking-widest text-brand-navy-soft">{pkg.package_ref}</div>
                <h2 className="font-display text-2xl text-brand-navy mt-1">{pkg.title}</h2>
              </div>
              <button onClick={() => setOpen(false)} data-testid={`pkg-detail-close-${pkg.package_ref}`}
                      className="text-brand-navy/60 hover:text-brand-navy text-xl leading-none">✕</button>
            </div>
            <dl className="mt-6 grid grid-cols-2 gap-x-6 gap-y-4 text-sm">
              <div><dt className="pmc-label">Status</dt><dd className="mt-1 text-brand-navy">{pkg.status || "—"}</dd></div>
              <div><dt className="pmc-label">Category</dt><dd className="mt-1 text-brand-navy">{pkg.category || "—"}</dd></div>
              <div><dt className="pmc-label">Estimated value</dt><dd className="mt-1 text-brand-navy font-mono">{fmt(pkg.value, pkg.currency)}</dd></div>
              <div><dt className="pmc-label">Float target</dt><dd className="mt-1 text-brand-navy font-mono">{pkg.float_target_date ? pkg.float_target_date.slice(0, 10) : "—"}</dd></div>
              <div><dt className="pmc-label">Owner</dt><dd className="mt-1 text-brand-navy">{pkg.owner_email || pkg.created_by || "—"}</dd></div>
              <div><dt className="pmc-label">Notice ref</dt><dd className="mt-1 text-brand-navy font-mono">{pkg.notice_ref || "Not yet floated"}</dd></div>
            </dl>
            {pkg.description && (
              <div className="mt-6">
                <div className="pmc-label">Description</div>
                <p className="mt-2 text-brand-navy/85 whitespace-pre-wrap text-sm leading-6">{pkg.description}</p>
              </div>
            )}
            {pkg.milestones && Array.isArray(pkg.milestones) && pkg.milestones.length > 0 && (
              <div className="mt-6">
                <div className="pmc-label">Milestones</div>
                <ul className="mt-2 space-y-1 text-sm">
                  {pkg.milestones.map((m, i) => (
                    <li key={i} className="text-brand-navy/85">
                      <span className="font-mono text-xs text-brand-navy/60 mr-2">
                        {m.due_date ? m.due_date.slice(0, 10) : ""}
                      </span>
                      {m.title || m.description || "Milestone"}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
