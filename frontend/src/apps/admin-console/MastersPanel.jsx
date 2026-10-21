import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { mastersApi, staffApi, tenantApi, formatApiError, showApiError} from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import StaffTab from "./masters/StaffTab";
import MatrixEditor from "./masters/MatrixEditor";
import DemoModeTab from "./masters/DemoModeTab";
import RatingCriteriaTab from "./masters/RatingCriteriaTab";
import FeeCharger from "./masters/FeeCharger";
import CategoriesTab from "./masters/CategoriesTab";
import TaxonomyTab from "./masters/TaxonomyTab";
import CurrenciesTab from "./masters/CurrenciesTab";
import LegalEntityTypesTab from "./masters/LegalEntityTypesTab";
import CategoryRequestsPanel from "./masters/CategoryRequestsPanel";
import ProfileChangeRequestsPanel from "./masters/ProfileChangeRequestsPanel";
import EmdMastersPanel from "./masters/EmdMastersPanel";
import CountryLicensesTab from "./masters/CountryLicensesTab";
import GeographyTab from "./masters/GeographyTab";
import CompaniesTab from "./masters/CompaniesTab";
import GoLiveTab from "./masters/GoLiveTab";
import { InfoDot } from "@/components/InfoDot";
import { useListPager } from "@/components/ListPager";

