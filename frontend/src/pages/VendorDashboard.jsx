import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import DashboardLayout from "@/components/app/DashboardLayout";
import api from "@/lib/api";
import StatusBadge from "@/components/app/StatusBadge";
import { useAuth } from "@/context/AuthContext";
import { ArrowRight, FileStack, Gavel, Bell } from "lucide-react";

export default function VendorDashboard() {
  const { user } = useAuth();
  const [tenders, setTenders] = useState([]);
  const [bids, setBids] = useState([]);
  const [profile, setProfile] = useState(null);

  useEffect(() => {
    api.get("/tenders").then(({ data }) => setTenders(data.filter((t) => t.status === "open").slice(0, 5))).catch(() => {});
    api.get("/bids").then(({ data }) => setBids(data.slice(0, 5))).catch(() => {});
    api.get("/vendor/profile").then(({ data }) => setProfile(data)).catch(() => {});
  }, []);

  const status = profile?.vendor_status || "pending";
  const profileComplete = !!profile?.vendor_profile;

  return (
    <DashboardLayout
      title={`Welcome, ${user?.name}`}
      subtitle="Bidder workspace. Track your KYC status, browse tenders, and manage submitted bids."
      actions={<StatusBadge status={status} testid="vendor-status-badge" />}
    >
      {status !== "approved" && (
        <div data-testid="vendor-approval-banner" className="mb-8 border-l-4 border-warning bg-warning/10 p-5">
          <div className="pmc-label text-warning">Action required</div>
          <div className="mt-2 font-serif text-2xl">Your account is {status}.</div>
          <p className="text-sm text-muted-foreground mt-2 max-w-2xl">
            {profileComplete
              ? "Compliance is reviewing your profile. You’ll be able to submit bids once approved."
              : "Complete your KYC profile to be reviewed by compliance."}
          </p>
          <Link to="/vendor/profile" className="mt-4 inline-flex items-center gap-2 text-sm bg-foreground text-white px-4 py-2">
            {profileComplete ? "Review profile" : "Complete profile"} <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      )}

      <div className="grid md:grid-cols-3 gap-0 border-t border-l">
        <MetricCard testid="metric-open-tenders" icon={<FileStack className="h-4 w-4" />} label="Open tenders" value={tenders.length} />
        <MetricCard testid="metric-my-bids" icon={<Gavel className="h-4 w-4" />} label="My bids" value={bids.length} />
        <MetricCard testid="metric-kyc-status" icon={<Bell className="h-4 w-4" />} label="KYC status" value={status.toUpperCase()} mono />
      </div>

      <section className="mt-12">
        <div className="flex items-end justify-between mb-4">
          <div>
            <div className="pmc-label">Feed</div>
            <h2 className="font-serif text-2xl">Latest open tenders</h2>
          </div>
          <Link to="/tenders" data-testid="vendor-view-all-tenders" className="text-sm text-primary underline underline-offset-4">View all</Link>
        </div>
        <TenderRows tenders={tenders} />
      </section>

      <section className="mt-12">
        <div className="flex items-end justify-between mb-4">
          <div>
            <div className="pmc-label">Personal</div>
            <h2 className="font-serif text-2xl">Recent bids</h2>
          </div>
          <Link to="/vendor/bids" data-testid="vendor-view-all-bids" className="text-sm text-primary underline underline-offset-4">View all</Link>
        </div>
        {bids.length === 0 ? (
          <div className="border p-8 text-center text-sm text-muted-foreground">You haven't submitted any bids yet.</div>
        ) : (
          <div className="border">
            <table className="w-full text-sm pmc-table" data-testid="vendor-recent-bids-table">
              <thead>
                <tr className="border-b bg-muted/30">
                  <Th>Tender</Th><Th>Price</Th><Th>Delivery</Th><Th>Status</Th>
                </tr>
              </thead>
              <tbody>
                {bids.map((b) => (
                  <tr key={b.id} className="border-b hover:bg-muted/40 transition-colors">
                    <Td><Link className="text-primary underline underline-offset-4" to={`/tenders/${b.tender_id}`}>{b.tender_id?.slice(-8)}</Link></Td>
                    <Td className="font-mono">{b.price_currency} {b.price_amount.toLocaleString()}</Td>
                    <Td className="font-mono">{b.delivery_days}d</Td>
                    <Td><StatusBadge status={b.status} /></Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </DashboardLayout>
  );
}

function MetricCard({ label, value, icon, mono, testid }) {
  return (
    <div data-testid={testid} className="p-6 border-r border-b bg-white">
      <div className="pmc-label flex items-center gap-2">{icon}{label}</div>
      <div className={`mt-4 text-4xl ${mono ? "font-mono" : "font-serif"} tracking-tight`}>{value}</div>
    </div>
  );
}

function TenderRows({ tenders }) {
  if (tenders.length === 0) return <div className="border p-8 text-center text-sm text-muted-foreground">No open tenders yet.</div>;
  return (
    <div className="border">
      <table className="w-full text-sm pmc-table" data-testid="tenders-list-table">
        <thead>
          <tr className="border-b bg-muted/30">
            <Th>ID</Th><Th>Title</Th><Th>Category</Th><Th>Budget</Th><Th>Deadline</Th><Th></Th>
          </tr>
        </thead>
        <tbody>
          {tenders.map((t) => (
            <tr key={t.id} className="border-b hover:bg-muted/40 transition-colors">
              <Td className="font-mono text-primary">#{t.id.slice(-6).toUpperCase()}</Td>
              <Td>{t.title}</Td>
              <Td>{t.category}</Td>
              <Td className="font-mono">{t.budget_amount ? `${t.budget_currency} ${t.budget_amount.toLocaleString()}` : "—"}</Td>
              <Td className="font-mono">{new Date(t.submission_deadline).toLocaleDateString()}</Td>
              <Td>
                <Link data-testid={`tender-view-${t.id}`} to={`/tenders/${t.id}`} className="text-primary underline underline-offset-4">View</Link>
              </Td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Th({ children }) { return <th className="text-left px-4 py-3 pmc-label border-b">{children}</th>; }
function Td({ children, className = "" }) { return <td className={`px-4 py-3 ${className}`}>{children}</td>; }
