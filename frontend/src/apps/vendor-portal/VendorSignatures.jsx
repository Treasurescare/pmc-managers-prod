import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { docusignApi, bidApi, formatApiError } from "@/lib/api";

/** Wave 44 — Vendor Signing Dashboard.
 *
 * Lists the vendor's own awarded bids that have PO/SLA/Contract PDFs waiting
 * for signature. Vendor can trigger an embedded DocuSign signing ceremony on
 * any of them — the backend guards ownership + awarded status. Envelope log
 * shows live status; refresh happens automatically after signing.
 */
export default function VendorSignatures() {
  const [awarded, setAwarded] = useState([]);
  const [envelopes, setEnvelopes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [signingUrl, setSigningUrl] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const bids = await bidApi.mine();
      setAwarded((bids || []).filter((b) => b.status === "awarded"));
      const env = await docusignApi.listMine().catch(() => ({ items: [] }));
      setEnvelopes(env.items || []);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // If DocuSign redirected back to us with ?ds_signed=1, refresh the list.
  useEffect(() => {
    const u = new URL(window.location.href);
    if (u.searchParams.get("ds_signed") === "1") {
      toast.success("Signature recorded — refreshing envelopes");
      u.searchParams.delete("ds_signed");
      window.history.replaceState({}, "", u.toString());
      load();
    }
  }, [load]);

  const signKind = async (bid, kind) => {
    const key = `${bid.id}:${kind}`;
    setBusy(key);
    setSigningUrl("");
    try {
      const r = await docusignApi.vendorSignAward(bid.id, kind, {
        signer_name: bid.company_name || bid.vendor_email,
        signer_email: bid.vendor_email,
      });
      setSigningUrl(r.signing_url);
      // Open in a popup — vendor can also click the button below.
      window.open(r.signing_url, "_blank", "noopener,noreferrer,width=1100,height=800");
      toast.success("Signing session ready");
      load();
    } catch (e) {
      const d = e?.response?.data?.detail;
      if (d?.code === "DOCUSIGN_CONSENT_REQUIRED") {
        toast.error("DocuSign consent not granted — contact admin");
      } else {
        toast.error(formatApiError(e));
      }
    } finally {
      setBusy("");
    }
  };

  const statusPill = (s) => {
    const cls = {
      sent: "bg-blue-50 text-blue-800 border-blue-200",
      delivered: "bg-indigo-50 text-indigo-800 border-indigo-200",
      completed: "bg-emerald-50 text-emerald-900 border-emerald-200",
      declined: "bg-red-50 text-red-800 border-red-200",
      voided: "bg-slate-100 text-slate-700 border-slate-200",
    }[s] || "bg-slate-50 text-slate-600 border-slate-200";
    return (
      <span className={`text-[10px] uppercase tracking-widest border px-2 py-1 ${cls}`}>{s || "—"}</span>
    );
  };

  // Group envelopes by bid so we can show status on the doc buttons.
  const envMap = {};
  envelopes.forEach((e) => {
    if (e.bid_id && e.sub_kind) envMap[`${e.bid_id}:${e.sub_kind}`] = e;
  });

  return (
    <div className="space-y-6" data-testid="vendor-signatures">
      <section>
        <div className="text-xs tracking-widest uppercase text-slate-500">eSignature</div>
        <h2 className="font-serif text-2xl text-slate-900 mt-1">Documents awaiting your signature</h2>
        <p className="text-sm text-slate-600 mt-1 max-w-2xl">
          Once your bid is awarded, PMC auto-drafts your Purchase Order, SLA, and Contract.
          Click <em>Sign now</em> on any document — you'll be redirected to DocuSign to
          e-sign in the browser. Progress updates automatically when you're done.
        </p>
      </section>

      {loading ? (
        <div className="text-slate-500 py-10 text-center">Loading…</div>
      ) : awarded.length === 0 ? (
        <div className="bg-white border rounded-lg p-8 text-center text-slate-500 text-sm"
             data-testid="vendor-signatures-empty">
          You don't have any awarded bids yet. Once PMC awards a bid to you, PO/SLA/Contract
          documents will appear here for you to e-sign.
        </div>
      ) : (
        <div className="space-y-4" data-testid="vendor-signatures-list">
          {awarded.map((b) => (
            <div key={b.id} className="bg-white border rounded-lg p-5"
                 data-testid={`vendor-award-card-${b.bid_ref}`}>
              <div className="flex flex-wrap items-baseline justify-between gap-3">
                <div>
                  <div className="text-xs text-slate-500">{b.bid_ref} · {b.notice_ref}</div>
                  <div className="font-serif text-lg text-slate-900 mt-0.5">
                    Awarded contract · {b.price_currency} {(b.price_amount || 0).toLocaleString()}
                  </div>
                </div>
                <span className="text-[10px] uppercase tracking-widest border border-emerald-300 bg-emerald-50 text-emerald-900 px-2 py-1">
                  Awarded
                </span>
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-3">
                {[
                  ["po", "Purchase Order"],
                  ["sla", "Service Level Agreement"],
                  ["contract", "Contract / LOA"],
                ].map(([kind, label]) => {
                  const env = envMap[`${b.id}:${kind}`];
                  const busyKey = `${b.id}:${kind}`;
                  const signed = env?.status === "completed";
                  return (
                    <div key={kind} className="border rounded p-3"
                         data-testid={`vendor-doc-${b.bid_ref}-${kind}`}>
                      <div className="text-xs text-slate-500 uppercase tracking-widest">{label}</div>
                      <div className="mt-2 flex items-center justify-between">
                        {env ? statusPill(env.status)
                             : <span className="text-[10px] uppercase tracking-widest text-slate-400">Not sent</span>}
                        {signed ? (
                          <span className="text-[10px] text-emerald-800 font-semibold">✓ Signed</span>
                        ) : (
                          <button
                            type="button"
                            onClick={() => signKind(b, kind)}
                            disabled={busy === busyKey}
                            data-testid={`vendor-sign-${b.bid_ref}-${kind}`}
                            className="text-[10px] uppercase tracking-widest px-3 py-1.5 bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-50"
                          >
                            {busy === busyKey ? "…" : env ? "Resume" : "Sign now"}
                          </button>
                        )}
                      </div>
                      {env?.updated_at && (
                        <div className="mt-1 text-[10px] text-slate-500">
                          Updated {env.updated_at.slice(0, 16).replace("T", " ")}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      {signingUrl && (
        <div className="border border-emerald-500 bg-emerald-50 p-3 text-sm"
             data-testid="vendor-signing-url-card">
          <div className="text-emerald-800 font-semibold">Signing session opened in a new tab.</div>
          <a href={signingUrl} target="_blank" rel="noreferrer"
             className="text-emerald-900 underline break-all text-xs mt-1 inline-block">
            Popup blocked? Click here to sign
          </a>
          <div className="text-[10px] text-emerald-700/70 mt-1">
            The link expires in ~5 minutes; click Sign now again to refresh.
          </div>
        </div>
      )}

      <section className="bg-white border rounded-lg p-5" data-testid="vendor-envelopes-log">
        <div className="text-xs tracking-widest uppercase text-slate-500 mb-2">
          Envelope history · {envelopes.length}
        </div>
        {envelopes.length === 0 ? (
          <div className="text-sm text-slate-500">No envelopes yet.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-xs text-slate-500">
              <tr>
                <th className="text-left py-1">Ref</th>
                <th className="text-left py-1">Doc</th>
                <th className="text-left py-1">Status</th>
                <th className="text-left py-1">Created</th>
              </tr>
            </thead>
            <tbody>
              {envelopes.map((e) => (
                <tr key={e.envelope_id} className="border-t"
                    data-testid={`vendor-envelope-${e.envelope_id}`}>
                  <td className="py-2 font-mono text-xs">{e.award_ref || e.bid_ref || "—"}</td>
                  <td className="py-2 text-xs">{(e.sub_kind || e.kind || "").toUpperCase()}</td>
                  <td className="py-2">{statusPill(e.status)}</td>
                  <td className="py-2 text-xs text-slate-500">
                    {(e.created_at || "").slice(0, 16).replace("T", " ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
