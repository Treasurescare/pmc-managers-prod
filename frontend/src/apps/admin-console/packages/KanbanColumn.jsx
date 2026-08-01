import PackageCard from "./PackageCard";

export default function KanbanColumn({ column, items, onDragOver, onDrop, onDragStart, fmt }) {
  return (
    <div
      onDragOver={onDragOver}
      onDrop={(e) => onDrop(e, column.code)}
      data-testid={`pkg-col-${column.code}`}
      className="border border-brand-navy/10 bg-white/60 min-h-[280px]"
    >
      <div className="px-3 py-2 bg-brand-navy text-white flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-widest font-semibold">{column.label}</span>
        <span className="text-[10px] font-mono tabular-nums text-white/70">{items.length}</span>
      </div>
      <div className="p-2 space-y-2">
        {items.length === 0 && (
          <div className="text-[11px] text-brand-navy/40 text-center py-6 border border-dashed border-brand-navy/10">Drop here</div>
        )}
        {items.map((p) => (<PackageCard key={p.id} pkg={p} onDragStart={onDragStart} fmt={fmt} />))}
      </div>
    </div>
  );
}
