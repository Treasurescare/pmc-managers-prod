import { useEffect, useState } from "react";
import { toast } from "sonner";
import { criteriaApi, showApiError } from "@/lib/api";

export const ResultNoticesPanel = ({ noticeRef }) => {
  const [items, setItems] = useState(null);
  const [canResend, setCanResend] = useState(false);
  const load = () => criteriaApi.resultNotices(noticeRef).then((r) => { setItems(r.items || []); setCanResend(!!r.can_resend); }).catch(() => setItems([]));
  useEffect(() => { load(); }, [noticeRef]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!items || !items.length) return null;
  const resend = async (b, n, e) => {
    try {
      const r = await criteriaApi.resendNotice(noticeRef, { bid_id: b.bid_id, idx: n.idx, email: e.to });
      r.ok ? toast.success(`Re-sent to ${e.to}`) : toast.error(r.error, { duration: 12000 });
    }
    catch (err) { showApiError(err); }
    load();
  };
  const failed = items.reduce((s, b) => s + b.notices.reduce((t, n) => t + n.emails.filter((e) => !e.sent).length, 0), 0);
  return (
    <div className="space-y-2" data-testid={`result-notices-${noticeRef}`}>
      <div className="flex justify-between items-center"><div className="pmc-label">Result notices to suppliers · {failed ? `${failed} email(s) not delivered` : "all emails sent"}</div>
        <button type="button" className="text-xs underline" onClick={load} data-testid={`rn-refresh-${noticeRef}`}>Refresh</button></div>
      <table className="w-full text-xs bg-white border"><thead><tr className="text-left"><th className="p-2">Bid</th><th>Notice</th><th>Recipient</th><th>Email</th><th /></tr></thead>
        <tbody>{items.flatMap((b) => b.notices.flatMap((n) => n.emails.map((e) => (
          <tr key={`${b.bid_id}-${n.idx}-${e.to}`} className="border-t" data-testid={`rn-row-${b.bid_ref}-${n.idx}-${e.to}`}>
            <td className="p-2">{b.bid_ref}<div className="text-brand-navy/60">{b.consortium ? `consortium ${b.consortium}` : b.company}</div></td>
            <td>{n.kind === "final" ? "Final" : "Preliminary"}<div className="text-brand-navy/60">{(n.at || "").slice(0, 16).replace("T", " ")}</div></td>
            <td>{e.to}</td>
            <td className={e.sent ? "text-emerald-800" : "text-red-700"} data-testid={`rn-status-${b.bid_ref}-${n.idx}-${e.to}`}>{e.sent ? "Sent" : "Not delivered"}{e.resend_count ? ` · re-sent ${e.resend_count}×` : ""}{e.last_error ? <div>{e.last_error}</div> : null}</td>
            <td className="text-right pr-2">{canResend && n.can_resend && <button type="button" className="pmc-btn pmc-btn--secondary" onClick={() => resend(b, n, e)} data-testid={`rn-resend-${b.bid_ref}-${n.idx}-${e.to}`}>{e.sent ? "Send again" : "Re-send"}</button>}</td>
          </tr>))))}</tbody></table>
    </div>);
};
