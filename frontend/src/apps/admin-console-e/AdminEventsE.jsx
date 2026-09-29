import { useEffect, useState } from "react";
import { toast } from "sonner";
import { notifyApi, showApiError } from "@/lib/api";
import AdminEShell from "./AdminEShell";

const LEVEL_CLASS = { critical: "pmc-pill--danger", warning: "pmc-pill--warning", info: "pmc-pill--info", success: "pmc-pill--success", ok: "pmc-pill--success" };

function levelOf(n) {
  const t = `${n.level || ""} ${n.title || ""}`.toLowerCase();
  if (t.includes("critical") || t.includes("fail") || t.includes("expir")) return "critical";
  if (t.includes("warn") || t.includes("deadline")) return "warning";
  if (t.includes("pass") || t.includes("success") || t.includes("verified")) return "ok";
  return "info";
}

const DEFAULT_RULES = {
  low_bids: true, guarantee_expiring: true, milestone_late: true,
  unsealing_window: true, failed_signins: true,
};

export default function AdminEventsE() {
  const [items, setItems] = useState(null);
  const [rules, setRules] = useState(() => {
    try { return JSON.parse(localStorage.getItem("pmc_alert_rules")) || DEFAULT_RULES; } catch { return DEFAULT_RULES; }
  });

  useEffect(() => {
    notifyApi.list().then((d) => setItems(Array.isArray(d) ? d : (d.items || []))).catch((e) => { showApiError(e); setItems([]); });
  }, []);

  const toggleRule = (k) => {
    const next = { ...rules, [k]: !rules[k] };
    setRules(next);
    localStorage.setItem("pmc_alert_rules", JSON.stringify(next));
    toast.success(next[k] ? "Rule enabled" : "Rule disabled");
  };

  const ack = async (n) => {
    try {
      await notifyApi.markRead(n.id);
      setItems((prev) => prev.map((x) => (x.id === n.id ? { ...x, is_read: true } : x)));
      toast.success("Acknowledged");
    } catch (e) { showApiError(e); }
  };

  const unread = (items || []).filter((n) => !n.is_read).length;
  const RULE_LABELS = [
    ["low_bids", "Deadline in 48 h with fewer than 3 bids"],
    ["guarantee_expiring", "Guarantee expiring within 30 days"],
    ["milestone_late", "Milestone late"],
    ["unsealing_window", "Unsealing within 2 h of deadline"],
    ["failed_signins", "Failed sign-in attempts (5+)"],
  ];

  return (
    <div data-testid="admin-events-e" data-pmc-e-page="admin-events-e">
      <AdminEShell active="Events & alerts" crumb={<>Events / <b>Events &amp; alerts</b></>}>
        <div style={{ padding: "28px 32px" }}>
          <div className="ah" style={{ marginBottom: "20px" }}>
            <div><div className="pmc-eyebrow">Events</div><h1 style={{ fontFamily: "var(--font-display)", fontSize: "32px", margin: "4px 0 0" }}>Events &amp; alerts</h1></div>
            <span className="pmc-pill pmc-pill--warning" data-testid="events-unread-pill">{unread} unread</span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) 340px", gap: "24px", alignItems: "start" }}>
            <section className="pmc-panel">
              <table className="pmc-table" data-testid="events-table">
                <thead><tr><th>Level</th><th>Event</th><th>When</th><th></th></tr></thead>
                <tbody>
                  {items === null && <tr><td colSpan={4} style={{ padding: "24px", textAlign: "center", color: "var(--ink-muted)" }}>Loading…</td></tr>}
                  {items !== null && items.length === 0 && <tr><td colSpan={4} style={{ padding: "24px", textAlign: "center", color: "var(--ink-muted)" }}>No events yet. New alerts land here in real time.</td></tr>}
                  {(items || []).map((n) => {
                    const lvl = levelOf(n);
                    let when = "—";
                    try { when = new Date(n.created_at).toLocaleString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }); } catch {}
                    return (
                      <tr key={n.id} data-testid={`event-row-${n.id}`} style={n.is_read ? { opacity: 0.55 } : undefined}>
                        <td><span className={`pmc-pill ${LEVEL_CLASS[lvl]}`}>{lvl === "ok" ? "OK" : lvl[0].toUpperCase() + lvl.slice(1)}</span></td>
                        <td><div style={{ fontWeight: 600 }}>{n.title || n.event_type || "Event"}</div><div className="pmc-muted" style={{ fontSize: "12px" }}>{n.body || n.message || ""}</div></td>
                        <td style={{ whiteSpace: "nowrap" }}>{when}</td>
                        <td>{!n.is_read && <button className="pmc-btn pmc-btn--secondary pmc-btn--sm" data-testid={`event-ack-${n.id}`} onClick={() => ack(n)}>Acknowledge</button>}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </section>
            <aside className="pmc-panel" style={{ position: "sticky", top: "88px" }}>
              <div className="pmc-panel__head"><h2 className="pmc-panel__title">Alert rules</h2></div>
              <div className="pmc-panel__body" style={{ display: "grid", gap: "12px" }}>
                {RULE_LABELS.map(([k, label]) => (
                  <label key={k} className="pmc-check" style={{ justifyContent: "space-between", cursor: "pointer" }} data-testid={`rule-${k}`}>
                    <span>{label}</span>
                    <input type="checkbox" checked={!!rules[k]} onChange={() => toggleRule(k)} />
                  </label>
                ))}
                <div className="pmc-muted" style={{ fontSize: "12px" }}>Rule preferences save to this browser.</div>
              </div>
            </aside>
          </div>
        </div>
      </AdminEShell>
    </div>
  );
}