export default function MastersPanel() {
  const { t } = useI18n();
  const [tab, setTab] = useState("staff");
  const [search, setSearch] = useState("");
  const [staff, setStaff] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [matrices, setMatrices] = useState([]);
  const [tenants, setTenants] = useState([]);
  const [tenantDraft, setTenantDraft] = useState({ code: "", name: "", kind: "corporate", country: "KZ" });
  const [showStaffNew, setShowStaffNew] = useState(false);
  const [staffDraft, setStaffDraft] = useState({
    email: "", name: "", password: "",
    roles: ["certifier"], hierarchy_level: 3,
    is_escrow_signatory: false, account_type: "staff", country_scope: [], company_id: "",
  });
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
  // v52cx — editingMatrixId toggles the Save button between create and
  // update. Null = fresh matrix, otherwise we PATCH the existing row.
  const [editingMatrixId, setEditingMatrixId] = useState(null);

  const load = useCallback(async () => {
    // Bug #13 fix — allSettled so any single 403 does not hang the panel.
    const [s, c, m, tn] = await Promise.allSettled([
      staffApi.listStaff(),
      mastersApi.listCompanies(),
      mastersApi.listMatrices(),
      tenantApi.list(),
    ]);
    if (s.status === "fulfilled") setStaff(s.value || []);
    if (c.status === "fulfilled") setCompanies(c.value || []);
    if (m.status === "fulfilled") setMatrices(m.value || []);
    if (tn.status === "fulfilled") setTenants(tn.value || []);
    const first = [s, c, m, tn].find((r) => r.status === "rejected");
    if (first) showApiError(first.reason);
  }, []);
  useEffect(() => { load(); }, [load]);

  const mq = search.trim().toLowerCase();
  const filteredCompanies = mq ? companies.filter((c) => (c.name||"").toLowerCase().includes(mq)
      || (c.code||"").toLowerCase().includes(mq)
      || (c.country||"").toLowerCase().includes(mq)) : companies;
  const filteredTenants = mq ? tenants.filter((tn) => (tn.name||"").toLowerCase().includes(mq)
      || (tn.code||"").toLowerCase().includes(mq)
      || (tn.kind||"").toLowerCase().includes(mq)) : tenants;
  const companiesPager = useListPager(filteredCompanies, { testid: "company-pager-unused" });
  void companiesPager;
  const tenantsPager = useListPager(filteredTenants, { testid: "tenant-pager" });

  const createStaff = async () => {
    if (!staffDraft.email || !staffDraft.name) return toast.error(t("panels.masters.email_name_required"));
    try {
      await staffApi.createStaff(staffDraft);
      toast.success(t("panels.masters.staff_created"));
      setShowStaffNew(false);
      setStaffDraft({ email: "", name: "", password: "", roles: ["certifier"], hierarchy_level: 3, is_escrow_signatory: false, account_type: "staff", country_scope: [], company_id: "" });
      load();
    } catch (e) { showApiError(e); }
  };

  const toggleRole = (r) => {
    const nextRoles = staffDraft.roles.includes(r)
      ? staffDraft.roles.filter((x) => x !== r)
      : [...staffDraft.roles, r];
    setStaffDraft({ ...staffDraft, roles: nextRoles });
  };

  const updateStaff = async (id, patch) => {
    try {
      await staffApi.updateStaff(id, patch);
      toast.success("Staff updated");
      load();
    } catch (e) { showApiError(e); }
  };

  const createMatrix = async () => {
    try {
      if (editingMatrixId) {
        // Pydantic model does not accept client-added id/_id/created_* fields.
        const { id, _id, created_at, created_by, ...clean } = matrixDraft; // eslint-disable-line no-unused-vars
        await mastersApi.updateMatrix(editingMatrixId, clean);
        toast.success("Matrix updated");
        setEditingMatrixId(null);
      } else {
        await mastersApi.createMatrix(matrixDraft);
        toast.success(t("panels.masters.matrix_saved"));
      }
      load();
    } catch (e) { showApiError(e); }
  };

  // v52cx — load a saved matrix back into the editor.
  const editMatrix = (m) => {
    setMatrixDraft({
      name: m.name,
      applies_to: m.applies_to || "bid",
      tender_value_min: m.tender_value_min ?? 0,
      tender_value_max: m.tender_value_max ?? 100000000,
      steps: (m.steps || []).map((s, i) => ({ order: s.order ?? i + 1, ...s })),
    });
    setEditingMatrixId(m.id);
    toast.info(`Editing "${m.name}" — change fields and click Save matrix to update.`);
  };

  // v52cx — delete with confirm. Backend 409s when a notice still uses it.
  const deleteMatrix = async (m) => {
    if (!window.confirm(`Delete approval matrix "${m.name}"? This cannot be undone.`)) return;
    try {
      await mastersApi.deleteMatrix(m.id);
      toast.success(`Deleted "${m.name}"`);
      if (editingMatrixId === m.id) setEditingMatrixId(null);
      load();
    } catch (e) { showApiError(e); }
  };

  const createTenant = async () => {
    if (!tenantDraft.code || !tenantDraft.name) return toast.error(t("panels.masters.code_name_required"));
    try {
      await tenantApi.create(tenantDraft);
      toast.success(t("panels.masters.tenant_added"));
      setTenantDraft({ code: "", name: "", kind: "corporate", country: "KZ" });
      load();
    } catch (e) { showApiError(e); }
  };

  return (
    <div data-testid="admin-masters-panel">
      {/* Tab bar as wrapping chips: every master is visible at once; the
          active chip is solid navy, the rest outlined. No horizontal scroll. */}
      <div className="flex flex-wrap gap-2 mb-4" data-testid="masters-tab-bar">
        {[["staff", t("panels.masters.tab_staff")], ["companies", t("panels.masters.tab_companies")], ["tenants", t("panels.masters.tab_tenants")], ["matrix", t("panels.masters.tab_matrix")], ["hierarchy", t("panels.masters.tab_hierarchy")], ["rating", "Rating & Fees"], ["fees", "Charge Fee"], ["categories", "Categories"], ["sectors", "Sectors"], ["contract_types", "Contract types"], ["currencies", "Currencies"], ["legal_entities", "Legal entity types"], ["country_licenses", "Country licenses"], ["geography", "Geography"], ["cat_requests", "Vendor requests"], ["profile_requests", "Profile changes"], ["emd_rules", "EMD rules"], ["go_live", "Go-live"], ["demo", "Investor Demo"]].map(([k, l]) => (
          <button key={k} onClick={() => { setTab(k); setSearch(""); }}
            className={`px-3 py-1.5 text-[11px] uppercase tracking-widest whitespace-nowrap border transition-colors ${tab === k ? "bg-brand-navy text-white border-brand-navy font-semibold" : "bg-white text-brand-navy/70 border-brand-navy/25 hover:border-brand-navy hover:text-brand-navy"}`}
            data-testid={`masters-tab-${k}`}>{l}</button>
        ))}
      </div>

      {/* Universal search bar — active on data-list tabs. */}
      {["staff","companies","tenants","matrix","hierarchy"].includes(tab) && (
        <input value={search} onChange={(e) => setSearch(e.target.value)}
          placeholder={`Search ${tab}…`}
          data-testid={`masters-search-${tab}`}
          className="w-full mb-4 px-3 py-2 border border-brand-navy/20 text-sm bg-white" />
      )}

      {tab === "staff" && (
        <StaffTab
          staff={(() => { const q = search.trim().toLowerCase(); return q
            ? staff.filter((s) => (s.name||"").toLowerCase().includes(q)
                || (s.email||"").toLowerCase().includes(q)
                || (s.roles||[s.role]||[]).some((r) => (r||"").toLowerCase().includes(q)))
            : staff; })()}
          showStaffNew={showStaffNew} setShowStaffNew={setShowStaffNew}
          staffDraft={staffDraft} setStaffDraft={setStaffDraft}
          onCreate={createStaff} onToggleRole={toggleRole} onUpdate={updateStaff}
          companies={companies}
        />
      )}

      {tab === "companies" && (
        <CompaniesTab companies={filteredCompanies} onChange={load} />
      )}

      {tab === "matrix" && (
        <MatrixEditor
          matrixDraft={matrixDraft} setMatrixDraft={setMatrixDraft}
          matrices={matrices} onSave={createMatrix}
          editingId={editingMatrixId}
          onCancelEdit={() => setEditingMatrixId(null)}
          onEdit={editMatrix} onDelete={deleteMatrix}
        />
      )}

      {tab === "hierarchy" && (
        <div className="bg-white border p-4" data-testid="hierarchy-view">
          <div className="pmc-label mb-2">{t("panels.masters.hierarchy_title")}</div>
          {[10, 5, 3, 1].map((lvl) => {
            const q = search.trim().toLowerCase();
            const row = staff.filter((s) => (s.hierarchy_level || 1) === lvl
              && (!q || (s.name||"").toLowerCase().includes(q)
                    || (s.email||"").toLowerCase().includes(q)
                    || (s.roles||[s.role]||[]).some((r) => (r||"").toLowerCase().includes(q))));
            return (
            <div key={lvl} className="mb-3">
              <div className="text-xs uppercase tracking-widest text-slate-500">{t("panels.masters.level_prefix")} {lvl}</div>
              <div className="grid grid-cols-3 gap-2 mt-1">
                {row.map((s) => (
                  <div key={s.id} className="border p-2 text-sm">
                    <div>{s.name}</div>
                    <div className="text-xs text-slate-500">{s.email}</div>
                    <div className="text-xs mt-1">{(s.roles || [s.role]).join(", ")}</div>
                  </div>
                ))}
              </div>
            </div>
          );})}
        </div>
      )}

      {tab === "demo" && <DemoModeTab />}

      {tab === "rating" && <RatingCriteriaTab />}

      {tab === "fees" && <FeeCharger />}

      {tab === "categories" && <CategoriesTab />}
      {tab === "sectors" && <TaxonomyTab kind="sector" label="Sector" />}
      {tab === "contract_types" && <TaxonomyTab kind="contract_type" label="Contract type" />}
      {tab === "currencies" && <CurrenciesTab />}
      {tab === "legal_entities" && <LegalEntityTypesTab />}
      {tab === "country_licenses" && <CountryLicensesTab />}
      {tab === "geography" && <GeographyTab />}

      {tab === "cat_requests" && <CategoryRequestsPanel />}
      {tab === "profile_requests" && <ProfileChangeRequestsPanel />}
      {tab === "emd_rules" && <EmdMastersPanel />}
      {tab === "go_live" && <GoLiveTab />}

      {tab === "tenants" && (
        <>
          <div className="bg-white border p-4 mb-4 grid gap-2 md:grid-cols-5" data-testid="tenant-new">
            <label className="text-xs uppercase tracking-widest text-brand-navy/60">
              {t("panels.masters.code")}<InfoDot tip="Uppercase tenant slug. Used as sub-path (e.g. /t/ACME) and in emails. Must be unique." />
              <input placeholder={t("panels.masters.code")} value={tenantDraft.code}
                onChange={(e) => setTenantDraft({ ...tenantDraft, code: e.target.value.toUpperCase() })}
                className="mt-1 w-full px-3 py-2 border normal-case tracking-normal" data-testid="tenant-code" />
            </label>
            <label className="text-xs uppercase tracking-widest text-brand-navy/60 md:col-span-2">
              {t("panels.masters.name")}<InfoDot tip="Display name shown on the tenant portal (e.g. 'Acme Holdings Ltd')." />
              <input placeholder={t("panels.masters.name")} value={tenantDraft.name}
                onChange={(e) => setTenantDraft({ ...tenantDraft, name: e.target.value })}
                className="mt-1 w-full px-3 py-2 border normal-case tracking-normal" data-testid="tenant-name" />
            </label>
            <label className="text-xs uppercase tracking-widest text-brand-navy/60">
              Kind<InfoDot tip="PMC = internal, Corporate = client-owned portal, Government = public-sector white-label." />
              <select value={tenantDraft.kind}
                onChange={(e) => setTenantDraft({ ...tenantDraft, kind: e.target.value })}
                className="mt-1 w-full px-3 py-2 border bg-white normal-case tracking-normal" data-testid="tenant-kind">
                <option value="pmc">{t("panels.masters.tenant_kind_pmc")}</option>
                <option value="corporate">{t("panels.masters.tenant_kind_corporate")}</option>
                <option value="government">{t("panels.masters.tenant_kind_government")}</option>
              </select>
            </label>
            <button onClick={createTenant} data-testid="tenant-create"
              className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white self-end">
              {t("panels.masters.add_tenant")}
            </button>
          </div>
          <div className="bg-white border">
            {filteredTenants.length === 0 ? (
              <div className="p-6 text-sm text-slate-500">
                {tenants.length === 0 ? t("panels.masters.no_tenants") : "No matches"}
              </div>
            ) : tenantsPager.paged.map((tn) => (
              <div key={tn.id} className="border-b p-3 text-sm" data-testid={`tenant-row-${tn.code}`}>
                <span className="font-mono text-xs mr-3">{tn.code}</span>
                <strong>{tn.name}</strong>
                <span className="ml-3 text-xs bg-slate-100 px-2 py-0.5 rounded">{tn.kind}</span>
                <span className="ml-2 text-xs text-slate-500">{tn.country}</span>
              </div>
            ))}
            {tenantsPager.controls}
          </div>
        </>
      )}
    </div>
  );
}
