import { useEffect, useState } from "react";
import DashboardLayout from "@/components/app/DashboardLayout";
import api, { formatApiError } from "@/lib/api";
import StatusBadge from "@/components/app/StatusBadge";
import { toast } from "sonner";
import { Check, X } from "lucide-react";
import { COUNTRIES } from "@/data/countries";

export default function AdminVendors() {
  const [vendors, setVendors] = useState([]);
  const [selected, setSelected] = useState(null);

  const load = async () => { try { const { data } = await api.get("/admin/vendors"); setVendors(data); } catch {} };
  useEffect(() => { load(); }, []);

  const act = async (id, kind) => {
    try { await api.post(`/admin/vendors/${id}/${kind}`); toast.success(`Vendor ${kind}d`); load(); setSelected(null); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <DashboardLayout title="Vendor approvals" subtitle="Review KYC files and approve or reject vendor applications.">
      <div className="grid lg:grid-cols-[1fr_400px] gap-6">
        <div className="border overflow-x-auto">
          <table className="w-full text-sm pmc-table" data-testid="admin-vendors-table">
            <thead>
              <tr className="border-b bg-muted/30">
                <Th>Company</Th><Th>Email</Th><Th>Country</Th><Th>Status</Th><Th>Submitted</Th><Th></Th>
              </tr>
            </thead>
            <tbody>
              {vendors.length === 0 && <tr><td colSpan={6} className="p-8 text-center text-muted-foreground">No vendor applications yet.</td></tr>}
              {vendors.map((v) => {
                const p = v.vendor_profile || {};
                return (
                  <tr key={v.id} className={`border-b hover:bg-muted/40 transition-colors ${selected?.id === v.id ? "bg-primary/5" : ""}`}>
                    <Td>{p.company_name || v.name || "—"}</Td>
                    <Td>{v.email}</Td>
                    <Td>{p.country || "—"}</Td>
                    <Td><StatusBadge status={v.vendor_status} /></Td>
                    <Td className="font-mono text-xs">{v.created_at ? new Date(v.created_at).toLocaleDateString() : "—"}</Td>
                    <Td><button data-testid={`vendor-inspect-${v.id}`} onClick={() => setSelected(v)} className="text-primary underline underline-offset-4">Inspect</button></Td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <aside className="border p-6" data-testid="vendor-inspect-panel">
          {!selected ? (
            <div className="text-sm text-muted-foreground">Select a vendor to inspect their submission.</div>
          ) : (
            <VendorInspector v={selected} onAction={act} />
          )}
        </aside>
      </div>
    </DashboardLayout>
  );
}

function VendorInspector({ v, onAction }) {
  const p = v.vendor_profile || {};
  const country = COUNTRIES.find((c) => c.code === p.country);
  return (
    <div>
      <div className="pmc-label">Vendor</div>
      <h3 className="font-serif text-2xl mt-1">{p.company_name || v.name}</h3>
      <div className="mt-1 text-sm text-muted-foreground">{v.email}</div>
      <div className="mt-2"><StatusBadge status={v.vendor_status} /></div>

      {p.company_name ? (
        <div className="mt-6 space-y-4 text-sm">
          <Row k="Legal entity" val={p.legal_entity_type} />
          <Row k="Country" val={country ? `${country.name} (${p.country})` : p.country} />
          <Row k={p.country_id_label || "Business ID"} val={p.registration_number} mono />
          <Row k="TIN / VAT" val={p.tax_id} mono />
          <Row k="Incorporation date" val={p.incorporation_date} />
          <Row k="Employees" val={p.employees_count} />
          <Row k="Primary contact" val={`${p.contact_name || ""} · ${p.contact_title || ""} · ${p.contact_email || ""} · ${p.contact_office_phone || ""}`} />
          <Row k="Authorized signatory" val={`${p.signatory_name || ""} · ${p.signatory_title || ""}`} />
          <Row k="Registered address" val={p.registered_address} />
          <Row k="Website" val={p.website} />
          <Row k="Sector" val={p.primary_sector} />
          <Row k="Description" val={p.business_description} />
          <Row k="Operating regions" val={(p.operating_regions || []).join(", ")} />
          <Row k="Categories" val={(p.business_categories || []).join(", ") || "—"} />
          {(p.turnover_year1 || p.turnover_year2 || p.turnover_year3) && (
            <Row k="Turnover (3y)" mono val={`${p.turnover_currency || "USD"} ${p.turnover_year1 || 0} / ${p.turnover_year2 || 0} / ${p.turnover_year3 || 0}`} />
          )}
          {p.bank_name && <Row k="Bank" val={`${p.bank_name} · ${p.bank_account_number} · ${p.bank_swift}`} mono />}
          {p.previous_projects?.length > 0 && (
            <div>
              <div className="pmc-label mb-1">Previous projects</div>
              <ul className="text-xs space-y-1">{p.previous_projects.map((pr, i) => (
                <li key={i}>· {pr.name} — {pr.client} ({pr.currency} {pr.value}, {pr.period})</li>
              ))}</ul>
            </div>
          )}
          {p.references?.length > 0 && (
            <div>
              <div className="pmc-label mb-1">References</div>
              <ul className="text-xs space-y-1">{p.references.map((r, i) => (
                <li key={i}>· {r.name} — {r.position} @ {r.company} · {r.email} · {r.phone}</li>
              ))}</ul>
            </div>
          )}
          {p.litigation_history && <Row k="Litigation (5y)" val={p.litigation_history} />}
          {(p.documents || []).length > 0 && (
            <div>
              <div className="pmc-label mb-1">Documents</div>
              <ul className="border">
                {p.documents.map((d, i) => (
                  <li key={i} className="flex items-center justify-between px-3 py-2 border-b last:border-b-0 text-sm">
                    <span>
                      <span>{d.name}</span>
                      {d.category && <span className="pmc-label ml-2 text-primary">{d.category}</span>}
                    </span>
                    <a href={d.data} download={d.name} className="text-primary underline underline-offset-4 text-xs">Download</a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : (
        <div className="mt-6 border p-4 text-sm text-muted-foreground">This vendor has not filed a KYC profile yet.</div>
      )}

      {v.vendor_status !== "approved" && (
        <button data-testid="admin-approve-btn" onClick={() => onAction(v.id, "approve")}
          className="mt-6 w-full inline-flex items-center justify-center gap-2 bg-primary text-white h-11 text-sm hover:-translate-y-0.5 transition-transform">
          <Check className="h-4 w-4" /> Approve vendor
        </button>
      )}
      {v.vendor_status !== "rejected" && (
        <button data-testid="admin-reject-btn" onClick={() => onAction(v.id, "reject")}
          className="mt-2 w-full inline-flex items-center justify-center gap-2 border border-destructive text-destructive h-11 text-sm hover:bg-destructive hover:text-white transition-colors">
          <X className="h-4 w-4" /> Reject
        </button>
      )}
    </div>
  );
}

function Row({ k, val, mono }) {
  return (
    <div className="border-b pb-2">
      <div className="pmc-label mb-1">{k}</div>
      <div className={mono ? "font-mono" : ""}>{val || "—"}</div>
    </div>
  );
}

function Th({ children }) { return <th className="text-left px-4 py-3 pmc-label border-b">{children}</th>; }
function Td({ children, className = "" }) { return <td className={`px-4 py-3 ${className}`}>{children}</td>; }
