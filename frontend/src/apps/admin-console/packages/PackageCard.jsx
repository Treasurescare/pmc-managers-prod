export default function PackageCard({ pkg, onDragStart, fmt }) {
  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, pkg)}
      data-testid={`pkg-card-${pkg.package_ref}`}
      className="border border-brand-navy/15 bg-white p-3 cursor-grab active:cursor-grabbing hover:border-brand-navy-soft/60 hover:shadow-sm transition-all"
    >
      <div className="text-[9px] font-mono uppercase tracking-widest text-brand-navy-soft">{pkg.package_ref}</div>
      <div className="text-[13px] font-semibold text-brand-navy mt-1 leading-tight">{pkg.title}</div>
      <div className="text-[11px] text-brand-navy/60 mt-1">{pkg.category}</div>
      <div className="flex items-center justify-between mt-2 text-[10px] font-mono">
        <span className="text-brand-navy/70">{fmt(pkg.value, pkg.currency)}</span>
        {pkg.float_target_date && <span className="text-brand-navy/50">{pkg.float_target_date.slice(0, 10)}</span>}
      </div>
    </div>
  );
}
