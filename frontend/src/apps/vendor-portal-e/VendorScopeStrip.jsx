import { useEffect, useState } from "react";
import { vendorTenderApi } from "@/lib/api";

export const VendorScopeStrip = () => {
  const [s, setS] = useState(null);
  useEffect(() => { vendorTenderApi.scope().then(setS).catch(() => {}); }, []);
  if (!s) return null;
  const { rules, approved_categories: cats, pending_tenders: pt } = s;
  return (
    <div className="pmc-panel" data-testid="vendor-scope-strip"
         style={{ padding: "10px 16px", marginBottom: "14px", fontSize: "13px" }}>
      <div className="pmc-eyebrow" style={{ marginBottom: "4px" }}>Your tender scope</div>
      {rules.restrict_to_approved_categories && (
        <div data-testid="vendor-scope-categories">
          Product Category must be one you're approved for:{" "}
          <b>{cats.length ? cats.join(", ") : "none yet — request one under My categories"}</b>
        </div>
      )}
      {rules.max_pending_tenders > 0 && (
        <div className="pmc-muted" data-testid="vendor-scope-pending" style={{ marginTop: "2px" }}>
          Awaiting review: {pt} of {rules.max_pending_tenders} allowed at a time
        </div>
      )}
    </div>
  );
};
