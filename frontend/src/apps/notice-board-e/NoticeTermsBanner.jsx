import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export const useNoticeTerms = (ref) => {
  const [t, setT] = useState(null);
  useEffect(() => { if (ref) { api.get(`/api/v1/notice-terms/${ref}`).then((r) => setT(r.data)).catch(() => setT(null)); } }, [ref]);
  return t;
};

export const NoticeTermsBanner = ({ noticeRef }) => {
  const t = useNoticeTerms(noticeRef);
  if (!t) return null;
  if (t.public_tender) {
    return (<div className="text-sm px-4 py-2 border border-emerald-300 bg-emerald-50 text-emerald-900" data-testid="notice-terms-public">
      Public tender: open to every verified supplier, and no fee is charged to the winning supplier.</div>);
  }
  if (!t.winner_fee_enabled) return null;
  return (<div className="text-sm px-4 py-2 border border-amber-300 bg-amber-50 text-amber-900" data-testid="notice-terms-winner-fee">
    Private tender: the buyer has chosen a {Number(t.winner_fee_pct).toFixed(2)}% service charge on the awarded value, payable by the winning bidder. Please include it in your price.</div>);
};
