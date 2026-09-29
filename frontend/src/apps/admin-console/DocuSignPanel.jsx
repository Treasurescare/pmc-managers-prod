import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { docusignApi, bidApi, formatApiError, showApiError} from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import { InfoDot } from "@/components/InfoDot";
import { useListPager } from "@/components/ListPager";

/** Wave 43 — DocuSign eSignature admin panel.
 *
 * Shows JWT consent status, lets admin trigger an embedded signing ceremony on
 * any Award PDF (PO/SLA/Contract) or on a Bid acknowledgement, and lists all
 * envelopes with live status.
 *
 * Wave 44 — adds a "Delivery mode" toggle so admins can pick either an
 * embedded (in-app) signing URL or ask DocuSign to email the signer directly.
 */
export default function DocuSignPanel() {
  const { t } = useI18n();
  const [status, setStatus] = useState(null);
  const [envelopes, setEnvelopes] = useState([]);
  const [awardedBids, setAwardedBids] = useState([]);
  const [pickedBidId, setPickedBidId] = useState("");
  const [kind, setKind] = useState("contract");
  const [signerName, setSignerName] = useState("");
  const [signerEmail, setSignerEmail] = useState("");
  const [delivery, setDelivery] = useState("embedded");
  const [busy, setBusy] = useState(false);
  const [signingUrl, setSigningUrl] = useState("");
  const [emailSent, setEmailSent] = useState(false);
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [viewEnv, setViewEnv] = useState(null);

  const filteredEnvelopes = envelopes.filter((e) => {
    const q = search.trim().toLowerCase();
    const matchStatus = statusFilter === "all" || e.status === statusFilter;
    const matchSearch = !q
      || (e.award_ref || "").toLowerCase().includes(q)
      || (e.bid_ref || "").toLowerCase().includes(q)
      || (e.signer_name || "").toLowerCase().includes(q)
      || (e.signer_email || "").toLowerCase().includes(q);
    return matchStatus && matchSearch;
  });
  const { paged: pagedEnvelopes, controls: envelopeControls } =
    useListPager(filteredEnvelopes, { defaultSize: 20, testid: "ds-pager" });

  const resendEnvelope = async (envelopeId) => {
    const env = envelopes.find((x) => x.envelope_id === envelopeId);
    if (env && ["completed", "voided", "rejected"].includes((env.status || "").toLowerCase())) {
      toast.error(`Cannot resend a ${env.status} envelope. Create a new one instead.`);
      return;
    }
    toast.info("Resending envelope…");
    // v49v — Safari blocks window.open after an await; open inside the
    // click gesture and steer once the API responds.
    const w = window.open("", "_blank");
    try {
      const r = await docusignApi.resendEnvelope(envelopeId);
      if (r.signing_url) {
        if (w) { try { w.location.href = r.signing_url; } catch (_) { window.location.href = r.signing_url; } }
        else window.location.href = r.signing_url;
        toast.success("New signing link opened");
      } else {
        try { w && w.close(); } catch (_) { /* ignore */ }
        toast.success(`Envelope resent to ${r.emailed_to || "signer"} via email`);
      }
      load();
    } catch (e) { try { w && w.close(); } catch (_) { /* ignore */ } showApiError(e); }
  };

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
    } catch (err) { showApiError(err); }
  }, [pickedBidId]);

  useEffect(() => { load(); }, [load]);

  const openConsent = () => {
    if (status?.consent_url) window.open(status.consent_url, "_blank", "noopener");
  };

  const sign = async () => {
    if (!pickedBidId) return toast.error(t("panels.docusign.pick_bid"));
    if (!signerName || !signerEmail) return toast.error(t("panels.docusign.signer_required"));
    setBusy(true);
    setSigningUrl(""); setEmailSent(false);
    // v49v — Safari blocks window.open after an await; open inside the
    // click gesture and steer once the signing/consent URL arrives.
    const w = window.open("", "_blank");
    try {
      const r = await docusignApi.signAward(pickedBidId, kind, {
        signer_name: signerName,
        signer_email: signerEmail,
        delivery,
      });
    if (r.signing_url) {
              setSigningUrl(r.signing_url);
              // Steer the pre-opened tab so the signer sees DocuSign immediately.
              if (w) { try { w.location.href = r.signing_url; } catch (_) { window.location.href = r.signing_url; } }
              else window.location.href = r.signing_url;
            }
      else { try { w && w.close(); } catch (_) { /* ignore */ } setEmailSent(true); }
      toast.success(t("panels.docusign.envelope_sent"));
      load();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      if (detail?.code === "DOCUSIGN_CONSENT_REQUIRED" && detail.consent_url) {
        if (w) { try { w.location.href = detail.consent_url; } catch (_) { window.location.href = detail.consent_url; } }
        else window.location.href = detail.consent_url;
        toast.error(t("panels.docusign.consent_required"));
      } else {
        try { w && w.close(); } catch (_) { /* ignore */ }
        showApiError(err);
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

  const deliveryChip = (d) => {
    const label = d === "email" ? "📧 email" : "🖥️ embedded";
    const cls = d === "email"
      ? "bg-blue-50 text-blue-800 border-blue-200"
      : "bg-purple-50 text-purple-800 border-purple-200";
    return <span className={`text-[10px] uppercase tracking-widest border px-2 py-1 ${cls}`}>{label}</span>;
  };

  const downloadSigned = async (envelope_id) => {
    try {
      const blob = await docusignApi.downloadPdf(envelope_id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `${envelope_id}-signed.pdf`;
      document.body.appendChild(a); a.click();
      setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 1000);
    } catch (err) {
      showApiError(err);
    }
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

        {/* Delivery mode toggle (Wave 44) */}
        <div className="mb-4" data-testid="ds-delivery-toggle">
          <div className="pmc-label mb-2">{t("panels.docusign.delivery_mode")}</div>
          <div className="grid gap-2 md:grid-cols-2">
            <label className={"border p-3 cursor-pointer text-sm " +
              (delivery === "embedded" ? "border-brand-navy bg-brand-navy/5" : "border-brand-navy/20 bg-white")}>
              <input type="radio" name="ds-delivery" checked={delivery === "embedded"}
                     onChange={() => setDelivery("embedded")}
                     data-testid="ds-delivery-embedded" className="mr-2" />
              <strong>{t("panels.docusign.delivery_embedded")}</strong>
            </label>
            <label className={"border p-3 cursor-pointer text-sm " +
              (delivery === "email" ? "border-brand-navy bg-brand-navy/5" : "border-brand-navy/20 bg-white")}>
              <input type="radio" name="ds-delivery" checked={delivery === "email"}
                     onChange={() => setDelivery("email")}
                     data-testid="ds-delivery-email" className="mr-2" />
              <strong>{t("panels.docusign.delivery_email")}</strong>
            </label>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <label><span className="pmc-label">{t("panels.docusign.awarded_bid")}<InfoDot tip="Only bids in the 'awarded' state appear here. Envelope is bound to this bid's Award reference." /></span>
            <select value={pickedBidId} onChange={(e) => setPickedBidId(e.target.value)}
              data-testid="ds-bid-picker"
              className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white">
              {awardedBids.length === 0 && <option value="">{t("panels.docusign.no_awarded")}</option>}
              {awardedBids.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.bid_ref} · {b.company_name || b.vendor_email}
                  {b.award_ref ? ` · ${b.award_ref}` : ""}
                </option>
              ))}
            </select>
          </label>
          <label><span className="pmc-label">{t("panels.docusign.document")}<InfoDot tip="Pick which award artefact to send. Each document type produces a separate DocuSign envelope." /></span>
            <select value={kind} onChange={(e) => setKind(e.target.value)}
              data-testid="ds-kind-picker"
              className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white">
              <option value="po">{t("panels.awards.po_title")}</option>
              <option value="sla">{t("panels.awards.sla_title")}</option>
              <option value="contract">{t("panels.awards.contract_title")}</option>
            </select>
          </label>
          <label><span className="pmc-label">{t("panels.docusign.signer_name")}<InfoDot tip="Full legal name of the signatory as it should appear on the executed PDF." /></span>
            <input value={signerName} onChange={(e) => setSignerName(e.target.value)}
              data-testid="ds-signer-name"
              className="mt-1 w-full px-3 py-2 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">{t("panels.docusign.signer_email")}<InfoDot tip="Email tied to the DocuSign envelope. Used for identity verification and delivery." /></span>
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
          <div className="mt-4 border border-emerald-500 bg-emerald-50 p-4 text-sm" data-testid="ds-signing-url">
            <div className="text-emerald-800 font-semibold mb-2">
              {t("panels.docusign.signing_link_ready")}
            </div>
            <div className="flex flex-wrap gap-2 mb-2">
              <button type="button"
                onClick={() => window.open(signingUrl, "_blank", "noopener")}
                data-testid="ds-open-signing-window"
                className="px-4 py-2 text-[11px] font-semibold uppercase tracking-widest bg-emerald-700 text-white hover:bg-emerald-800">
                🖥️ Open signing window
              </button>
              <button type="button"
                onClick={() => { navigator.clipboard.writeText(signingUrl); toast.success(t("panels.docusign.link_copied")); }}
                data-testid="ds-copy-signing-url"
                className="px-4 py-2 text-[11px] font-semibold uppercase tracking-widest border border-emerald-700 text-emerald-800 hover:bg-emerald-100">
                📋 Copy link
              </button>
            </div>
            <div className="text-[10px] text-emerald-700/70">{t("panels.docusign.link_expires")}</div>
          </div>
        )}
        {emailSent && (
          <div className="mt-4 border border-blue-500 bg-blue-50 p-3 text-sm" data-testid="ds-email-sent">
            <div className="text-blue-800 font-semibold">
              📧 {t("panels.docusign.envelope_sent")}
            </div>
            <div className="text-blue-900 text-xs mt-1">
              {t("panels.docusign.email_sent_hint")} <code className="font-mono">{signerEmail}</code>
            </div>
          </div>
        )}
      </section>

      <section className="border border-brand-navy/10 bg-white overflow-x-auto"
               data-testid="ds-envelope-list">
        <div className="p-3 border-b border-brand-navy/10 flex flex-wrap items-center gap-2">
          <div className="pmc-label">
            {t("panels.docusign.envelopes")} · {envelopes.length}
          </div>
          {[["all","All"],["sent","Sent"],["delivered","Waiting"],["completed","Signed"],["declined","Rejected"],["voided","Voided"]].map(([k,l]) => (
            <button key={k} type="button" onClick={() => setStatusFilter(k)}
              data-testid={`ds-filter-${k}`}
              className={`px-3 py-1 text-[10px] uppercase tracking-widest border ${
                statusFilter === k ? "bg-brand-navy text-white border-brand-navy"
                  : "border-brand-navy/20 text-brand-navy/70 hover:border-brand-navy"}`}>
              {l}
            </button>
          ))}
          <input value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by ref, signer, email…"
            data-testid="ds-search"
            className="flex-1 min-w-[200px] px-3 py-1.5 border border-brand-navy/20 text-sm bg-white" />
        </div>
        <table className="w-full text-sm">
          <thead className="text-xs text-brand-navy/60 bg-brand-navy/5">
            <tr>
              <th className="text-left px-3 py-2">{t("panels.docusign.col_kind")}</th>
              <th className="text-left px-3 py-2">{t("panels.docusign.col_ref")}</th>
              <th className="text-left px-3 py-2">{t("panels.docusign.col_signer")}</th>
              <th className="text-left px-3 py-2">Delivery</th>
              <th className="text-left px-3 py-2">{t("panels.docusign.col_status")}</th>
              <th className="text-left px-3 py-2">{t("panels.docusign.col_created")}</th>
              <th className="text-left px-3 py-2">PDF</th>
              <th className="text-left px-3 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredEnvelopes.length === 0 ? (
              <tr><td colSpan={8} className="p-6 text-center text-brand-navy/50">
                {envelopes.length === 0 ? t("panels.docusign.empty") : "No matches"}
              </td></tr>
            ) : pagedEnvelopes.map((e) => (
              <tr key={e.envelope_id} className="border-t border-brand-navy/10"
                  data-testid={`ds-envelope-${e.envelope_id}`}>
                <td className="px-3 py-2">
                  {e.kind === "award" ? `${e.sub_kind?.toUpperCase() || "AWARD"}` : "BID ACK"}
                </td>
                <td className="px-3 py-2 font-mono text-xs">{e.award_ref || e.bid_ref}</td>
                <td className="px-3 py-2 text-xs">{e.signer_name}<br /><span className="text-brand-navy/50">{e.signer_email}</span></td>
                <td className="px-3 py-2">{deliveryChip(e.delivery || "embedded")}</td>
                <td className="px-3 py-2">{statusChip(e.status)}</td>
                <td className="px-3 py-2 text-xs">{e.created_at?.slice(0, 16).replace("T", " ")}</td>
                <td className="px-3 py-2">
                  {e.status === "completed" ? (
                    <button onClick={() => downloadSigned(e.envelope_id)}
                      data-testid={`ds-download-${e.envelope_id}`}
                      className="text-[10px] uppercase tracking-widest border border-emerald-500 text-emerald-700 px-2 py-1 hover:bg-emerald-50">
                      ⬇ signed
                    </button>
                  ) : <span className="text-[10px] text-brand-navy/30">—</span>}
                </td>
                <td className="px-3 py-2 flex gap-1 flex-wrap">
                  <button onClick={() => setViewEnv(e)} data-testid={`ds-view-${e.envelope_id}`}
                    className="text-[10px] bg-slate-700 text-white px-2 py-1 rounded hover:bg-slate-900">👁 View</button>
                  {!["completed","declined","voided"].includes(e.status) && (
                    <button onClick={() => resendEnvelope(e.envelope_id)}
                      data-testid={`ds-resend-${e.envelope_id}`}
                      className="text-[10px] bg-indigo-600 text-white px-2 py-1 rounded hover:bg-indigo-700">↻ Resend</button>
                  )}
                  {e.status === "completed" && (
                    <button onClick={() => downloadSigned(e.envelope_id)}
                      data-testid={`ds-print-${e.envelope_id}`}
                      className="text-[10px] bg-emerald-600 text-white px-2 py-1 rounded hover:bg-emerald-700">🖨 Print</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {envelopeControls}
      </section>

      {viewEnv && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
             data-testid="ds-view-modal" onClick={() => setViewEnv(null)}>
          <div className="bg-white max-w-2xl w-full p-6 space-y-3" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-start border-b pb-3">
              <div>
                <div className="text-xs uppercase tracking-widest text-slate-500">DocuSign envelope</div>
                <div className="font-mono text-sm">{viewEnv.envelope_id}</div>
              </div>
              <button onClick={() => setViewEnv(null)} data-testid="ds-view-close"
                className="px-3 py-1.5 text-xs border">Close</button>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div><div className="text-[10px] uppercase text-slate-500">Kind</div>{viewEnv.kind} · {viewEnv.sub_kind || "—"}</div>
              <div><div className="text-[10px] uppercase text-slate-500">Ref</div><span className="font-mono">{viewEnv.award_ref || viewEnv.bid_ref || "—"}</span></div>
              <div><div className="text-[10px] uppercase text-slate-500">Signer</div>{viewEnv.signer_name}<br/><span className="text-xs text-slate-500">{viewEnv.signer_email}</span></div>
              <div><div className="text-[10px] uppercase text-slate-500">Delivery</div>{viewEnv.delivery || "embedded"}</div>
              <div><div className="text-[10px] uppercase text-slate-500">Status</div>{statusChip(viewEnv.status)}</div>
              <div><div className="text-[10px] uppercase text-slate-500">Created</div>{viewEnv.created_at?.slice(0, 16).replace("T", " ")}</div>
              {viewEnv.completed_at && (
                <div><div className="text-[10px] uppercase text-slate-500">Signed at</div>{viewEnv.completed_at?.slice(0, 16).replace("T", " ")}</div>
              )}
              {viewEnv.last_resent_at && (
                <div><div className="text-[10px] uppercase text-slate-500">Last resent</div>{viewEnv.last_resent_at?.slice(0, 16).replace("T", " ")}</div>
              )}
            </div>
            <div className="flex gap-2 pt-3 border-t">
              {!["completed","declined","voided"].includes(viewEnv.status) && (
                <button onClick={() => { resendEnvelope(viewEnv.envelope_id); setViewEnv(null); }}
                  data-testid="ds-view-resend"
                  className="px-3 py-1.5 text-xs bg-indigo-600 text-white">↻ Resend</button>
              )}
              {viewEnv.status === "completed" && (
                <button onClick={() => downloadSigned(viewEnv.envelope_id)}
                  data-testid="ds-view-download"
                  className="px-3 py-1.5 text-xs bg-emerald-600 text-white">🖨 Print / download signed</button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
