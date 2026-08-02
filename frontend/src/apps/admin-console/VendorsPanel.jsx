import { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";
import { api, vendorInviteApi, formatApiError } from "@/lib/api";
import BulkInviteModal from "./BulkInviteModal";

function KpiTile({ label, value }) {
  return (
    <div className="border border-brand-navy/10 bg-white p-4">
      <div className="pmc-label">{label}</div>
      <div className="pmc-stat-lg mt-1 text-brand-navy">{value ?? "—"}</div>
    </div>
  );
}

export default function VendorsPanel() {
  const [vendors, setVendors] = useState([]);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState(null);
  const [kpi, setKpi] = useState(null);
  const [loadingKpi, setLoadingKpi] = useState(false);
  const [showInvite, setShowInvite] = useState(false);
  const [showBulk, setShowBulk] = useState(false);
  const [inviteDraft, setInviteDraft] = useState({ email: "", company_name: "", country: "KZ", contact_name: "" });
  const [templateMeta, setTemplateMeta] = useState({ available: false });

  const load = useCallback(() => {
    api.get("/api/v1/vendors", { params: search ? { search } : {} })
      .then((r) => setVendors(r.data || []))
      .catch((e) => toast.error(formatApiError(e)));
  }, [search]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    vendorInviteApi.templateMeta().then(setTemplateMeta).catch(() => {});
  }, []);

  useEffect(() => {
    if (!selected) { setKpi(null); return; }
    setLoadingKpi(true);
    api.get(`/api/v1/vendors/${selected.vendor_ref}/kpi`)
      .then((r) => setKpi(r.data))
      .catch((e) => toast.error(formatApiError(e)))
      .finally(() => setLoadingKpi(false));
  }, [selected]);

  const sendInvite = async () => {
    if (!inviteDraft.email) return toast.error("Email is required");
    try {
      const r = await vendorInviteApi.invite(inviteDraft);
      toast.success(`Invited ${r.email} · ${r.vendor_ref}`);
      setShowInvite(false);
      setInviteDraft({ email: "", company_name: "", country: "KZ", contact_name: "" });
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const uploadTemplate = async (f) => {
    if (!f) return;
    try {
      const r = await vendorInviteApi.uploadTemplate(f);
      toast.success(`Template uploaded · ${r.file_name}`);
      setTemplateMeta({ available: true, file_name: r.file_name, size_bytes: r.size_bytes });
    } catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div className="space-y-4" data-testid="admin-vendors-panel">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="text-sm text-brand-navy/70">
          {vendors.length} vendors · use "Invite vendor" to pre-register a supplier
        </div>
        <div className="flex gap-2 items-center">
          <label className="text-xs cursor-pointer border border-brand-navy/20 px-3 py-1.5 uppercase tracking-widest text-brand-navy hover:bg-brand-navy/5"
                 data-testid="vendor-template-upload-label">
            {templateMeta.available ? "Replace registration template" : "Upload registration template"}
            <input type="file" accept=".pdf,.docx,.doc" onChange={(e) => uploadTemplate(e.target.files?.[0])}
                   className="hidden" data-testid="vendor-template-upload" />
          </label>
          {templateMeta.available && (
            <a href={vendorInviteApi.templateDownloadUrl()} target="_blank" rel="noreferrer"
               className="text-xs underline text-brand-navy/70"
               data-testid="vendor-template-download">Download current ({templateMeta.file_name})</a>
          )}
          <button onClick={() => setShowBulk(true)} data-testid="vendor-bulk-invite-open"
                  className="px-4 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5">
            Bulk invite (CSV)
          </button>
          <button onClick={() => setShowInvite(!showInvite)}
                  data-testid="vendor-invite-toggle"
                  className="px-5 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
            {showInvite ? "Cancel" : "Invite vendor"}
          </button>
        </div>
      </div>

      <BulkInviteModal open={showBulk} onClose={() => setShowBulk(false)} onDone={load} />

      {showInvite && (
        <div className="border border-brand-navy-soft/40 bg-white p-6 grid gap-3 md:grid-cols-4"
             data-testid="vendor-invite-form">
          <label className="md:col-span-2 text-sm">
            <span className="pmc-label">Vendor email</span>
            <input value={inviteDraft.email} type="email" required
                   onChange={(e) => setInviteDraft({ ...inviteDraft, email: e.target.value })}
                   data-testid="vendor-invite-email"
                   className="mt-1 w-full px-3 py-2 border border-brand-navy/20" />
          </label>
          <label className="md:col-span-2 text-sm">
            <span className="pmc-label">Company name</span>
            <input value={inviteDraft.company_name}
                   onChange={(e) => setInviteDraft({ ...inviteDraft, company_name: e.target.value })}
                   data-testid="vendor-invite-company"
                   className="mt-1 w-full px-3 py-2 border border-brand-navy/20" />
          </label>
          <label className="text-sm">
            <span className="pmc-label">Contact name</span>
            <input value={inviteDraft.contact_name}
                   onChange={(e) => setInviteDraft({ ...inviteDraft, contact_name: e.target.value })}
                   className="mt-1 w-full px-3 py-2 border border-brand-navy/20" />
          </label>
          <label className="text-sm">
            <span className="pmc-label">Country</span>
            <input value={inviteDraft.country}
                   onChange={(e) => setInviteDraft({ ...inviteDraft, country: e.target.value })}
                   className="mt-1 w-full px-3 py-2 border border-brand-navy/20" />
          </label>
          <div className="md:col-span-4 text-[11px] text-brand-navy/50">
            An email will be sent asking the vendor to verify their address and set a password.
            Their vendor reference is generated automatically.
          </div>
          <div className="md:col-span-4 flex justify-end">
            <button onClick={sendInvite} data-testid="vendor-invite-submit"
                    className="px-8 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90">
              Send invitation
            </button>
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[5fr_7fr]">
        <div>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name or ref…"
            data-testid="vendor-search"
            className="w-full px-4 py-2 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white text-sm mb-3"
          />
          <div className="border border-brand-navy/10 bg-white">
            {vendors.length === 0 && (
              <div className="p-6 text-brand-navy/50 text-sm">
                No vendors yet. Invite one above or approve a registration.
              </div>
            )}
            {vendors.map((v) => (
              <button
                key={v.id}
                type="button"
                onClick={() => setSelected(v)}
                data-testid={`vendor-row-${v.vendor_ref}`}
                className={"w-full text-left p-4 border-b border-brand-navy/10 hover:bg-brand-navy/5 " + (selected?.id === v.id ? "bg-brand-navy/5" : "")}
              >
                <div className="text-sm font-semibold text-brand-navy">{v.company_name || "(no name)"}</div>
                <div className="text-xs font-mono text-brand-navy-soft mt-1">{v.vendor_ref}</div>
                <div className="text-xs text-brand-navy/50 mt-0.5">
                  {v.email} · {v.country}
                  {v.email_verified === false && <span className="ml-2 text-amber-600">· pending verify</span>}
                  {v.is_active === false && v.email_verified !== false && <span className="ml-2 text-slate-500">· inactive</span>}
                </div>
              </button>
            ))}
          </div>
        </div>

        <div>
          {!selected ? (
            <div className="border border-dashed border-brand-navy/20 bg-white p-14 text-center text-brand-navy/50">
              Select a vendor on the left to see their KPI dashboard.
            </div>
          ) : loadingKpi || !kpi ? (
            <div className="border border-brand-navy/10 bg-white p-14 text-center text-brand-navy/50">Loading vendor KPI…</div>
          ) : (
            <div className="border border-brand-navy/10 bg-white p-6" data-testid="vendor-kpi">
              <div className="pmc-label">Approved supplier</div>
              <h3 className="font-display text-2xl text-brand-navy mt-1">{kpi.company_name || "(no name)"}</h3>
              <div className="text-sm font-mono text-brand-navy-soft mt-1">{kpi.vendor_ref}</div>
              <div className="text-xs text-brand-navy/50 mt-0.5">{kpi.email} · {kpi.country} · {kpi.primary_sector || "sector n/a"}</div>
              <div className="mt-6 grid gap-3 md:grid-cols-4">
                <KpiTile label="Days approved" value={kpi.approved_days_ago} />
                <KpiTile label="Review turnaround (h)" value={kpi.time_to_decision_hours} />
                <KpiTile label="KZ licenses" value={kpi.kz_licenses_count} />
                <KpiTile label="Categories" value={kpi.categories_count} />
              </div>
              <div className="mt-6 grid gap-4 md:grid-cols-2 text-sm">
                <div>
                  <div className="pmc-label">KZ licenses held</div>
                  {(kpi.kz_licenses_held || []).length === 0
                    ? <div className="text-brand-navy/50 mt-1">None</div>
                    : (<ul className="mt-1 text-brand-navy">
                        {kpi.kz_licenses_held.map((l) => <li key={l}>· {l}</li>)}</ul>)}
                </div>
                <div>
                  <div className="pmc-label">Operating regions</div>
                  {(kpi.operating_regions || []).length === 0
                    ? <div className="text-brand-navy/50 mt-1">Not declared</div>
                    : <div className="mt-1 text-brand-navy">{kpi.operating_regions.join(", ")}</div>}
                </div>
                <div className="md:col-span-2">
                  <div className="pmc-label">Business categories declared</div>
                  {(kpi.categories_declared || []).length === 0
                    ? <div className="text-brand-navy/50 mt-1">None</div>
                    : <div className="mt-1 text-brand-navy">{kpi.categories_declared.join(" · ")}</div>}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
