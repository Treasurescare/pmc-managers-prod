import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { docusignApi, bidApi, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";

/** Wave 43 — DocuSign eSignature admin panel.
 *
 * Shows JWT consent status, lets admin trigger an embedded signing ceremony on
 * any Award PDF (PO/SLA/Contract) or on a Bid acknowledgement, and lists all
 * envelopes with live status. */
export default function DocuSignPanel() {
  const { t } = useI18n();
  const [status, setStatus] = useState(null);
  const [envelopes, setEnvelopes] = useState([]);
  const [awardedBids, setAwardedBids] = useState([]);
  const [pickedBidId, setPickedBidId] = useState("");
  const [kind, setKind] = useState("contract");
  const [signerName, setSignerName] = useState("");
  const [signerEmail, setSignerEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [signingUrl, setSigningUrl] = useState("");

  const load = useCallback(async () => {
    try {
      const [s, e, b] = await Promise.all([
        docusignApi.status(),
        docusignApi.listEnvelopes().catch(() => ({ items: [] })),
        bidApi.listAll({ status: "awarded" }).catch(() => []),
      ]);
      setStatus(s); setEnvelopes(e.items || []);
      setAwardedBids(b || []);
      if (!pickedBidId && b?.length) setPickedBidId(b[0].id);
    } catch (err) { toast.error(formatApiError(err)); }
  }, [pickedBidId]);

  useEffect(() => { load(); }, [load]);

  const openConsent = () => {
    if (status?.consent_url) window.open(status.consent_url, "_blank", "noopener");
  };

  const sign = async () => {
    if (!pickedBidId) return toast.error(t("panels.docusign.pick_bid"));
    if (!signerName || !signerEmail) return toast.error(t("panels.docusign.signer_required"));
    setBusy(true);
    try {
      const r = await docusignApi.signAward(pickedBidId, kind, {
        signer_name: signerName,
        signer_email: signerEmail,
      });
      setSigningUrl(r.signing_url);
      toast.success(t("panels.docusign.envelope_sent"));
      load();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      if (detail?.code === "DOCUSIGN_CONSENT_REQUIRED" && detail.consent_url) {
        window.open(detail.consent_url, "_blank", "noopener");
        toast.error(t("panels.docusign.consent_required"));
      } else {
        toast.error(formatApiError(err));
      }
    } finally { setBusy(false); }
  };

  const statusChip = (s) => {
    const clsMap = {
      sent: "bg-blue-50 text-blue-800 border-blue-200",
      delivered: "bg-indigo-50 text-indigo-800 border-indigo-200",
      completed: "bg-emerald-50 text-emerald-800 border-emerald-200",
      declined: "bg-red-50 text-red-800 border-red-200",
      voided: "bg-slate-100 text-slate-700 border-slate-200",
    };
    return <span className={`text-[10px] uppercase tracking-widest border px-2 py-1 ${clsMap[s] || "bg-slate-50 border-slate-200"}`}>{s}</span>;
  };

  return (
    <div data-testid="admin-docusign-panel" className="space-y-6">
      <section>
        <div className="pmc-label">{t("panels.docusign.kicker")}</div>
        <h2 className="font-display text-2xl text-brand-navy mt-1">{t("panels.docusign.heading")}</h2>
        <p className="text-sm text-brand-navy/60 mt-2 max-w-2xl">{t("panels.docusign.subhead")}</p>
      </section>

      <section className="border border-brand-navy/10 bg-white p-5 flex items-start justify-between flex-wrap gap-4"
               data-testid="ds-status-card">
        <div>
          <div className="pmc-label">{t("panels.docusign.status_title")}</div>
          <div className="mt-2 text-sm text-brand-navy space-y-1">
            <div>{t("panels.docusign.env")}: <strong>{status?.env || "…"}</strong></div>
            <div>{t("panels.docusign.configured")}: <strong>{status?.configured ? "✓" : "✗"}</strong></div>
            <div>{t("panels.docusign.consent")}: {status?.consent_ok
                ? <strong className="text-emerald-700">✓ {t("panels.docusign.granted")}</strong>
                : <strong className="text-amber-700">⚠ {t("panels.docusign.needed")}</strong>}</div>
            <div>{t("panels.docusign.account")}: <code className="text-xs">{status?.account_id || "—"}</code></div>
          </div>
        </div>
        {status && !status.consent_ok && status.consent_url && (
          <button type="button" onClick={openConsent} data-testid="ds-consent-btn"
            className="px-5 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
            {t("panels.docusign.grant_consent")}
          </button>
        )}
      </section>

      <section className="border border-brand-navy/10 bg-white p-5" data-testid="ds-request-form">
        <div className="pmc-label mb-3">{t("panels.docusign.request_sig_title")}</div>
        <div className="grid gap-3 md:grid-cols-2">
          <label><span className="pmc-label">{t("panels.docusign.awarded_bid")}</span>
            <select value={pickedBidId} onChange={(e) => setPickedBidId(e.target.value)}
              data-testid="ds-bid-picker"
              className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white">
              {awardedBids.length === 0 && <option value="">{t("panels.docusign.no_awarded")}</option>}
              {awardedBids.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.bid_ref} · {b.company_name || b.vendor_email}
                </option>
              ))}
            </select>
          </label>
          <label><span className="pmc-label">{t("panels.docusign.document")}</span>
            <select value={kind} onChange={(e) => setKind(e.target.value)}
              data-testid="ds-kind-picker"
              className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white">
              <option value="po">{t("panels.awards.po_title")}</option>
              <option value="sla">{t("panels.awards.sla_title")}</option>
              <option value="contract">{t("panels.awards.contract_title")}</option>
            </select>
          </label>
          <label><span className="pmc-label">{t("panels.docusign.signer_name")}</span>
            <input value={signerName} onChange={(e) => setSignerName(e.target.value)}
              data-testid="ds-signer-name"
              className="mt-1 w-full px-3 py-2 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">{t("panels.docusign.signer_email")}</span>
            <input type="email" value={signerEmail} onChange={(e) => setSignerEmail(e.target.value)}
              data-testid="ds-signer-email"
              className="mt-1 w-full px-3 py-2 border border-brand-navy/20" /></label>
        </div>
        <div className="mt-4 flex justify-end">
          <button type="button" onClick={sign} disabled={busy || !pickedBidId}
            data-testid="ds-send-envelope"
            className="px-6 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90 disabled:opacity-50">
            {busy ? t("panels.docusign.sending") : t("panels.docusign.send_envelope")}
          </button>
        </div>
        {signingUrl && (
          <div className="mt-4 border border-emerald-500 bg-emerald-50 p-3 text-sm" data-testid="ds-signing-url">
            <div className="text-emerald-800 font-semibold">{t("panels.docusign.signing_link_ready")}</div>
            <a href={signingUrl} target="_blank" rel="noreferrer"
              className="text-emerald-900 underline break-all text-xs mt-1 inline-block">
              {signingUrl}
            </a>
            <div className="text-[10px] text-emerald-700/70 mt-1">{t("panels.docusign.link_expires")}</div>
          </div>
        )}
      </section>

      <section className="border border-brand-navy/10 bg-white overflow-x-auto"
               data-testid="ds-envelope-list">
        <div className="pmc-label p-3 border-b border-brand-navy/10">
          {t("panels.docusign.envelopes")} · {envelopes.length}
        </div>
        <table className="w-full text-sm">
          <thead className="text-xs text-brand-navy/60 bg-brand-navy/5">
            <tr>
              <th className="text-left px-3 py-2">{t("panels.docusign.col_kind")}</th>
              <th className="text-left px-3 py-2">{t("panels.docusign.col_ref")}</th>
              <th className="text-left px-3 py-2">{t("panels.docusign.col_signer")}</th>
              <th className="text-left px-3 py-2">{t("panels.docusign.col_status")}</th>
              <th className="text-left px-3 py-2">{t("panels.docusign.col_created")}</th>
            </tr>
          </thead>
          <tbody>
            {envelopes.map((e) => (
              <tr key={e.envelope_id} className="border-t border-brand-navy/10"
                  data-testid={`ds-envelope-${e.envelope_id}`}>
                <td className="px-3 py-2">
                  {e.kind === "award" ? `${e.sub_kind?.toUpperCase() || "AWARD"}` : "BID ACK"}
                </td>
                <td className="px-3 py-2 font-mono text-xs">{e.award_ref || e.bid_ref}</td>
                <td className="px-3 py-2 text-xs">{e.signer_name}<br /><span className="text-brand-navy/50">{e.signer_email}</span></td>
                <td className="px-3 py-2">{statusChip(e.status)}</td>
                <td className="px-3 py-2 text-xs">{e.created_at?.slice(0, 16).replace("T", " ")}</td>
              </tr>
            ))}
            {envelopes.length === 0 && (
              <tr><td colSpan={5} className="p-6 text-center text-brand-navy/50">
                {t("panels.docusign.empty")}
              </td></tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
