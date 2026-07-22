const MAP = {
  open: { bg: "bg-success/10", text: "text-success", border: "border-success/30", label: "OPEN" },
  closed: { bg: "bg-muted", text: "text-muted-foreground", border: "border-border", label: "CLOSED" },
  awarded: { bg: "bg-primary/10", text: "text-primary", border: "border-primary/30", label: "AWARDED" },
  pending: { bg: "bg-warning/10", text: "text-warning", border: "border-warning/30", label: "PENDING" },
  approved: { bg: "bg-success/10", text: "text-success", border: "border-success/30", label: "APPROVED" },
  rejected: { bg: "bg-destructive/10", text: "text-destructive", border: "border-destructive/30", label: "REJECTED" },
  submitted: { bg: "bg-info/10", text: "text-info", border: "border-info/30", label: "SUBMITTED" },
};

export default function StatusBadge({ status, testid }) {
  const key = (status || "").toLowerCase();
  const c = MAP[key] || { bg: "bg-muted", text: "text-muted-foreground", border: "border-border", label: (status || "-").toUpperCase() };
  return (
    <span
      data-testid={testid}
      className={`inline-flex items-center px-2 py-1 text-[10px] font-semibold tracking-widest border ${c.bg} ${c.text} ${c.border}`}
    >
      {c.label}
    </span>
  );
}
