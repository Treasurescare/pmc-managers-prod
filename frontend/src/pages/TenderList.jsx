import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import DashboardLayout from "@/components/app/DashboardLayout";
import api from "@/lib/api";
import StatusBadge from "@/components/app/StatusBadge";
import { useAuth } from "@/context/AuthContext";
import { BUSINESS_CATEGORIES, ALL_CATEGORY_FLAT } from "@/data/countries";

export default function TenderList() {
  const { user } = useAuth();
  const [sp] = useSearchParams();
  const mine = sp.get("mine") === "1";
  const [rows, setRows] = useState([]);
  const [status, setStatus] = useState("all");
  const [category, setCategory] = useState("all");
  const [search, setSearch] = useState("");

  useEffect(() => {
    api.get(`/tenders${mine ? "?mine=true" : ""}`).then(({ data }) => setRows(data)).catch(() => {});
  }, [mine]);

  const filtered = rows.filter((t) => {
    if (status !== "all" && t.status !== status) return false;
    if (category !== "all" && t.category !== category) return false;
    if (search && !t.title.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const title = user?.role === "vendor" ? "Open tenders" : mine ? "My tenders" : "All tenders";

  return (
    <DashboardLayout title={title} subtitle="Filter, search and open each tender to review scope or place a bid.">
      <div className="grid md:grid-cols-4 gap-0 border-t border-l mb-6">
        <FilterCell>
          <label className="pmc-label mb-2 block">Search</label>
          <input data-testid="tender-search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Title contains..."
            className="w-full h-10 px-3 border border-input bg-white text-sm focus:border-primary focus:outline-none" />
        </FilterCell>
        <FilterCell>
          <label className="pmc-label mb-2 block">Status</label>
          <select data-testid="tender-filter-status" value={status} onChange={(e) => setStatus(e.target.value)} className="w-full h-10 px-3 border border-input bg-white text-sm">
            <option value="all">All</option>
            <option value="open">Open</option>
            <option value="closed">Closed</option>
            <option value="awarded">Awarded</option>
          </select>
        </FilterCell>
        <FilterCell>
          <label className="pmc-label mb-2 block">Category</label>
          <select data-testid="tender-filter-category" value={category} onChange={(e) => setCategory(e.target.value)} className="w-full h-10 px-3 border border-input bg-white text-sm">
            <option value="all">All</option>
            {ALL_CATEGORY_FLAT.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </FilterCell>
        <FilterCell>
          <div className="pmc-label mb-2">Results</div>
          <div className="font-mono text-2xl" data-testid="tender-count">{filtered.length}</div>
        </FilterCell>
      </div>

      <div className="border overflow-x-auto">
        <table className="w-full text-sm pmc-table" data-testid="tenders-table">
          <thead>
            <tr className="border-b bg-muted/30">
              <Th>ID</Th><Th>Type</Th><Th>Title</Th><Th>Category</Th><Th>Budget</Th><Th>Deadline</Th><Th>Status</Th><Th>Publisher</Th><Th></Th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr><td colSpan={9} className="text-center text-muted-foreground py-10">No tenders match your filter.</td></tr>
            )}
            {filtered.map((t) => (
              <tr key={t.id} className="border-b hover:bg-muted/40 transition-colors">
                <Td className="font-mono text-primary">#{t.id.slice(-6).toUpperCase()}</Td>
                <Td><span className="pmc-label text-primary">{(t.document_type || "tender").toUpperCase()}</span></Td>
                <Td>{t.title}</Td>
                <Td>{t.category}</Td>
                <Td className="font-mono">{t.budget_amount ? `${t.budget_currency} ${t.budget_amount.toLocaleString()}` : "—"}</Td>
                <Td className="font-mono">{new Date(t.submission_deadline).toLocaleString()}</Td>
                <Td><StatusBadge status={t.status} /></Td>
                <Td className="text-muted-foreground">{t.created_by_name}</Td>
                <Td><Link data-testid={`open-tender-${t.id}`} to={`/tenders/${t.id}`} className="text-primary underline underline-offset-4">Open</Link></Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </DashboardLayout>
  );
}

function FilterCell({ children }) { return <div className="p-4 border-r border-b bg-white">{children}</div>; }
function Th({ children }) { return <th className="text-left px-4 py-3 pmc-label border-b">{children}</th>; }
function Td({ children, className = "" }) { return <td className={`px-4 py-3 ${className}`}>{children}</td>; }
