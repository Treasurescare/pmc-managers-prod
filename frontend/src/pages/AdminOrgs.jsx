import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Building2, LayoutList, Trash2 } from "lucide-react";
import DashboardLayout from "@/components/app/DashboardLayout";
import api from "@/lib/api";
import { formatApiError } from "@/lib/api";

const LEVELS = [
  { value: "dept_head", label: "Department Head" },
  { value: "finance", label: "Finance" },
  { value: "contracts_committee", label: "Contracts Committee" },
];

export default function AdminOrgs() {
  const [orgs, setOrgs] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [orgForm, setOrgForm] = useState({ name: "", code: "", country: "KZ", description: "" });
  const [creatingOrg, setCreatingOrg] = useState(false);
  const [deptForm, setDeptForm] = useState({ org_id: "", name: "", code: "", approval_thresholds: [] });
  const [creatingDept, setCreatingDept] = useState(false);

  const load = async () => {
    try {
      const [o, d] = await Promise.all([api.get("/orgs"), api.get("/departments")]);
      setOrgs(o.data); setDepartments(d.data);
    } catch (e) { toast.error(formatApiError(e)); }
  };
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const createOrg = async (e) => {
    e.preventDefault();
    setCreatingOrg(true);
    try {
      await api.post("/orgs", orgForm);
      toast.success("Organisation created");
      setOrgForm({ name: "", code: "", country: "KZ", description: "" });
      load();
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setCreatingOrg(false); }
  };

  const addThreshold = () => setDeptForm((s) => ({ ...s, approval_thresholds: [...s.approval_thresholds, { threshold: 10000, level: "dept_head" }] }));
  const setThreshold = (i, patch) => setDeptForm((s) => ({ ...s, approval_thresholds: s.approval_thresholds.map((t, idx) => idx === i ? { ...t, ...patch } : t) }));
  const removeThreshold = (i) => setDeptForm((s) => ({ ...s, approval_thresholds: s.approval_thresholds.filter((_, idx) => idx !== i) }));

  const createDept = async (e) => {
    e.preventDefault();
    if (!deptForm.org_id) { toast.error("Select an org"); return; }
    setCreatingDept(true);
    try {
      await api.post("/departments", {
        ...deptForm,
        approval_thresholds: deptForm.approval_thresholds.map((t) => ({ threshold: Number(t.threshold) || 0, level: t.level })),
      });
      toast.success("Department created");
      setDeptForm({ org_id: "", name: "", code: "", approval_thresholds: [] });
      load();
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setCreatingDept(false); }
  };

  const orgMap = orgs.reduce((m, o) => { m[o.id] = o; return m; }, {});

  return (
    <DashboardLayout title="Buyer Organisations & Departments" subtitle="Manage the org hierarchy and per-department approval thresholds">
      <div className="grid lg:grid-cols-2 gap-8">
        {/* Orgs */}
        <section data-testid="admin-orgs-section">
          <div className="pmc-label mb-2 flex items-center gap-2"><Building2 className="h-3 w-3" /> Organisations</div>
          <form onSubmit={createOrg} className="border p-4 space-y-3 bg-white" data-testid="org-form">
            <div className="grid grid-cols-2 gap-3">
              <input required data-testid="org-name" placeholder="Name" value={orgForm.name} onChange={(e) => setOrgForm({ ...orgForm, name: e.target.value })}
                className="h-10 px-3 border border-input focus:border-primary focus:outline-none" />
              <input required data-testid="org-code" placeholder="Code (e.g. PMC-KZ)" value={orgForm.code} onChange={(e) => setOrgForm({ ...orgForm, code: e.target.value })}
                className="h-10 px-3 border border-input focus:border-primary focus:outline-none font-mono" />
              <input placeholder="Country (2-letter)" maxLength={2} value={orgForm.country} onChange={(e) => setOrgForm({ ...orgForm, country: e.target.value.toUpperCase() })}
                className="h-10 px-3 border border-input focus:border-primary focus:outline-none font-mono uppercase" />
              <input placeholder="Description" value={orgForm.description} onChange={(e) => setOrgForm({ ...orgForm, description: e.target.value })}
                className="h-10 px-3 border border-input focus:border-primary focus:outline-none" />
            </div>
            <button data-testid="org-create-btn" disabled={creatingOrg} className="text-sm bg-primary text-white px-4 py-2 disabled:opacity-60 hover:-translate-y-0.5 transition-transform">
              {creatingOrg ? "Creating..." : "Create org"}
            </button>
          </form>

          <div className="mt-4 border" data-testid="orgs-list">
            <table className="w-full text-sm">
              <thead className="bg-muted/30"><tr><th className="pmc-label text-left px-3 py-2">Name</th><th className="pmc-label text-left px-3 py-2">Code</th><th className="pmc-label text-left px-3 py-2">Country</th></tr></thead>
              <tbody>
                {orgs.map((o) => (
                  <tr key={o.id} className="border-b" data-testid={`org-row-${o.id}`}>
                    <td className="px-3 py-2">{o.name}</td>
                    <td className="px-3 py-2 font-mono">{o.code}</td>
                    <td className="px-3 py-2 font-mono">{o.country}</td>
                  </tr>
                ))}
                {orgs.length === 0 && <tr><td colSpan={3} className="px-3 py-6 text-center text-muted-foreground">No orgs yet.</td></tr>}
              </tbody>
            </table>
          </div>
        </section>

        {/* Departments */}
        <section data-testid="admin-depts-section">
          <div className="pmc-label mb-2 flex items-center gap-2"><LayoutList className="h-3 w-3" /> Departments</div>
          <form onSubmit={createDept} className="border p-4 space-y-3 bg-white" data-testid="dept-form">
            <div className="grid grid-cols-2 gap-3">
              <select required data-testid="dept-org" value={deptForm.org_id} onChange={(e) => setDeptForm({ ...deptForm, org_id: e.target.value })}
                className="h-10 px-3 border border-input bg-white focus:border-primary focus:outline-none">
                <option value="">— select org —</option>
                {orgs.map((o) => <option key={o.id} value={o.id}>{o.name} ({o.code})</option>)}
              </select>
              <input required data-testid="dept-name" placeholder="Department name" value={deptForm.name} onChange={(e) => setDeptForm({ ...deptForm, name: e.target.value })}
                className="h-10 px-3 border border-input focus:border-primary focus:outline-none" />
              <input required data-testid="dept-code" placeholder="Code" value={deptForm.code} onChange={(e) => setDeptForm({ ...deptForm, code: e.target.value })}
                className="h-10 px-3 border border-input focus:border-primary focus:outline-none font-mono" />
            </div>
            <div className="border-t pt-3 space-y-2">
              <div className="pmc-label text-xs">Approval thresholds (budget-based)</div>
              {deptForm.approval_thresholds.map((t, i) => (
                <div key={i} className="flex gap-2 items-center" data-testid={`dept-threshold-${i}`}>
                  <input type="number" min="0" value={t.threshold} onChange={(e) => setThreshold(i, { threshold: e.target.value })}
                    placeholder="Budget over (USD)"
                    className="w-40 h-9 px-2 border border-input font-mono focus:border-primary focus:outline-none" />
                  <span className="text-xs text-muted-foreground">→</span>
                  <select value={t.level} onChange={(e) => setThreshold(i, { level: e.target.value })}
                    className="flex-1 h-9 px-2 border border-input bg-white focus:border-primary focus:outline-none">
                    {LEVELS.map((L) => <option key={L.value} value={L.value}>{L.label}</option>)}
                  </select>
                  <button type="button" onClick={() => removeThreshold(i)} className="text-destructive p-1"><Trash2 className="h-4 w-4" /></button>
                </div>
              ))}
              <button type="button" onClick={addThreshold} data-testid="dept-add-threshold"
                className="text-xs border border-dashed border-primary text-primary px-3 py-1.5 hover:bg-primary/5 flex items-center gap-1">
                <Plus className="h-3 w-3" /> Add threshold
              </button>
            </div>
            <button data-testid="dept-create-btn" disabled={creatingDept} className="text-sm bg-primary text-white px-4 py-2 disabled:opacity-60 hover:-translate-y-0.5 transition-transform">
              {creatingDept ? "Creating..." : "Create department"}
            </button>
          </form>

          <div className="mt-4 border" data-testid="departments-list">
            <table className="w-full text-sm">
              <thead className="bg-muted/30"><tr><th className="pmc-label text-left px-3 py-2">Org</th><th className="pmc-label text-left px-3 py-2">Name</th><th className="pmc-label text-left px-3 py-2">Thresholds</th></tr></thead>
              <tbody>
                {departments.map((d) => (
                  <tr key={d.id} className="border-b" data-testid={`dept-row-${d.id}`}>
                    <td className="px-3 py-2 font-mono text-xs">{(orgMap[d.org_id] || {}).code || d.org_id.slice(0, 6)}</td>
                    <td className="px-3 py-2">{d.name} <span className="text-xs text-muted-foreground font-mono">({d.code})</span></td>
                    <td className="px-3 py-2 text-xs font-mono">
                      {(d.approval_thresholds || []).map((t, i) => (
                        <div key={i}>{t.threshold ? `≥ ${Number(t.threshold).toLocaleString()}` : "any"} → {t.level.replace("_", " ")}</div>
                      ))}
                      {(d.approval_thresholds || []).length === 0 && <span className="text-muted-foreground">—</span>}
                    </td>
                  </tr>
                ))}
                {departments.length === 0 && <tr><td colSpan={3} className="px-3 py-6 text-center text-muted-foreground">No departments yet.</td></tr>}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </DashboardLayout>
  );
}
