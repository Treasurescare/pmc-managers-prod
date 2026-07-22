import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import DashboardLayout from "@/components/app/DashboardLayout";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Users, FileStack, Gavel, ShieldCheck, ArrowRight } from "lucide-react";

export default function AdminDashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  useEffect(() => { api.get("/admin/stats").then(({ data }) => setStats(data)).catch(() => {}); }, []);

  return (
    <DashboardLayout title={`PMC Global Board`} subtitle={`Signed in as ${user?.name} · Administrator`}>
      <div className="grid md:grid-cols-3 lg:grid-cols-6 gap-0 border-t border-l">
        <Stat testid="stat-users" icon={<Users className="h-4 w-4" />} label="Users" value={stats?.users ?? "—"} />
        <Stat testid="stat-vendors-pending" icon={<ShieldCheck className="h-4 w-4" />} label="Vendors pending" value={stats?.vendors_pending ?? "—"} />
        <Stat testid="stat-vendors-approved" icon={<ShieldCheck className="h-4 w-4" />} label="Vendors approved" value={stats?.vendors_approved ?? "—"} />
        <Stat testid="stat-tenders-open" icon={<FileStack className="h-4 w-4" />} label="Open tenders" value={stats?.tenders_open ?? "—"} />
        <Stat testid="stat-tenders-total" icon={<FileStack className="h-4 w-4" />} label="Total tenders" value={stats?.tenders_total ?? "—"} />
        <Stat testid="stat-bids-total" icon={<Gavel className="h-4 w-4" />} label="Total bids" value={stats?.bids_total ?? "—"} />
      </div>

      <div className="mt-10 grid md:grid-cols-2 gap-6">
        <Panel to="/admin/vendors" label="Review vendor applications" body="Approve or reject vendor KYC to open bidding rights." testid="panel-review-vendors" />
        <Panel to="/tenders" label="Browse all tenders" body="See every tender across the platform in one board." testid="panel-all-tenders" />
      </div>
    </DashboardLayout>
  );
}

function Stat({ label, value, icon, testid }) {
  return (
    <div data-testid={testid} className="p-6 border-r border-b bg-white">
      <div className="pmc-label flex items-center gap-2">{icon}{label}</div>
      <div className="mt-4 text-4xl font-serif tracking-tight">{value}</div>
    </div>
  );
}

function Panel({ to, label, body, testid }) {
  return (
    <Link data-testid={testid} to={to} className="border p-6 bg-white hover:pmc-hard-shadow-primary transition-shadow group block">
      <div className="pmc-label">Action</div>
      <div className="font-serif text-2xl mt-2">{label}</div>
      <p className="text-sm text-muted-foreground mt-2 mb-6">{body}</p>
      <div className="inline-flex items-center gap-2 text-sm text-primary">
        Open <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
      </div>
    </Link>
  );
}
