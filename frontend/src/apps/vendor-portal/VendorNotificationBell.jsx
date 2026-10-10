import { useEffect, useState } from "react";
import { toast } from "sonner";
import { vendorNotifyApi, showApiError } from "@/lib/api";

const stripHtml = (s) => (s || "").replace(/<br\s*\/?>/gi, "\n").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();

/**
 * v47e — in-app notification bell for the vendor portal.
 * Polls every 20s; shows bid transitions, EMD confirmations and sign-in alerts.
 */
export default function VendorNotificationBell() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);

  const refresh = async () => {
    try { setItems(await vendorNotifyApi.list()); }
    catch (err) {
      if (process.env.NODE_ENV !== "production") console.debug("vendor notifications poll failed:", err?.response?.status);
    }
  };
  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 20000);
    return () => clearInterval(t);
  }, []);

  const unread = items.filter((n) => !n.read).length;

  const markAll = async () => {
    try { await vendorNotifyApi.markAllRead(); toast.success("All read"); refresh(); }
    catch (e) { showApiError(e); }
  };
  const markOne = async (id) => {
    try { await vendorNotifyApi.markRead(id); refresh(); }
    catch (e) { showApiError(e); }
  };

  return (
    <div className="relative" data-testid="vendor-notification-bell">
      <button onClick={() => setOpen(!open)}
        className="relative px-3 py-1.5 border text-xs uppercase tracking-widest"
        data-testid="vendor-notif-toggle">
        Alerts {unread > 0 && <span className="ml-1 inline-flex items-center justify-center bg-red-600 text-white rounded-full h-4 min-w-[16px] px-1 text-[10px]">{unread}</span>}
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-96 bg-white border shadow-lg z-50 max-h-[60vh] overflow-auto"
          data-testid="vendor-notif-panel">
          <div className="flex justify-between items-center p-3 border-b bg-slate-50">
            <div className="text-sm font-semibold">Notifications</div>
            <button onClick={markAll} className="text-xs text-blue-600 hover:underline"
              data-testid="vendor-notif-mark-all">Mark all read</button>
          </div>
          {items.length === 0 && <div className="p-6 text-sm text-slate-500 text-center">All clear</div>}
          {items.map((n) => {
            // v52bp — corrigendum alerts carry a deep link to the one-page
            // diff PDF (set by backend `publish_corrigendum`). Render an
            // "Open PDF" button so bidders can preview the diff in a new tab.
            const isCorr = n.related_type === "corrigendum" && n.related_url;
            return (
            <div key={n.id} className={`p-3 border-b text-sm ${n.read ? "opacity-60" : "bg-blue-50/30"}`}
              data-testid={`vendor-notif-${n.id}`}>
              <div className="font-semibold text-xs">{n.subject}</div>
              <div className="text-xs text-slate-500 mt-1 whitespace-pre-line">{stripHtml(n.body)}</div>
              <div className="mt-2 flex items-center gap-2 flex-wrap">
                {isCorr && (
                  <a href={n.related_url} target="_blank" rel="noreferrer"
                     onClick={() => markOne(n.id)}
                     data-testid={`vendor-notif-pdf-${n.id}`}
                     className="text-[10px] uppercase tracking-widest px-2 py-1 border border-brand-navy/30 text-brand-navy hover:bg-brand-navy hover:text-white">
                    📄 Open PDF
                  </a>
                )}
                {isCorr && n.related_notice_ref && (
                  <a href={`/notices/${n.related_notice_ref}`}
                     onClick={() => markOne(n.id)}
                     data-testid={`vendor-notif-notice-${n.id}`}
                     className="text-[10px] uppercase tracking-widest px-2 py-1 border border-brand-navy/20 text-brand-navy/80 hover:border-brand-navy">
                    View notice
                  </a>
                )}
              </div>
              <div className="text-[10px] text-slate-400 mt-1">
                {new Date(n.created_at).toLocaleString()}
                {!n.read && (
                  <button onClick={() => markOne(n.id)}
                    className="ml-2 text-blue-600 hover:underline"
                    data-testid={`vendor-notif-read-${n.id}`}>mark read</button>
                )}
              </div>
            </div>
          );})}
        </div>
      )}
    </div>
  );
}
