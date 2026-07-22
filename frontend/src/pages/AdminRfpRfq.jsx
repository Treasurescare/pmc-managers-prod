import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import DashboardLayout from "@/components/app/DashboardLayout";
import api from "@/lib/api";
import StatusBadge from "@/components/app/StatusBadge";
import { PlusSquare, FileText, FileSpreadsheet } from "lucide-react";

export default function AdminRfpRfq() {
  const [rows, setRows] = useState([]);
  const [tab, setTab] = useState("rfp"); // rfp | rfq

  useEffect(() => {
    api.get(`/tenders?document_type=${tab}`).then(({ data }) => setRows(data)).catch(() => {});
  }, [tab]);

  return (
    <DashboardLayout
      title="RFP / RFQ Board"
      subtitle="Create and manage Requests for Proposal (RFP) and Requests for Quotation (RFQ)."
      actions={
        <div className="flex gap-2">
          <Link data-testid="admin-new-rfp" to="/admin/rfp-rfq/new?type=rfp" className="inline-flex items-center gap-2 bg-primary text-white px-4 py-2 text-sm hover:-translate-y-0.5 transition-transform">
            <PlusSquare className="h-4 w-4" /> New RFP
          </Link>
          <Link data-testid="admin-new-rfq" to="/admin/rfp-rfq/new?type=rfq" className="inline-flex items-center gap-2 bg-foreground text-white px-4 py-2 text-sm hover:-translate-y-0.5 transition-transform">
            <PlusSquare className="h-4 w-4" /> New RFQ
          </Link>
        </div>
      }
    >
      <div className="grid grid-cols-2 gap-0 border max-w-md mb-6">
        <button data-testid="tab-rfp" onClick={() => setTab("rfp")} className={`px-4 py-3 text-sm border-r inline-flex items-center justify-center gap-2 ${tab === "rfp" ? "bg-primary text-white" : "hover:bg-muted/40"}`}>
          <FileText className="h-4 w-4" /> RFP
        </button>
        <button data-testid="tab-rfq" onClick={() => setTab("rfq")} className={`px-4 py-3 text-sm inline-flex items-center justify-center gap-2 ${tab === "rfq" ? "bg-primary text-white" : "hover:bg-muted/40"}`}>
          <FileSpreadsheet className="h-4 w-4" /> RFQ
        </button>
      </div>

      <div className="border overflow-x-auto">
        <table className="w-full text-sm pmc-table" data-testid="admin-rfp-rfq-table">
          <thead>
            <tr className="border-b bg-muted/30">
              <Th>ID</Th><Th>Type</Th><Th>Title</Th><Th>Category</Th><Th>Budget</Th><Th>Deadline</Th><Th>Status</Th><Th>Publisher</Th><Th></Th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr><td colSpan={9} className="text-center text-muted-foreground py-10">No {tab.toUpperCase()} yet. Click the button above to create one.</td></tr>
            )}
            {rows.map((t) => (
              <tr key={t.id} className="border-b hover:bg-muted/40 transition-colors">
                <Td className="font-mono text-primary">#{t.id.slice(-6).toUpperCase()}</Td>
                <Td><span className="pmc-label text-primary">{t.document_type?.toUpperCase() || "TENDER"}</span></Td>
                <Td>{t.title}</Td>
                <Td>{t.category}</Td>
                <Td className="font-mono">{t.budget_amount ? `${t.budget_currency} ${t.budget_amount.toLocaleString()}` : "—"}</Td>
                <Td className="font-mono">{new Date(t.submission_deadline).toLocaleString()}</Td>
                <Td><StatusBadge status={t.status} /></Td>
                <Td className="text-muted-foreground">{t.created_by_name}</Td>
                <Td><Link data-testid={`open-doc-${t.id}`} to={`/tenders/${t.id}`} className="text-primary underline underline-offset-4">Open</Link></Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </DashboardLayout>
  );
}

function Th({ children }) { return <th className="text-left px-4 py-3 pmc-label border-b">{children}</th>; }
function Td({ children, className = "" }) { return <td className={`px-4 py-3 ${className}`}>{children}</td>; }
