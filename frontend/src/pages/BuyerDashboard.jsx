import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import DashboardLayout from "@/components/app/DashboardLayout";
import api from "@/lib/api";
import StatusBadge from "@/components/app/StatusBadge";
import { useAuth } from "@/context/AuthContext";
import { PlusSquare, ArrowRight, FileStack, Gavel } from "lucide-react";

export default function BuyerDashboard() {
  const { user } = useAuth();
  const [tenders, setTenders] = useState([]);
  const [bids, setBids] = useState([]);

  useEffect(() => {
    api.get("/tenders?mine=1").then(({ data }) => setTenders(data)).catch(() => {});
    api.get("/bids").then(({ data }) => setBids(data)).catch(() => {});
  }, []);

  const open = tenders.filter((t) => t.status === "open").length;
  const awarded = tenders.filter((t) => t.status === "awarded").length;

  return (
    <DashboardLayout
      title={`Welcome, ${user?.name}`}
      subtitle="Buyer workspace. Publish tenders, review bids, and award decisively."
      actions={
        <Link data-testid="buyer-create-tender-cta" to="/buyer/create" className="inline-flex items-center gap-2 bg-primary text-white px-4 py-2 text-sm hover:-translate-y-0.5 transition-transform">
          <PlusSquare className="h-4 w-4" /> New tender
        </Link>
      }
    >
      <div className="grid md:grid-cols-3 gap-0 border-t border-l">
        <Metric testid="metric-my-tenders" icon={<FileStack className="h-4 w-4" />} label="My tenders" value={tenders.length} />
        <Metric testid="metric-open" icon={<FileStack className="h-4 w-4" />} label="Open" value={open} />
        <Metric testid="metric-awarded" icon={<Gavel className="h-4 w-4" />} label="Awarded" value={awarded} />
      </div>

      <section className="mt-12">
        <div className="pmc-label">Portfolio</div>
        <h2 className="font-serif text-2xl mb-4">Your tenders</h2>
        {tenders.length === 0 ? (
          <div className="border p-8 text-center text-sm text-muted-foreground">
            You haven't posted any tenders yet.
            <div className="mt-4">
              <Link to="/buyer/create" className="inline-flex items-center gap-2 bg-foreground text-white px-4 py-2 text-sm">
                Create your first tender <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        ) : (
          <div className="border overflow-x-auto">
            <table className="w-full text-sm pmc-table" data-testid="buyer-tenders-table">
              <thead>
                <tr className="border-b bg-muted/30">
                  <Th>ID</Th><Th>Title</Th><Th>Category</Th><Th>Budget</Th><Th>Deadline</Th><Th>Status</Th><Th></Th>
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
                    <Td><StatusBadge status={t.status} /></Td>
                    <Td>
                      <Link data-testid={`buyer-view-tender-${t.id}`} to={`/tenders/${t.id}`} className="text-primary underline underline-offset-4">Review</Link>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="mt-12">
        <div className="pmc-label">Latest activity</div>
        <h2 className="font-serif text-2xl mb-4">Recent bids received</h2>
        {bids.length === 0 ? (
          <div className="border p-8 text-center text-sm text-muted-foreground">No bids received yet.</div>
        ) : (
          <div className="border">
            <table className="w-full text-sm pmc-table">
              <thead>
                <tr className="border-b bg-muted/30">
                  <Th>Vendor</Th><Th>Tender</Th><Th>Price</Th><Th>Delivery</Th><Th>Status</Th>
                </tr>
              </thead>
              <tbody>
                {bids.slice(0, 6).map((b) => (
                  <tr key={b.id} className="border-b hover:bg-muted/40">
                    <Td>{b.vendor_company || b.vendor_email}</Td>
                    <Td>
                      <Link className="text-primary underline underline-offset-4" to={`/tenders/${b.tender_id}`}>
                        #{b.tender_id.slice(-6).toUpperCase()}
                      </Link>
                    </Td>
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

function Metric({ label, value, icon, testid }) {
  return (
    <div data-testid={testid} className="p-6 border-r border-b bg-white">
      <div className="pmc-label flex items-center gap-2">{icon}{label}</div>
      <div className="mt-4 text-4xl font-serif tracking-tight">{value}</div>
    </div>
  );
}
function Th({ children }) { return <th className="text-left px-4 py-3 pmc-label border-b">{children}</th>; }
function Td({ children, className = "" }) { return <td className={`px-4 py-3 ${className}`}>{children}</td>; }
