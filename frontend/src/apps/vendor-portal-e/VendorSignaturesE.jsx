import { useEffect, useState } from "react";
import { useUiTheme } from "@/context/UiThemeContext";
import { docusignApi, showApiError } from "@/lib/api";
import { toast } from "sonner";
import VendorPortalChrome from "./VendorPortalChrome";

function fmtDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("en-GB",
      { day: "2-digit", month: "short", year: "numeric" });
  } catch { return iso.slice(0, 10); }
}

function statusPill(status) {
  const map = {
    completed: ["pmc-pill--success", "Completed"],
    sent:      ["pmc-pill--warning", "Awaiting your signature"],
    delivered: ["pmc-pill--warning", "Awaiting your signature"],
    created:   ["pmc-pill--info", "Preparing"],
    declined:  ["pmc-pill--danger", "Declined"],
    voided:    ["pmc-pill--danger", "Voided"],
  };
  const [cls, label] = map[status] || ["", status || "—"];
  return <span className={`pmc-pill ${cls}`}>{label}</span>;
}

export default function VendorSignaturesE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  const [envelopes, setEnvelopes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [launching, setLaunching] = useState(null);

  useEffect(() => {
    if (!isE) return;
    setLoading(true);
    docusignApi.listMine()
      .then((res) => setEnvelopes(res.items || []))
      .catch((e) => {
        // Non-fatal: show empty state instead of a toast when DocuSign is
        // not configured in this environment.
        if (e?.response?.status !== 404 && e?.response?.status !== 503) showApiError(e);
      })
      .finally(() => setLoading(false));
  }, [isE]);

  const openSigning = async (envelopeId) => {
    setLaunching(envelopeId);
    try {
      const res = await docusignApi.resumeSign(envelopeId);
      if (res?.signing_url) {
        window.open(res.signing_url, "_blank", "noopener,noreferrer");
      } else {
        toast.error("Signing URL unavailable. Try again shortly or contact PMC.");
      }
    } catch (e) { showApiError(e, { fallbackTitle: "Could not open signing view" }); }
    finally { setLaunching(null); }
  };

  const downloadSigned = async (envelopeId) => {
    try {
      const blob = await docusignApi.vendorDownloadPdf(envelopeId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${envelopeId}-signed.pdf`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) { showApiError(e, { fallbackTitle: "Download failed" }); }
  };

  const pending = envelopes.filter((e) => ["sent", "delivered", "created"].includes(e.status));
  const completed = envelopes.filter((e) => e.status === "completed");

  if (!isE && Legacy) return <Legacy />;
  if (!isE) return null;

  return (
    <div data-testid="vendor-signatures-e" data-pmc-e-page="vendor-signatures-e">
      <VendorPortalChrome active="/vendor/signatures">
        <div className="sp-head">
          <div>
            <div className="pmc-eyebrow">Signatures</div>
            <h1 data-testid="vsig-heading">
              {loading ? "Loading…" : `${pending.length} document${pending.length === 1 ? "" : "s"} to sign`}
            </h1>
          </div>
        </div>

        {loading && (
          <div className="pmc-callout" data-testid="vsig-loading">
            Fetching your envelopes from DocuSign…
          </div>
        )}

        {!loading && envelopes.length === 0 && (
          <div className="pmc-callout" data-testid="vsig-empty">
            <svg className="pmc-ico" aria-hidden="true"><use href="#i-flag" /></svg>
            <div>
              <b>Nothing to sign yet.</b>{" "}
              When PMC awards one of your bids, the contract and purchase order will appear here for signature.
            </div>
          </div>
        )}

        {!loading && envelopes.length > 0 && (
          <section className="pmc-panel" data-testid="vsig-table">
            <table className="pmc-table">
              <thead>
                <tr>
                  <th>Document</th>
                  <th>Status</th>
                  <th>Detail</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {envelopes.map((e) => (
                  <tr key={e.envelope_id} data-testid={`vsig-row-${e.envelope_id}`}>
                    <td>
                      <div style={{ fontWeight: 600 }}>
                        {e.subject || `${(e.sub_kind || "contract").toUpperCase()} · ${e.award_ref || e.bid_ref || e.envelope_id}`}
                      </div>
                      <span className="pmc-ref">{e.award_ref || e.bid_ref || e.envelope_id}</span>
                    </td>
                    <td>{statusPill(e.status)}</td>
                    <td className="pmc-muted" style={{ fontSize: 13 }}>
                      {e.status === "completed"
                        ? `Signed ${fmtDate(e.completed_at || e.last_updated_at)}`
                        : `Sent ${fmtDate(e.created_at)}`}
                    </td>
                    <td style={{ textAlign: "right" }}>
                      {["sent", "delivered", "created"].includes(e.status) && (
                        <button type="button"
                                onClick={() => openSigning(e.envelope_id)}
                                disabled={launching === e.envelope_id}
                                className="pmc-btn pmc-btn--primary pmc-btn--sm"
                                data-testid={`vsig-sign-${e.envelope_id}`}>
                          {launching === e.envelope_id ? "Opening…" : "Review & sign"}
                        </button>
                      )}
                      {e.status === "completed" && e.has_document !== false && (
                        <button type="button"
                                onClick={() => downloadSigned(e.envelope_id)}
                                className="pmc-btn pmc-btn--secondary pmc-btn--sm"
                                data-testid={`vsig-download-${e.envelope_id}`}>
                          Download
                        </button>
                      )}
                      {e.status === "completed" && e.has_document === false && (
                        <span className="pmc-muted" style={{ fontSize: 12 }}
                              data-testid={`vsig-nodoc-${e.envelope_id}`}>
                          PDF not archived — ask PMC to regenerate
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}

        {completed.length > 0 && (
          <div className="pmc-muted" style={{ marginTop: 16, fontSize: 13 }}
               data-testid="vsig-footer">
            Signed PDFs include a DocuSign Certificate of Completion and are mirrored
            on your audit ledger.
          </div>
        )}
      </VendorPortalChrome>
    </div>
  );
}
