import { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { Radio, ChevronRight, ChevronLeft, RefreshCw } from "lucide-react";
import api from "@/lib/api";

function timeLeft(iso) {
  if (!iso) return "—";
  const diff = new Date(iso).getTime() - Date.now();
  if (diff <= 0) return "Closed";
  const d = Math.floor(diff / 86400000);
  const h = Math.floor((diff % 86400000) / 3600000);
  const m = Math.floor((diff % 3600000) / 60000);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function timeAgo(iso) {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

export default function TenderFeed({ collapsed, onToggle }) {
  const [items, setItems] = useState([]);
  const [refreshedAt, setRefreshedAt] = useState(null);
  const [loading, setLoading] = useState(false);
  const [tick, setTick] = useState(0);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/feed/tenders?limit=25");
      setItems(data);
      setRefreshedAt(new Date());
    } catch {}
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  // Poll every 15 seconds
  useEffect(() => {
    const iv = setInterval(load, 15000);
    return () => clearInterval(iv);
  }, []);

  // Re-render every 30s so countdowns update
  useEffect(() => {
    const iv = setInterval(() => setTick((v) => v + 1), 30000);
    return () => clearInterval(iv);
  }, []);

  // Detect newly added items since last render
  const newestId = items[0]?.id;
  const [seenTopId, setSeenTopId] = useState(null);
  useEffect(() => {
    if (newestId && seenTopId === null) setSeenTopId(newestId);
  }, [newestId, seenTopId]);
  const hasNew = newestId && seenTopId && newestId !== seenTopId;

  if (collapsed) {
    return (
      <button
        data-testid="tender-feed-expand"
        onClick={onToggle}
        className="w-10 border-l bg-white flex flex-col items-center py-4 gap-3 hover:bg-muted/50 transition-colors"
        aria-label="Expand tender feed"
      >
        <ChevronLeft className="h-4 w-4 text-muted-foreground" />
        <span className="rotate-180 pmc-label" style={{ writingMode: "vertical-rl" }}>Live Tender Feed</span>
        {hasNew && <span className="h-2 w-2 rounded-full bg-primary animate-pulse" aria-label="New tender" />}
      </button>
    );
  }

  return (
    <aside data-testid="tender-feed" className="w-[320px] border-l bg-white flex flex-col h-full">
      <div className="border-b p-4 flex items-center gap-3">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
        </span>
        <div className="flex-1 min-w-0">
          <div className="pmc-label">Live board</div>
          <div className="font-serif text-lg leading-tight">Tender feed</div>
        </div>
        <button data-testid="tender-feed-refresh" onClick={load} className="text-muted-foreground hover:text-foreground" aria-label="Refresh">
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
        </button>
        <button data-testid="tender-feed-collapse" onClick={onToggle} className="text-muted-foreground hover:text-foreground" aria-label="Collapse">
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>

      <div className="px-4 py-2 border-b bg-muted/20 text-[11px] text-muted-foreground flex items-center justify-between">
        <span data-testid="tender-feed-count">{items.length} shown · auto-refreshes</span>
        {refreshedAt && <span className="font-mono">updated {timeAgo(refreshedAt.toISOString())}</span>}
      </div>

      <div className="flex-1 overflow-y-auto" data-testid="tender-feed-list">
        {items.length === 0 && !loading && (
          <div className="p-6 text-center text-sm text-muted-foreground">
            <Radio className="mx-auto h-6 w-6 mb-3 opacity-40" />
            No open tenders on the board yet.
          </div>
        )}
        {items.map((t, idx) => {
          const isNew = idx === 0 && hasNew;
          const dt = (t.document_type || "tender").toUpperCase();
          return (
            <Link
              to={`/tenders/${t.id}`}
              key={t.id + tick}
              onClick={() => setSeenTopId(newestId)}
              data-testid={`feed-item-${t.id}`}
              className={`block border-b px-4 py-3 hover:bg-primary/5 transition-colors ${isNew ? "bg-primary/10 border-l-2 border-l-primary" : ""}`}
            >
              <div className="flex items-center gap-2">
                <span className={`text-[10px] font-semibold tracking-widest px-1.5 py-0.5 border ${
                  dt === "RFP" ? "border-primary text-primary" : dt === "RFQ" ? "border-warning text-warning" : "border-foreground text-foreground"
                }`}>{dt}</span>
                {t.status === "awarded" && <span className="text-[10px] font-semibold tracking-widest px-1.5 py-0.5 bg-success text-white">AWARDED</span>}
                {isNew && <span className="text-[10px] font-semibold tracking-widest px-1.5 py-0.5 bg-primary text-white">NEW</span>}
              </div>
              <div className="font-serif text-[15px] leading-tight mt-2 line-clamp-2">{t.title}</div>
              <div className="text-[11px] text-muted-foreground mt-1 truncate">{t.category}</div>
              {t.description && (
                <p className="text-xs text-muted-foreground mt-2 line-clamp-2 leading-relaxed">{t.description}</p>
              )}
              <div className="flex items-center justify-between mt-3 text-[11px] font-mono">
                <span>{t.budget_amount ? `${t.budget_currency} ${Number(t.budget_amount).toLocaleString()}` : "—"}</span>
                <span className={new Date(t.submission_deadline) - Date.now() < 86400000 ? "text-destructive" : "text-muted-foreground"}>
                  {timeLeft(t.submission_deadline)}
                </span>
              </div>
            </Link>
          );
        })}
      </div>
    </aside>
  );
}
