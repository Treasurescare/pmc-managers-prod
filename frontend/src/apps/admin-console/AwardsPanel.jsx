import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { awardsApi, bidApi, docusignApi, formatApiError, BACKEND_URL } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";

/** Wave 39 — Post-Award document dashboard.
 *
 * Admin picks any awarded bid, sees the auto-generated PO / SLA / Contract
 * (all PDFs), can download each, hit "Regenerate" if any failed, and now
 * (Wave 44+) can send any of the 3 PDFs directly for e-signature via
 * DocuSign — no tab-switching required. */
export default function AwardsPanel() {
  const { t } = useI18n();
  const [awardedBids, setAwardedBids] = useState([]);
  const [pickedBidId, setPickedBidId] = useState("");
  const [docs, setDocs] = useState([]);
  const [busy, setBusy] = useState(false);
  // Send-for-signature modal state
  const [signKind, setSignKind] = useState(""); // "po" | "sla" | "contract" | ""
  const [signerName, setSignerName] = useState("");
  const [signerEmail, setSignerEmail] = useState("");
  const [signDelivery, setSignDelivery] = useState("email");
  const [signBusy, setSignBusy] = useState(false);

  const loadBids = useCallback(() => {
    bidApi.listAll({ status: "awarded" }).then((rows) => {
      setAwardedBids(rows || []);
      if (!pickedBidId && rows?.length) setPickedBidId(rows[0].id);
    }).catch((e) => toast.error(formatApiError(e)));
  }, [pickedBidId]);

  const loadDocs = useCallback((bidId) => {
    if (!bidId) return;
    awardsApi.list(bidId).then((d) => setDocs(d.items || []))
      .catch((e) => toast.error(formatApiError(e)));
  }, []);

  useEffect(() => { loadBids(); }, [loadBids]);
  useEffect(() => { loadDocs(pickedBidId); }, [pickedBidId, loadDocs]);

  const regenerate = async () => {
    if (!pickedBidId) return;
    setBusy(true);
    try {
      const r = await awardsApi.regenerate(pickedBidId);
      toast.success(`${t("panels.awards.regenerated")} — ${r.award_ref}`);
      loadDocs(pickedBidId);
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  const kindLabel = (k) => ({
    po: t("panels.awards.po_title"),
    sla: t("panels.awards.sla_title"),
    contract: t("panels.awards.contract_title"),
  }[k] || k);

  const currentBid = awardedBids.find((b) => b.id === pickedBidId);

  const openSignModal = (kind) => {
    setSignKind(kind);
    setSignerName(currentBid?.company_name || currentBid?.vendor_email || "");
    setSignerEmail(currentBid?.vendor_email || "");
    setSignDelivery("email");
  };

  const closeSignModal = () => {
    if (signBusy) return;
    setSignKind("");
  };

  const sendForSignature = async () => {
    if (!pickedBidId || !signKind) return;
    if (!signerName || !signerEmail) {
      toast.error(t("panels.awards.signer_required"));
      return;
    }
    setSignBusy(true);
    try {
      const r = await docusignApi.signAward(pickedBidId, signKind, {
        signer_name: signerName,
        signer_email: signerEmail,
        delivery: signDelivery,
      });
      if (r.signing_url) {
        window.open(r.signing_url, "_blank", "noopener");
        toast.success(t("panels.awards.envelope_sent_embedded"));
      } else {
        toast.success(`${t("panels.awards.envelope_sent_email")} ${signerEmail}`);
      }
      setSignKind("");
    } catch (err) {
      const detail = err?.response?.data?.detail;
      if (detail?.code === "DOCUSIGN_CONSENT_REQUIRED" && detail.consent_url) {
        window.open(detail.consent_url, "_blank", "noopener");
        toast.error(t("panels.docusign.consent_required"));
      } else {
        toast.error(formatApiError(err));
      }
    } finally {
      setSignBusy(false);
    }
  };

  return (
    <div data-testid="admin-awards-panel">
      <div className="flex items-center justify-between mb-4 gap-3 flex-wrap">
        <div className="text-sm text-brand-navy/70">
          {t("panels.awards.hint")}
        </div>
        <button type="button" onClick={regenerate} disabled={!pickedBidId || busy}
                data-testid="awards-regenerate"
                className="px-5 py-2 text-[11px] font-semibold uppercase tracking-widest border border-brand-navy/40 text-brand-navy hover:bg-brand-navy hover:text-white disabled:opacity-40">
          {busy ? t("panels.awards.regenerating") : t("panels.awards.regenerate")}
        </button>
      </div>

      <label className="block mb-4">
        <span className="pmc-label">{t("panels.awards.awarded_bid")}</span>
        <select value={pickedBidId} onChange={(e) => setPickedBidId(e.target.value)}
                data-testid="awards-bid-picker"
                className="mt-1 w-full px-4 py-3 border border-brand-navy/20">
          {awardedBids.length === 0 && <option value="">{t("panels.awards.no_awarded_bids")}</option>}
          {awardedBids.map((b) => (
            <option key={b.id} value={b.id}>
              {b.bid_ref} · {b.company_name || b.vendor_email} · {b.award_ref || b.notice_ref}
            </option>
          ))}
        </select>
      </label>

      <div className="grid gap-4 md:grid-cols-3">
        {["po", "sla", "contract"].map((k) => {
          const d = docs.find((x) => x.kind === k);
          return (
            <div key={k} className="border border-brand-navy/10 bg-white p-5"
                 data-testid={`award-card-${k}`}>
              <div className="pmc-label">{kindLabel(k)}</div>
              {d ? (
                <>
                  <div className="mt-2 text-xs text-brand-navy/60 font-mono">{d.award_ref}</div>
                  {d.po_no && <div className="text-xs text-brand-navy/60 font-mono">PO: {d.po_no}</div>}
                  <div className="text-xs text-brand-navy/60 mt-1">{t("panels.awards.issued")} {d.awarded_at?.slice(0, 10)}</div>
                  <div className="text-xs text-brand-navy/50 mt-1">{(d.size_bytes / 1024).toFixed(1)} KB</div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <a href={`${BACKEND_URL}/api/v1/awards/bid/${pickedBidId}/pdf/${k}`}
                       target="_blank" rel="noreferrer"
                       data-testid={`award-download-${k}`}
                       className="inline-block text-[11px] font-semibold uppercase tracking-widest px-4 py-2 bg-brand-navy text-white hover:bg-brand-navy-deep">
                      {t("panels.awards.download_pdf")}
                    </a>
                    <button type="button" onClick={() => openSignModal(k)}
                       data-testid={`award-sign-${k}`}
                       className="inline-block text-[11px] font-semibold uppercase tracking-widest px-4 py-2 border border-brand-navy-soft text-brand-navy-soft hover:bg-brand-navy-soft hover:text-white">
                      {t("panels.awards.send_for_signature")}
                    </button>
                  </div>
                </>
              ) : (
                <div className="mt-2 text-xs text-brand-navy/40 italic">
                  {t("panels.awards.not_generated")}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {signKind && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4"
             onClick={closeSignModal}
             data-testid="award-sign-modal">
          <div className="bg-white max-w-md w-full p-6 border border-brand-navy/20"
               onClick={(e) => e.stopPropagation()}>
            <div className="pmc-label">{t("panels.awards.send_for_signature")}</div>
            <h3 className="font-display text-xl text-brand-navy mt-1">
              {kindLabel(signKind)}
              {currentBid?.award_ref && (
                <span className="ml-2 text-xs font-mono text-brand-navy/50">
                  {currentBid.award_ref}
                </span>
              )}
            </h3>
            <p className="text-xs text-brand-navy/60 mt-1">
              {t("panels.awards.send_hint")}
            </p>

            <div className="mt-4 space-y-3">
              <label className="block">
                <span className="pmc-label">{t("panels.awards.signer_name")}</span>
                <input value={signerName} onChange={(e) => setSignerName(e.target.value)}
                       data-testid="award-sign-name"
                       className="mt-1 w-full px-3 py-2 border border-brand-navy/20" />
              </label>
              <label className="block">
                <span className="pmc-label">{t("panels.awards.signer_email")}</span>
                <input type="email" value={signerEmail} onChange={(e) => setSignerEmail(e.target.value)}
                       data-testid="award-sign-email"
                       className="mt-1 w-full px-3 py-2 border border-brand-navy/20" />
              </label>
              <div>
                <span className="pmc-label">{t("panels.awards.delivery_mode")}</span>
                <div className="mt-2 grid grid-cols-2 gap-2">
                  <label className={"border p-3 cursor-pointer text-sm " +
                    (signDelivery === "email" ? "border-brand-navy bg-brand-navy/5" : "border-brand-navy/20 bg-white")}>
                    <input type="radio" name="award-delivery" checked={signDelivery === "email"}
                           onChange={() => setSignDelivery("email")}
                           data-testid="award-sign-delivery-email" className="mr-2" />
                    <strong>{t("panels.awards.delivery_email")}</strong>
                  </label>
                  <label className={"border p-3 cursor-pointer text-sm " +
                    (signDelivery === "embedded" ? "border-brand-navy bg-brand-navy/5" : "border-brand-navy/20 bg-white")}>
                    <input type="radio" name="award-delivery" checked={signDelivery === "embedded"}
                           onChange={() => setSignDelivery("embedded")}
                           data-testid="award-sign-delivery-embedded" className="mr-2" />
                    <strong>{t("panels.awards.delivery_embedded")}</strong>
                  </label>
                </div>
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-2">
              <button type="button" onClick={closeSignModal} disabled={signBusy}
                      data-testid="award-sign-cancel"
                      className="px-4 py-2 text-[11px] font-semibold uppercase tracking-widest border border-brand-navy/40 text-brand-navy hover:bg-brand-navy/5 disabled:opacity-40">
                {t("panels.awards.cancel")}
              </button>
              <button type="button" onClick={sendForSignature} disabled={signBusy}
                      data-testid="award-sign-submit"
                      className="px-5 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90 disabled:opacity-50">
                {signBusy ? t("panels.docusign.sending") : t("panels.awards.send_envelope")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
