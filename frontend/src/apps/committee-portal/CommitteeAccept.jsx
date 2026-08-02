import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";

/**
 * External committee invite accept/decline landing page.
 * URL: /committee/accept/:token
 */
export default function CommitteeAccept() {
  const { token } = useParams();
  const [meta, setMeta] = useState(null);
  const [decision, setDecision] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get(`/api/v1/committees/external/${token}`)
      .then((r) => setMeta(r.data))
      .catch((e) => setError(formatApiError(e)));
  }, [token]);

  const submit = async (dec) => {
    setBusy(true);
    try {
      const r = await api.post(`/api/v1/committees/external/${token}/decision`, { decision: dec });
      setDecision(r.data.decision);
      toast.success(`Invitation ${dec}`);
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-6">
        <div className="max-w-md w-full bg-white border rounded-lg p-8 text-center">
          <h1 className="font-serif text-2xl text-red-700">Invitation invalid or expired</h1>
          <p className="text-sm text-slate-600 mt-3">{error}</p>
        </div>
      </div>
    );
  }
  if (!meta) return <div className="p-10 text-slate-500">Loading invitation…</div>;

  if (decision) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-6"
           data-testid="committee-accept-result">
        <div className="max-w-md w-full bg-white border rounded-lg p-8 text-center">
          <h1 className={"font-serif text-2xl " + (decision === "accepted" ? "text-emerald-700" : "text-slate-700")}>
            Invitation {decision}
          </h1>
          <p className="text-sm text-slate-600 mt-3">
            Thank you. The procurement team has been notified. You may close this window.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-6"
         data-testid="committee-accept-page">
      <div className="max-w-lg w-full bg-white border rounded-lg p-8 space-y-4">
        <div className="pmc-label">Committee invitation</div>
        <h1 className="font-serif text-2xl">{meta.tender_title || "Bid evaluation committee"}</h1>
        <table className="w-full text-sm">
          <tbody>
            <tr><td className="pr-3 py-1 text-slate-500">Tender Ref</td><td className="font-mono">{meta.notice_ref}</td></tr>
            <tr><td className="pr-3 py-1 text-slate-500">Budget</td><td>{meta.budget_currency} {(meta.budget_amount || 0).toLocaleString()}</td></tr>
            <tr><td className="pr-3 py-1 text-slate-500">Deadline</td><td>{(meta.submission_deadline || "").slice(0, 10)}</td></tr>
            <tr><td className="pr-3 py-1 text-slate-500">Invitee</td><td>{meta.invitee?.name} · {meta.invitee?.designation || "External"}</td></tr>
          </tbody>
        </table>
        <p className="text-sm text-slate-600">
          You've been invited to serve on this evaluation committee. Your acceptance authorises
          the procurement team to include you in bid reviews for this tender.
        </p>
        <div className="flex gap-3 pt-2">
          <button onClick={() => submit("declined")} disabled={busy}
                  data-testid="committee-decline"
                  className="flex-1 border px-4 py-3 text-sm rounded">Decline</button>
          <button onClick={() => submit("accepted")} disabled={busy}
                  data-testid="committee-accept"
                  className="flex-1 bg-emerald-600 text-white px-4 py-3 text-sm rounded hover:bg-emerald-700 disabled:opacity-50">
            Accept invitation
          </button>
        </div>
      </div>
    </div>
  );
}
