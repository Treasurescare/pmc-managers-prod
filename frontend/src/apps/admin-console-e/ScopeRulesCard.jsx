import { useEffect, useState } from "react";
import { toast } from "sonner";
import { vendorTenderApi, showApiError } from "@/lib/api";

export const ScopeRulesCard = () => {
  const [r, setR] = useState(null);
  useEffect(() => { vendorTenderApi.getScopeRules().then(setR).catch(() => {}); }, []);
  if (!r) return null;
  const save = async () => {
    try { setR(await vendorTenderApi.setScopeRules(r)); toast.success("Vendor scope rules saved"); }
    catch (e) { showApiError(e); }
  };
  const num = (k) => (
    <input type="number" min={0} max={100} value={r[k]} data-testid={`scope-${k}`}
           onChange={(e) => setR({ ...r, [k]: Number(e.target.value) })}
           style={{ width: "70px", marginLeft: "6px", padding: "4px 6px", border: "1px solid var(--line)" }} />
  );
  return (
    <div className="pmc-panel" data-testid="scope-rules-card" style={{ padding: "12px 16px", marginBottom: "16px", fontSize: "13px", display: "flex", gap: "18px", flexWrap: "wrap", alignItems: "center" }}>
      <b>Vendor scope rules</b>
      <label><input type="checkbox" checked={r.restrict_to_approved_categories} data-testid="scope-restrict-categories"
                    onChange={(e) => setR({ ...r, restrict_to_approved_categories: e.target.checked })} /> Only approved categories</label>
      <label>Max tenders awaiting review{num("max_pending_tenders")}</label>
      <label>Max pending category requests{num("max_pending_category_requests")}</label>
      <span className="pmc-muted" style={{ fontSize: "11px" }}>0 = no limit</span>
      <button className="pmc-btn pmc-btn--sm pmc-btn--primary" data-testid="scope-save" onClick={save}>Save</button>
    </div>
  );
};
