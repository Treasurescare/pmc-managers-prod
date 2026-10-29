import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import DOMPurify from "dompurify";
import { vendorMessagesApi, showApiError } from "@/lib/api";
import VendorPortalChrome from "./VendorPortalChrome";

const KIND = { category: "Category", payment: "Payment", service: "Service" };

export default function VendorMessages() {
  const [rows, setRows] = useState(null);
  const [open, setOpen] = useState(null);
  const [filter, setFilter] = useState("all");
  const load = () => vendorMessagesApi.list().then((r) => setRows(r.items || [])).catch(() => setRows([]));
  useEffect(() => { load(); }, []);
  const view = async (m) => {
    setOpen(open === m.id ? null : m.id);
    if (!m.read) { try { await vendorMessagesApi.read(m.id); setRows((rs) => rs.map((x) => x.id === m.id ? { ...x, read: true } : x)); } catch (e) { showApiError(e); } }
  };
  const readAll = async () => { try { await vendorMessagesApi.readAll(); load(); } catch (e) { showApiError(e); } };
  const shown = (rows || []).filter((m) => filter === "all" || (filter === "unread" ? !m.read : m.kind === filter));
  const unread = (rows || []).filter((m) => !m.read).length;
  return (
    <div data-testid="vendor-messages">
      <VendorPortalChrome active="/vendor/messages">
        <div className="sp-head"><div><div className="pmc-eyebrow">Inbox</div><h1>Messages from PMC</h1></div>
          {unread > 0 && <button className="pmc-btn pmc-btn--secondary" onClick={readAll} data-testid="msg-read-all">Mark all read ({unread})</button>}</div>
        <div style={{ display: "flex", gap: "6px", marginBottom: "12px", flexWrap: "wrap" }}>
          {[["all", "All"], ["unread", `Unread (${unread})`], ["category", "Category"], ["payment", "Payment"], ["service", "Service"]].map(([k, l]) => (
            <button key={k} onClick={() => setFilter(k)} data-testid={`msg-filter-${k}`}
              className={`pmc-btn pmc-btn--sm ${filter === k ? "pmc-btn--primary" : "pmc-btn--ghost"}`}>{l}</button>
          ))}
        </div>
        <section className="pmc-panel" data-testid="msg-list">
          {rows === null ? <div className="pmc-panel__body pmc-muted">Loading…</div>
            : shown.length === 0 ? <div className="pmc-panel__body pmc-muted" data-testid="msg-empty">No messages.</div>
            : shown.map((m) => (
              <div key={m.id} data-testid={`msg-row-${m.id}`} style={{ borderTop: "1px solid var(--line)" }}>
                <button onClick={() => view(m)} data-testid={`msg-open-${m.id}`}
                  style={{ width: "100%", textAlign: "left", background: m.read ? "transparent" : "rgba(183,121,31,.07)", border: 0, padding: "12px 16px", cursor: "pointer", display: "flex", flexWrap: "wrap", justifyContent: "space-between", gap: "6px 12px" }}>
                  <span><span className="pmc-pill pmc-pill--muted" style={{ marginRight: "8px" }}>{KIND[m.kind] || "Notice"}</span>
                    <b style={{ fontWeight: m.read ? 500 : 700 }}>{m.subject}</b></span>
                  <span className="pmc-muted" style={{ fontSize: "12px", whiteSpace: "nowrap" }}>{String(m.created_at || "").slice(0, 16).replace("T", " ")}</span>
                </button>
                {open === m.id && (
                  <div style={{ padding: "0 16px 14px", fontSize: "14px", lineHeight: 1.6 }} data-testid={`msg-body-${m.id}`}>
                    <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(m.body || "") }} />
                    {m.link && (m.link.startsWith("/")
                      ? <Link to={m.link} className="pmc-btn pmc-btn--primary pmc-btn--sm" data-testid={`msg-link-${m.id}`}>Open</Link>
                      : <a href={m.link} className="pmc-btn pmc-btn--primary pmc-btn--sm" data-testid={`msg-link-${m.id}`}>Open</a>)}
                  </div>
                )}
              </div>
            ))}
        </section>
      </VendorPortalChrome>
    </div>
  );
}
