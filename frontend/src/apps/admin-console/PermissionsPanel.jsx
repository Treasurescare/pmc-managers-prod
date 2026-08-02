import { useEffect, useState } from "react";
import { toast } from "sonner";
import { permissionsApi, formatApiError } from "@/lib/api";

const ACTIONS = ["view", "create", "modify", "delete", "publish"];
const DOC_TYPES = [
  { code: "*", label: "All types" },
  { code: "tender", label: "Tender" },
  { code: "rfp", label: "RFP" },
  { code: "rfq", label: "RFQ" },
];
const ROLE_LABELS = {
  admin: "Admin (master)", reviewer: "Reviewer",
  escrow_agent: "Escrow Agent", certifier: "Certifier",
  legal_counsel: "Legal Counsel", accounting: "Accounting",
  committee_member: "Committee Member", auditor: "Auditor",
  support: "Support",
};

export default function PermissionsPanel() {
  const [rows, setRows] = useState([]);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    try {
      const r = await permissionsApi.get();
      setRows(r.rows || []);
    } catch (e) { toast.error(formatApiError(e)); }
  };
  useEffect(() => { load(); }, []);

  const toggle = (i, action) => {
    const copy = [...rows];
    copy[i] = { ...copy[i], [action]: !copy[i][action] };
    setRows(copy);
  };

  const updateDocType = (i, docType) => {
    const copy = [...rows];
    copy[i] = { ...copy[i], document_type: docType };
    setRows(copy);
  };

  const save = async () => {
    setSaving(true);
    try {
      await permissionsApi.put(rows);
      toast.success("Permissions saved");
      await load();
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setSaving(false); }
  };

  const reset = async () => {
    if (!confirm("Reset to default matrix? Custom rules will be lost.")) return;
    try {
      await permissionsApi.reset();
      toast.success("Reset to defaults");
      await load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div data-testid="admin-permissions-panel">
      <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
        <div className="text-sm text-brand-navy/70">
          Permission Matrix — controls who can view / create / modify / delete / publish tenders, RFPs and RFQs
        </div>
        <div className="flex gap-2">
          <button onClick={reset} data-testid="perm-reset"
                  className="px-4 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5">
            Reset defaults
          </button>
          <button onClick={save} disabled={saving} data-testid="perm-save"
                  className="px-5 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-50">
            {saving ? "Saving…" : "Save matrix"}
          </button>
        </div>
      </div>

      <div className="border border-brand-navy/10 bg-white overflow-x-auto" data-testid="perm-table">
        <table className="w-full text-sm">
          <thead className="text-left text-brand-navy/60 text-xs uppercase tracking-wider bg-brand-navy/5">
            <tr>
              <th className="px-3 py-2">Role</th>
              <th className="px-3 py-2">Doc type</th>
              {ACTIONS.map((a) => (
                <th key={a} className="px-3 py-2 text-center capitalize">{a}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={`${r.role}-${i}`} className="border-t border-brand-navy/10"
                  data-testid={`perm-row-${r.role}`}>
                <td className="px-3 py-2 font-semibold">
                  {ROLE_LABELS[r.role] || r.role}
                  {r.role === "admin" && (
                    <div className="text-[10px] text-brand-navy/40 mt-0.5">(overrides — always allowed)</div>
                  )}
                </td>
                <td className="px-3 py-2">
                  <select value={r.document_type}
                          onChange={(e) => updateDocType(i, e.target.value)}
                          data-testid={`perm-doctype-${r.role}`}
                          disabled={r.role === "admin"}
                          className="text-xs border border-brand-navy/20 px-2 py-1">
                    {DOC_TYPES.map((d) => (
                      <option key={d.code} value={d.code}>{d.label}</option>
                    ))}
                  </select>
                </td>
                {ACTIONS.map((a) => (
                  <td key={a} className="px-3 py-2 text-center">
                    <input type="checkbox" checked={!!r[a]}
                           disabled={r.role === "admin"}
                           onChange={() => toggle(i, a)}
                           data-testid={`perm-${r.role}-${a}`}
                           className="h-4 w-4" />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="text-[11px] text-brand-navy/50 mt-3 italic">
        Notes · Admin is always allowed regardless of the checkboxes. Any other role must have the box ticked
        to perform the action. The matrix is enforced server-side on every /notices endpoint.
      </div>
    </div>
  );
}
