import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { mastersApi, staffApi, tenantApi, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import StaffTab from "./masters/StaffTab";
import MatrixEditor from "./masters/MatrixEditor";

export default function MastersPanel() {
  const { t } = useI18n();
  const [tab, setTab] = useState("staff");
  const [staff, setStaff] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [matrices, setMatrices] = useState([]);
  const [tenants, setTenants] = useState([]);
  const [tenantDraft, setTenantDraft] = useState({ code: "", name: "", kind: "corporate", country: "KZ" });
  const [showStaffNew, setShowStaffNew] = useState(false);
  const [staffDraft, setStaffDraft] = useState({
    email: "", name: "", password: "",
    roles: ["reviewer"], hierarchy_level: 3,
  });
  const [companyDraft, setCompanyDraft] = useState({ name: "", code: "", country: "KZ" });
  const [matrixDraft, setMatrixDraft] = useState({
    name: "Standard Pipeline", applies_to: "bid",
    tender_value_min: 0, tender_value_max: 100000000,
    steps: [
      { order: 1, role_code: "escrow_agent", action_label: "Escrow accept EMD", sla_hours: 24, required: true },
      { order: 2, role_code: "admin", action_label: "Admin flag to Certifier", sla_hours: 24, required: true },
      { order: 3, role_code: "certifier", action_label: "Certifier site inspection", sla_hours: 72, required: true },
      { order: 4, role_code: "legal_counsel", action_label: "Legal KYC clearance", sla_hours: 48, required: true },
      { order: 5, role_code: "accounting", action_label: "Accounting sign-off", sla_hours: 24, required: true },
      { order: 6, role_code: "committee_member", action_label: "Committee award", sla_hours: 168, required: true },
    ],
  });

  const load = useCallback(async () => {
    try {
      const [s, c, m, t] = await Promise.all([
        staffApi.listStaff(), mastersApi.listCompanies(),
        mastersApi.listMatrices(), tenantApi.list().catch(() => []),
      ]);
      setStaff(s); setCompanies(c); setMatrices(m); setTenants(t);
    } catch (e) { toast.error(formatApiError(e)); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const createStaff = async () => {
    if (!staffDraft.email || !staffDraft.name) return toast.error(t("panels.masters.email_name_required"));
    try {
      await staffApi.createStaff(staffDraft);
      toast.success(t("panels.masters.staff_created"));
      setShowStaffNew(false);
      setStaffDraft({ email: "", name: "", password: "", roles: ["reviewer"], hierarchy_level: 3 });
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const toggleRole = (r) => {
    const nextRoles = staffDraft.roles.includes(r)
      ? staffDraft.roles.filter((x) => x !== r)
      : [...staffDraft.roles, r];
    setStaffDraft({ ...staffDraft, roles: nextRoles });
  };

  const createCompany = async () => {
    if (!companyDraft.name || !companyDraft.code) return toast.error(t("panels.masters.name_code_required"));
    try {
      await mastersApi.createCompany(companyDraft);
      toast.success(t("panels.masters.company_added"));
      setCompanyDraft({ name: "", code: "", country: "KZ" });
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const createMatrix = async () => {
    try {
      await mastersApi.createMatrix(matrixDraft);
      toast.success(t("panels.masters.matrix_saved"));
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const createTenant = async () => {
    if (!tenantDraft.code || !tenantDraft.name) return toast.error(t("panels.masters.code_name_required"));
    try {
      await tenantApi.create(tenantDraft);
      toast.success(t("panels.masters.tenant_added"));
      setTenantDraft({ code: "", name: "", kind: "corporate", country: "KZ" });
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div data-testid="admin-masters-panel">
      <div className="flex gap-2 mb-4 border-b">
        {[["staff", t("panels.masters.tab_staff")], ["companies", t("panels.masters.tab_companies")], ["tenants", t("panels.masters.tab_tenants")], ["matrix", t("panels.masters.tab_matrix")], ["hierarchy", t("panels.masters.tab_hierarchy")]].map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`px-4 py-2 text-xs uppercase tracking-widest ${tab === k ? "border-b-2 border-brand-navy font-semibold" : "text-slate-500"}`}
            data-testid={`masters-tab-${k}`}>{l}</button>
        ))}
      </div>

      {tab === "staff" && (
        <StaffTab
          staff={staff}
          showStaffNew={showStaffNew} setShowStaffNew={setShowStaffNew}
          staffDraft={staffDraft} setStaffDraft={setStaffDraft}
          onCreate={createStaff} onToggleRole={toggleRole}
        />
      )}

      {tab === "companies" && (
        <>
          <div className="bg-white border p-4 mb-4 grid gap-2 md:grid-cols-4" data-testid="company-new">
            <input placeholder={t("panels.masters.name")} value={companyDraft.name}
              onChange={(e) => setCompanyDraft({ ...companyDraft, name: e.target.value })}
              className="px-3 py-2 border" data-testid="company-name" />
            <input placeholder={t("panels.masters.code")} value={companyDraft.code}
              onChange={(e) => setCompanyDraft({ ...companyDraft, code: e.target.value })}
              className="px-3 py-2 border" data-testid="company-code" />
            <input placeholder={t("panels.masters.country")} value={companyDraft.country}
              onChange={(e) => setCompanyDraft({ ...companyDraft, country: e.target.value })}
              className="px-3 py-2 border" />
            <button onClick={createCompany} data-testid="company-create"
              className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white">
              {t("panels.masters.add_company")}
            </button>
          </div>
          <div className="bg-white border">
            {companies.map((c) => (
              <div key={c.id} className="border-b p-3 text-sm" data-testid={`company-row-${c.code}`}>
                <span className="font-mono text-xs mr-3">{c.code}</span>
                <strong>{c.name}</strong>
                <span className="ml-3 text-xs text-slate-500">{c.country}</span>
              </div>
            ))}
            {companies.length === 0 && <div className="p-6 text-sm text-slate-500">{t("panels.masters.no_companies")}</div>}
          </div>
        </>
      )}

      {tab === "matrix" && (
        <MatrixEditor
          matrixDraft={matrixDraft} setMatrixDraft={setMatrixDraft}
          matrices={matrices} onSave={createMatrix}
        />
      )}

      {tab === "hierarchy" && (
        <div className="bg-white border p-4" data-testid="hierarchy-view">
          <div className="pmc-label mb-2">{t("panels.masters.hierarchy_title")}</div>
          {[10, 5, 3, 1].map((lvl) => (
            <div key={lvl} className="mb-3">
              <div className="text-xs uppercase tracking-widest text-slate-500">{t("panels.masters.level_prefix")} {lvl}</div>
              <div className="grid grid-cols-3 gap-2 mt-1">
                {staff.filter((s) => (s.hierarchy_level || 1) === lvl).map((s) => (
                  <div key={s.id} className="border p-2 text-sm">
                    <div>{s.name}</div>
                    <div className="text-xs text-slate-500">{s.email}</div>
                    <div className="text-xs mt-1">{(s.roles || [s.role]).join(", ")}</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === "tenants" && (
        <>
          <div className="bg-white border p-4 mb-4 grid gap-2 md:grid-cols-5" data-testid="tenant-new">
            <input placeholder={t("panels.masters.code")} value={tenantDraft.code}
              onChange={(e) => setTenantDraft({ ...tenantDraft, code: e.target.value.toUpperCase() })}
              className="px-3 py-2 border" data-testid="tenant-code" />
            <input placeholder={t("panels.masters.name")} value={tenantDraft.name}
              onChange={(e) => setTenantDraft({ ...tenantDraft, name: e.target.value })}
              className="px-3 py-2 border md:col-span-2" data-testid="tenant-name" />
            <select value={tenantDraft.kind}
              onChange={(e) => setTenantDraft({ ...tenantDraft, kind: e.target.value })}
              className="px-3 py-2 border bg-white" data-testid="tenant-kind">
              <option value="pmc">{t("panels.masters.tenant_kind_pmc")}</option>
              <option value="corporate">{t("panels.masters.tenant_kind_corporate")}</option>
              <option value="government">{t("panels.masters.tenant_kind_government")}</option>
            </select>
            <button onClick={createTenant} data-testid="tenant-create"
              className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white">
              {t("panels.masters.add_tenant")}
            </button>
          </div>
          <div className="bg-white border">
            {tenants.map((tn) => (
              <div key={tn.id} className="border-b p-3 text-sm" data-testid={`tenant-row-${tn.code}`}>
                <span className="font-mono text-xs mr-3">{tn.code}</span>
                <strong>{tn.name}</strong>
                <span className="ml-3 text-xs bg-slate-100 px-2 py-0.5 rounded">{tn.kind}</span>
                <span className="ml-2 text-xs text-slate-500">{tn.country}</span>
              </div>
            ))}
            {tenants.length === 0 && <div className="p-6 text-sm text-slate-500">{t("panels.masters.no_tenants")}</div>}
          </div>
        </>
      )}
    </div>
  );
}
