import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { BidOpeningPanel } from "../admin-console/bidding/BidOpeningPanel";

export const OpenCommitteesOpening = () => {
  const [refs, setRefs] = useState([]);
  useEffect(() => {
    api.get("/api/v1/committees").then((r) => setRefs((r.data || []).filter((c) => c.status === "open").map((c) => c.notice_ref))).catch(() => setRefs([]));
  }, []);
  if (!refs.length) return null;
  return (
    <section className="pmc-panel" data-testid="bo-opening-section">
      <div className="pmc-panel__head"><h2 className="pmc-panel__title">Bid opening</h2></div>
      <div className="pmc-panel__body" style={{ display: "grid", gap: "10px" }}>
        {refs.map((r) => <BidOpeningPanel key={r} noticeRef={r} />)}
      </div>
    </section>
  );
};
