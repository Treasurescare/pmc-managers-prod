import { useEffect, useState } from "react";
import { api } from "@/lib/api";

/**
 * EscrowInstitutionsKPI — v51ao. Needs-attention tile that pings whenever an
 * escrow institution registration is sitting unreviewed. Hidden when the
 * queue is empty.
 */
export default function EscrowInstitutionsKPI() {
  const [count, setCount] = useState(0);
  useEffect(() => {
    api.get("/api/v1/escrow-institutions", { params: { status: "submitted" } })
      .then((r) => setCount(r.data?.total || 0))
      .catch(() => setCount(0));
  }, []);
  if (!count) return null;
  return (
    <a href="/admin/e/escrow-institutions"
       data-testid="dash-attn-escrow-insts">
      <span>
        <span className="n" data-attn="escrow-insts">{count}</span>
        {" "}escrow institution{count === 1 ? "" : "s"} awaiting review
      </span>
      <span className="arr" aria-hidden="true">→</span>
    </a>
  );
}
