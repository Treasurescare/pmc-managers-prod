import { useEffect, useState } from "react";
import DashboardLayout from "@/components/app/DashboardLayout";
import api from "@/lib/api";
import { Bell, Check } from "lucide-react";
import { Link } from "react-router-dom";

export default function Notifications() {
  const [rows, setRows] = useState([]);

  const load = async () => { try { const { data } = await api.get("/notifications"); setRows(data); } catch {} };
  useEffect(() => { load(); }, []);

  const markAll = async () => { await api.post("/notifications/mark-all-read"); load(); };

  return (
    <DashboardLayout
      title="Notifications"
      subtitle="Everything that happens on your account is timestamped and stored."
      actions={
        <button data-testid="mark-all-read" onClick={markAll} className="inline-flex items-center gap-2 border border-foreground px-4 py-2 text-sm hover:bg-foreground hover:text-white transition-colors">
          <Check className="h-4 w-4" /> Mark all read
        </button>
      }
    >
      {rows.length === 0 ? (
        <div className="border p-10 text-center text-sm text-muted-foreground">
          <Bell className="mx-auto h-6 w-6 mb-3" /> You're all caught up.
        </div>
      ) : (
        <ul className="border" data-testid="notifications-list">
          {rows.map((n) => (
            <li key={n.id} className={`px-6 py-4 border-b last:border-b-0 flex gap-4 ${!n.read ? "bg-primary/5" : ""}`}>
              <div className={`mt-1 h-2 w-2 rounded-full ${!n.read ? "bg-primary" : "bg-transparent border border-border"}`} />
              <div className="flex-1 min-w-0">
                <div className="font-serif text-lg leading-snug">{n.title}</div>
                <div className="text-sm text-muted-foreground mt-1">{n.body}</div>
                <div className="text-xs text-muted-foreground/70 font-mono mt-2">{new Date(n.created_at).toLocaleString()}</div>
              </div>
              {n.link && <Link className="text-sm text-primary underline underline-offset-4 self-start" to={n.link}>Open</Link>}
            </li>
          ))}
        </ul>
      )}
    </DashboardLayout>
  );
}
