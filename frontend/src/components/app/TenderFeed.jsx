import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { Link } from "react-router-dom";
import { Radio, ChevronRight, ChevronLeft, RefreshCw, CheckCheck, Filter as FilterIcon } from "lucide-react";
import api, { API_BASE } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

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

const FILTERS = [
  { key: "all", label: "All" },
  { key: "rfp", label: "RFP" },
  { key: "rfq", label: "RFQ" },
  { key: "tender", label: "Tender" },
  { key: "mine", label: "My country" },
  { key: "unread", label: "Unread" },
];

export default function TenderFeed({ collapsed, onToggle }) {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [refreshedAt, setRefreshedAt] = useState(null);
  const [loading, setLoading] = useState(false);
  const [tick, setTick] = useState(0);
  const [live, setLive] = useState(false);
  const [filter, setFilter] = useState(() => {
    try { return localStorage.getItem("pmc.feed.filter") || "all"; } catch { return "all"; }
  });
  const esRef = useRef(null);

  const userCountry = (user && (user.vendor_profile?.country || user.country)) || null;

  const queryParams = useMemo(() => {
    const p = new URLSearchParams({ limit: "25" });
    if (filter === "rfp" || filter === "rfq" || filter === "tender") p.set("document_type", filter);
    if (filter === "mine" && userCountry) p.set("country", userCountry);
    if (filter === "unread") p.set("unread_only", "true");
    return p.toString();
  }, [filter, userCountry]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get(`/feed/tenders?${queryParams}`);
      setItems(data);
      setRefreshedAt(new Date());
    } catch (e) { console.warn("Feed fetch failed", e); }
    setLoading(false);
  }, [queryParams]);

  // Initial + filter-driven load
  useEffect(() => { load(); }, [load]);

  // Persist filter
  useEffect(() => { try { localStorage.setItem("pmc.feed.filter", filter); } catch (e) { /* storage disabled */ } }, [filter]);

  // SSE stream for real-time push
  useEffect(() => {
    if (!user) return;
    // EventSource uses cookies from same origin — backend & frontend share the ingress
    const url = `${API_BASE}/feed/stream`;
    let es;
    try {
      es = new EventSource(url, { withCredentials: true });
    } catch (err) {
      console.warn("SSE unavailable", err);
      return;
    }
    esRef.current = es;
    es.addEventListener("connected", () => setLive(true));
    es.addEventListener("tender.created", (e) => {
      try {
        const payload = JSON.parse(e.data);
        // Client-side filter matching
        if (filter === "rfp" && payload.document_type !== "rfp") return;
        if (filter === "rfq" && payload.document_type !== "rfq") return;
        if (filter === "tender" && payload.document_type !== "tender") return;
        if (filter === "mine" && userCountry && payload.delivery_country !== userCountry) return;
        setItems((prev) => {
          if (prev.some((x) => x.id === payload.id)) return prev;
          return [{ ...payload, unread: true }, ...prev].slice(0, 30);
        });
        setRefreshedAt(new Date());
      } catch (err) { console.warn("SSE tender.created parse failed", err); }
    });
    es.addEventListener("tender.updated", (e) => {
      try {
        const payload = JSON.parse(e.data);
        setItems((prev) => prev.map((x) => x.id === payload.id ? { ...x, ...payload } : x));
      } catch (err) { console.warn("SSE tender.updated parse failed", err); }
    });
    es.onerror = () => { setLive(false); };
    return () => { setLive(false); try { es.close(); } catch (err) { /* already closed */ } };
  }, [user, filter, userCountry]);

  // Re-render every 30s so countdowns update
  useEffect(() => {
    const iv = setInterval(() => setTick((v) => v + 1), 30000);
    return () => clearInterval(iv);
  }, []);

  const unreadCount = items.filter((t) => t.unread).length;

  const markRead = async (tid) => {
    setItems((prev) => prev.map((x) => x.id === tid ? { ...x, unread: false } : x));
    try { await api.post(`/feed/mark-read/${tid}`); } catch (e) { console.warn("mark-read failed", e); }
  };

  const markAllRead = async () => {
    setItems((prev) => prev.map((x) => ({ ...x, unread: false })));
    try { await api.post("/feed/mark-all-read"); } catch (e) { console.warn("mark-all-read failed", e); }
    if (filter === "unread") load();
  };

  if (collapsed) {
    return (
      <button
        data-testid="tender-feed-expand"
        onClick={onToggle}
        className="w-10 border-l bg-white flex flex-col items-center py-4 gap-3 hover:bg-muted/50 transition-colors relative"
        aria-label="Expand tender feed"
      >
        <ChevronLeft className="h-4 w-4 text-muted-foreground" />
        <span className="rotate-180 pmc-label" style={{ writingMode: "vertical-rl" }}>Live Tender Feed</span>
        {unreadCount > 0 && (
          <span
            data-testid="feed-unread-badge-collapsed"
            className="absolute top-2 right-2 min-w-[18px] h-[18px] px-1 rounded-full bg-primary text-white text-[10px] font-bold flex items-center justify-center"
          >
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>
    );
  }

  return (
    <aside data-testid="tender-feed" className="w-[320px] border-l bg-white flex flex-col h-full">
      <div className="border-b p-4 flex items-center gap-3">
        <span className="relative flex h-2 w-2" title={live ? "Live" : "Reconnecting…"}>
          <span className={`absolute inline-flex h-full w-full rounded-full ${live ? "bg-emerald-500 animate-ping" : "bg-muted-foreground"} opacity-75`}></span>
          <span className={`relative inline-flex rounded-full h-2 w-2 ${live ? "bg-emerald-500" : "bg-muted-foreground"}`}></span>
        </span>
        <div className="flex-1 min-w-0">
          <div className="pmc-label">{live ? "Live · SSE" : "Idle"}</div>
          <div className="font-serif text-lg leading-tight">Tender feed</div>
        </div>
        {unreadCount > 0 && (
          <button
            data-testid="feed-mark-all-read"
            onClick={markAllRead}
            title="Mark all read"
            className="text-muted-foreground hover:text-foreground"
            aria-label="Mark all read"
          >
            <CheckCheck className="h-4 w-4" />
          </button>
        )}
        <button data-testid="tender-feed-refresh" onClick={load} className="text-muted-foreground hover:text-foreground" aria-label="Refresh">
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
        </button>
        <button data-testid="tender-feed-collapse" onClick={onToggle} className="text-muted-foreground hover:text-foreground" aria-label="Collapse">
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>

      <FeedFilters filter={filter} onFilter={setFilter} unreadCount={unreadCount} userCountry={userCountry} />

      <div className="px-4 py-2 border-b bg-muted/20 text-[11px] text-muted-foreground flex items-center justify-between">
        <span data-testid="tender-feed-count">{items.length} shown{unreadCount > 0 ? ` · ${unreadCount} unread` : ""}</span>
        {refreshedAt && <span className="font-mono">updated {timeAgo(refreshedAt.toISOString())}</span>}
      </div>

      <div className="flex-1 overflow-y-auto" data-testid="tender-feed-list">
        {items.length === 0 && !loading && (
          <div className="p-6 text-center text-sm text-muted-foreground">
            <Radio className="mx-auto h-6 w-6 mb-3 opacity-40" />
            {filter === "unread" ? "No unread tenders." : "No open tenders on the board yet."}
          </div>
        )}
        {items.map((t) => (
          <FeedItem key={t.id + "_" + tick} t={t} onMarkRead={markRead} />
        ))}
      </div>
    </aside>
  );
}

// ---------- Sub-components (extracted for readability) ----------
function filterBtnClass(active, disabled) {
  if (active) return "bg-foreground text-white border-foreground";
  if (disabled) return "border-muted text-muted-foreground/50 cursor-not-allowed";
  return "border-muted-foreground/30 text-muted-foreground hover:border-foreground hover:text-foreground";
}

function FeedFilters({ filter, onFilter, unreadCount, userCountry }) {
  return (
    <div className="border-b px-3 py-2 flex flex-wrap gap-1" data-testid="feed-filters">
      {FILTERS.map((f) => {
        const disabled = f.key === "mine" && !userCountry;
        const active = filter === f.key;
        const showUnreadCount = f.key === "unread" && unreadCount > 0 && !active;
        return (
          <button
            key={f.key}
            onClick={() => !disabled && onFilter(f.key)}
            disabled={disabled}
            data-testid={`feed-filter-${f.key}`}
            className={`text-[11px] tracking-widest uppercase px-2 py-1 border transition-colors ${filterBtnClass(active, disabled)}`}
          >
            {f.label}
            {showUnreadCount && <span className="ml-1 text-primary font-bold">{unreadCount}</span>}
          </button>
        );
      })}
    </div>
  );
}

function dtBadgeClass(dt) {
  if (dt === "RFP") return "border-primary text-primary";
  if (dt === "RFQ") return "border-warning text-warning";
  return "border-foreground text-foreground";
}

function timeChipClass(deadlineIso) {
  const diff = new Date(deadlineIso) - Date.now();
  if (diff <= 0) return "px-1.5 py-0.5 bg-muted text-foreground/80 font-semibold";
  if (diff < 86400000) return "px-1.5 py-0.5 bg-destructive text-white font-semibold";
  return "px-1.5 py-0.5 bg-foreground/10 text-foreground font-semibold";
}

function FeedItem({ t, onMarkRead }) {
  const dt = (t.document_type || "tender").toUpperCase();
  const handleClick = () => { if (t.unread) onMarkRead(t.id); };
  return (
    <Link
      to={`/tenders/${t.id}`}
      onClick={handleClick}
      data-testid={`feed-item-${t.id}`}
      className={`block border-b px-4 py-3 hover:bg-primary/5 transition-colors ${t.unread ? "bg-primary/[0.06] border-l-2 border-l-primary" : ""}`}
    >
      <div className="flex items-center gap-2">
        <span className={`text-[10px] font-semibold tracking-widest px-1.5 py-0.5 border ${dtBadgeClass(dt)}`}>{dt}</span>
        {t.status === "awarded" && (
          <span className="text-[10px] font-semibold tracking-widest px-1.5 py-0.5 bg-success text-white">AWARDED</span>
        )}
        {t.unread && (
          <span data-testid={`feed-unread-dot-${t.id}`} className="ml-auto h-2 w-2 rounded-full bg-primary" aria-label="Unread" />
        )}
      </div>
      <div className="font-serif text-[15px] leading-tight mt-2 line-clamp-2">{t.title}</div>
      <div className="text-[11px] text-muted-foreground mt-1 truncate">
        {t.category}{t.delivery_country ? ` · ${t.delivery_country}` : ""}
      </div>
      {t.description && (
        <p className="text-xs text-muted-foreground mt-2 line-clamp-2 leading-relaxed">{t.description}</p>
      )}
      <div className="flex items-center justify-between mt-3 text-[11px] font-mono">
        <span className="text-foreground/80">
          {t.budget_amount ? `${t.budget_currency} ${Number(t.budget_amount).toLocaleString()}` : "—"}
        </span>
        <span data-testid={`feed-time-${t.id}`} className={timeChipClass(t.submission_deadline)}>
          {timeLeft(t.submission_deadline)}
        </span>
      </div>
    </Link>
  );
}
