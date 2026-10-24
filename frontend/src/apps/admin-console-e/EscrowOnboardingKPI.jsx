import { useEffect, useState } from "react";
import { api } from "@/lib/api";

// v56v — dashboard attention chips: escrow institutions awaiting review +
// new escrow accounts onboarded this month. Always shown (0 is informative).
export default function EscrowOnboardingKPI() {
  const [s, setS] = useState(null);
  useEffect(() => {
    api.get("/api/v1/escrow-institutions/admin/onboarding-stats")
      .then((r) => setS(r.data))
      .catch(() => setS(null));
  }, []);
  if (!s) return null;
  return (
    <>
      <a href="/admin/e/escrow-institutions" data-testid="dash-attn-escrow-insts">
        <span><span className="n" data-attn="escrow-insts">{s.awaiting_review}</span> escrow institutions awaiting review</span>
        <span className="arr" aria-hidden="true">→</span>
      </a>
      <a href="/admin/e/escrow" data-testid="dash-attn-escrow-accts">
        <span><span className="n" data-attn="escrow-accts">{s.accounts_this_month}</span> new escrow accounts this month</span>
        <span className="arr" aria-hidden="true">→</span>
      </a>
    </>
  );
}
