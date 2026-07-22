import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import DashboardLayout from "@/components/app/DashboardLayout";
import api from "@/lib/api";
import StatusBadge from "@/components/app/StatusBadge";

export default function MyBids() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api.get("/bids").then(({ data }) => setRows(data)).catch(() => {}); }, []);

  return (
    <DashboardLayout title="My bids" subtitle="Every proposal you've submitted across the board.">
      {rows.length === 0 ? (
        <div className="border p-10 text-center text-sm text-muted-foreground">
          No bids yet. Browse <Link className="text-primary underline underline-offset-4" to="/tenders">open tenders</Link> to submit one.
        </div>
      ) : (
        <div className="border overflow-x-auto">
          <table className="w-full text-sm pmc-table" data-testid="my-bids-table">
            <thead>
              <tr className="border-b bg-muted/30">
                <Th>Bid ID</Th><Th>Tender</Th><Th>Price</Th><Th>Delivery</Th><Th>Submitted</Th><Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {rows.map((b) => (
                <tr key={b.id} className="border-b hover:bg-muted/40 transition-colors">
                  <Td className="font-mono">#{b.id.slice(-6).toUpperCase()}</Td>
                  <Td><Link className="text-primary underline underline-offset-4" to={`/tenders/${b.tender_id}`}>#{b.tender_id.slice(-6).toUpperCase()}</Link></Td>
                  <Td className="font-mono">{b.price_amount != null ? `${b.price_currency} ${b.price_amount.toLocaleString()}` : "SEALED"}</Td>
                  <Td className="font-mono">{b.delivery_days != null ? `${b.delivery_days}d` : "—"}</Td>
                  <Td className="font-mono text-xs">{new Date(b.created_at).toLocaleString()}</Td>
                  <Td><StatusBadge status={b.status} /></Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </DashboardLayout>
  );
}

function Th({ children }) { return <th className="text-left px-4 py-3 pmc-label border-b">{children}</th>; }
function Td({ children, className = "" }) { return <td className={`px-4 py-3 ${className}`}>{children}</td>; }
