import { useEffect, useState } from "react";
import { notifyApi, formatApiError } from "@/lib/api";
import { toast } from "sonner";

export default function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);

  const refresh = async () => {
    try { setItems(await notifyApi.list()); } catch { /* silent */ }
  };
  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 20000); // poll every 20s
    return () => clearInterval(t);
  }, []);

  const unread = items.filter((n) => !n.read).length;

  const markAll = async () => {
    try { await notifyApi.markAllRead(); toast.success("All read"); refresh(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const markOne = async (id) => {
    try { await notifyApi.markRead(id); refresh(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div className="relative" data-testid="notification-bell">
      <button onClick={() => setOpen(!open)}
        className="relative px-3 py-1.5 border text-xs uppercase tracking-widest"
        data-testid="notif-toggle">
        Alerts {unread > 0 && <span className="ml-1 inline-flex items-center justify-center bg-red-600 text-white rounded-full h-4 min-w-[16px] px-1 text-[10px]">{unread}</span>}
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-96 bg-white border shadow-lg z-50 max-h-[60vh] overflow-auto"
          data-testid="notif-panel">
          <div className="flex justify-between items-center p-3 border-b bg-slate-50">
            <div className="text-sm font-semibold">Notifications</div>
            <button onClick={markAll} className="text-xs text-blue-600 hover:underline"
              data-testid="notif-mark-all">Mark all read</button>
          </div>
          {items.length === 0 && <div className="p-6 text-sm text-slate-500 text-center">All clear</div>}
          {items.map((n) => (
            <div key={n.id} className={`p-3 border-b text-sm ${n.read ? "opacity-60" : "bg-blue-50/30"}`}
              data-testid={`notif-${n.id}`}>
              <div className="font-semibold text-xs">{n.subject}</div>
              <div className="text-xs text-slate-500 mt-1" dangerouslySetInnerHTML={{ __html: n.body }} />
              <div className="text-[10px] text-slate-400 mt-1">
                {new Date(n.created_at).toLocaleString()}
                {!n.read && (
                  <button onClick={() => markOne(n.id)}
                    className="ml-2 text-blue-600 hover:underline">mark read</button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
