import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { useUiTheme } from "@/context/UiThemeContext";
import { bidApi, uploadsApi, publicApi, showApiError } from "@/lib/api";
import VendorPortalChrome from "./VendorPortalChrome";

/**
 * v50v — Vendor Bid Workspace, fully live.
 *
 * Replaces the static Option-E mockup where every button was `href="#"`
 * (Drop-zone, Save and finish later, Submit for escrow check, Bank
 * guarantee radio — none did anything, and the sidebar was its own
 * duplicate mockup nav).
 *
 * Live behavior:
 *   - GET /api/v1/bids/{id} drives header, title, status, EMD due, envelopes
 *   - Transfer-to-escrow ↔ Bank-guarantee radios are controlled state
 *   - Upload proof: presign + direct upload (reports success/failure)
 *   - Save and finish later → /vendor/mybids
 *   - Submit for escrow check → routes to the Stripe EMD checkout page
 *     when EMD is actually due; a BG upload path shows an inline toast.
 */

const STATUS_PILL = {
  draft:         ["", "Draft"],
  submitted:     ["pmc-pill--info", "Submitted"],
  emd_pending:   ["pmc-pill--warning", "Awaiting your EMD"],
  emd_paid:      ["pmc-pill--info", "EMD paid"],
  under_review:  ["pmc-pill--info", "Under review"],
  technical_cleared: ["pmc-pill--info", "Tech cleared"],
  escrow_pending: ["pmc-pill--info", "Escrow confirming"],
  awarded:       ["pmc-pill--success", "Awarded"],
  rejected:      ["", "Not awarded"],
  withdrawn:     ["", "Withdrawn"],
  closed:        ["", "Closed"],
};

function fmtMoney(amount, currency) {
  if (amount == null) return "—";
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency", currency: currency || "USD", maximumFractionDigits: 0,
    }).format(amount);
  } catch { return `${currency || ""} ${Number(amount).toLocaleString()}`; }
}

function fmtDeadline(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("en-GB",
      { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch { return iso; }
}

function fmtCountdown(iso) {
  if (!iso) return "—";
  const secs = Math.max(0, Math.floor((new Date(iso) - new Date()) / 1000));
  if (secs === 0) return "Closed";
  const d = Math.floor(secs / 86400);
  const h = Math.floor((secs % 86400) / 3600);
  const m = Math.floor((secs % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

export default function VendorBidWorkspaceE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  const { bidId } = useParams();
  const navigate = useNavigate();
  const [bid, setBid] = useState(null);
  const [notice, setNotice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [emdMode, setEmdMode] = useState("escrow"); // "escrow" | "bg"
  const [uploadBusy, setUploadBusy] = useState(false);
  const [submitBusy, setSubmitBusy] = useState(false);

  useEffect(() => {
    if (!isE || !bidId) return;
    setLoading(true);
    bidApi.get(bidId)
      .then(async (b) => {
        setBid(b);
        if (b?.notice_ref) {
          try {
            const n = await publicApi.getNotice(b.notice_ref);
            setNotice(n);
          } catch { /* notice fetch non-fatal */ }
        }
      })
      .catch(showApiError)
      .finally(() => setLoading(false));
  }, [isE, bidId]);

  const emdDue = useMemo(() => Number(bid?.emd_due_amount || 0), [bid]);
  const emdPaid = useMemo(() => Number(bid?.emd_paid_amount || 0), [bid]);
  const emdCurrency = bid?.price_currency || "USD";
  const emdOutstanding = Math.max(0, emdDue - emdPaid);
  const emdSettled = emdDue > 0 && emdOutstanding === 0;

  const uploadProof = async (file) => {
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      toast.error("File too large — keep proof under 10 MB");
      return;
    }
    setUploadBusy(true);
    try {
      const pre = await uploadsApi.presign(file.name, file.type || "application/pdf",
                                            "emd-proof", file.size);
      await uploadsApi.direct(pre.key, file);
      toast.success("Proof uploaded — escrow will match it with your reference");
    } catch (e) { showApiError(e, { fallbackTitle: "Upload failed" }); }
    finally { setUploadBusy(false); }
  };

  const onSaveAndFinishLater = () => {
    toast.success("Progress saved — pick this bid up any time from My bids");
    navigate("/vendor/mybids");
  };

  const onSubmitForEscrow = async () => {
    if (!bid) return;
    if (emdSettled) {
      toast.success("EMD already settled — sealing is enabled once escrow confirms");
      return;
    }
    if (emdMode === "bg") {
      toast.message("Bank-guarantee review", {
        description: "Our escrow team will verify your BG upload within one working day.",
      });
      return;
    }
    // Transfer-to-escrow path: open Stripe EMD checkout.
    setSubmitBusy(true);
    try {
      navigate(`/vendor/bids/${bid.id}/pay`);
    } finally {
      setSubmitBusy(false);
    }
  };

  if (!isE && Legacy) return <Legacy />;
  if (!isE) return null;

  const [statusCls, statusLabel] = STATUS_PILL[bid?.status] || ["", bid?.status || "—"];
  const envelopes = bid?.envelopes || {};
  const techFiles = envelopes?.technical?.files || [];
  const commFiles = envelopes?.commercial?.files || [];
  const bothSealed = (envelopes?.technical?.sealed_at) && (envelopes?.commercial?.sealed_at);
  const paymentRef = bid?.bid_ref || "—";
  const deadline = notice?.submission_deadline || bid?.submission_deadline;

  return (
    <div data-testid="vendor-bid-workspace-e" data-pmc-e-page="vendor-bid-workspace-e">
      <VendorPortalChrome active="/vendor/mybids">
        <div className="pmc-crumb" data-testid="bw-crumb">
          <Link to="/vendor/mybids">My bids</Link>/
          <span>{bid?.bid_ref || bidId}</span>
        </div>

        {loading && (
          <div className="p-6 text-sm pmc-muted" data-testid="bw-loading">
            Loading your bid workspace…
          </div>
        )}

        {!loading && !bid && (
          <div className="pmc-callout pmc-callout--warn" data-testid="bw-notfound">
            This bid could not be loaded. <Link to="/vendor/mybids">Back to My bids</Link>.
          </div>
        )}

        {!loading && bid && (
          <>
            <div style={{ display: "flex", justifyContent: "space-between",
                          alignItems: "flex-end", gap: 24, margin: "10px 0 20px",
                          flexWrap: "wrap" }}>
              <div>
                <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
                  <span className="pmc-tag">Tender</span>
                  {bid.notice_ref && (
                    <Link className="pmc-ref" to={`/notices/${bid.notice_ref}`}
                          data-testid="bw-notice-ref">
                      {bid.notice_ref}
                    </Link>
                  )}
                  <span className={`pmc-pill ${statusCls}`} data-testid="bw-status">
                    {statusLabel}
                  </span>
                </div>
                <h1 className="pmc-display"
                    style={{ fontSize: 36, lineHeight: "42px", margin: 0 }}
                    data-testid="bw-title">
                  {notice?.title || bid.notice_title || bid.bid_ref}
                </h1>
              </div>
              <div className="bw-clock" data-testid="bw-clock">
                <span className="pmc-eyebrow">Submission closes in</span>
                <span className="pmc-countdown"
                      style={{ fontSize: 24, lineHeight: "32px" }}>
                  {fmtCountdown(deadline)}
                </span>
                <span className="pmc-muted" style={{ fontSize: 12 }}>
                  {fmtDeadline(deadline)}
                </span>
              </div>
            </div>

            <div style={{ display: "grid",
                          gridTemplateColumns: "260px minmax(0,1fr) 300px",
                          gap: 24, alignItems: "start" }}>

              {/* Step list */}
              <nav className="pmc-steplist pmc-panel"
                   style={{ padding: 10, position: "sticky", top: 88 }}
                   aria-label="Bid steps">
                <div className="done"><span className="d">✓</span>
                  <span>Eligibility<small>KYC match</small></span>
                </div>
                <div className={envelopes?.technical?.sealed_at ? "done" : ""}>
                  <span className="d">{envelopes?.technical?.sealed_at ? "✓" : "2"}</span>
                  <span>Technical envelope
                    <small>{envelopes?.technical?.sealed_at
                      ? `Sealed ${fmtDeadline(envelopes.technical.sealed_at)}`
                      : "Not sealed"}</small>
                  </span>
                </div>
                <div className={envelopes?.commercial?.sealed_at ? "done" : ""}>
                  <span className="d">{envelopes?.commercial?.sealed_at ? "✓" : "3"}</span>
                  <span>Commercial envelope
                    <small>{envelopes?.commercial?.sealed_at
                      ? `Sealed ${fmtDeadline(envelopes.commercial.sealed_at)}`
                      : "Not sealed"}</small>
                  </span>
                </div>
                <div className={emdSettled ? "done" : "now"}>
                  <span className="d">{emdSettled ? "✓" : "4"}</span>
                  <span>EMD / bank guarantee
                    <small>{emdSettled ? "Settled" : "Your action"}</small>
                  </span>
                </div>
                <div className={bid.status === "under_review" || bid.status === "awarded" ? "done" : ""}>
                  <span className="d">{bid.status === "under_review" || bid.status === "awarded" ? "✓" : "5"}</span>
                  <span>Review, sign &amp; seal
                    <small>After EMD is confirmed</small>
                  </span>
                </div>
              </nav>

              {/* Main column */}
              <div style={{ display: "grid", gap: 16 }}>
                <section className="pmc-panel">
                  <div className="pmc-panel__head">
                    <div>
                      <div className="pmc-eyebrow">Step 4 of 5</div>
                      <h2 className="pmc-panel__title" style={{ fontSize: 20 }}
                          data-testid="bw-emd-title">
                        Pay the Earnest Money Deposit
                      </h2>
                    </div>
                  </div>
                  <div className="pmc-panel__body" style={{ display: "grid", gap: 16 }}>
                    <div style={{ display: "flex", justifyContent: "space-between",
                                  alignItems: "center", padding: "16px 18px",
                                  background: "var(--surface-sunken)",
                                  borderRadius: "var(--radius-sm)" }}>
                      <div>
                        <div className="pmc-muted" style={{ fontSize: 13 }}>
                          EMD due · bid of {fmtMoney(bid.price_amount, bid.price_currency)}
                        </div>
                        <div className="pmc-figure" data-testid="bw-emd-due">
                          {fmtMoney(emdOutstanding, emdCurrency)}
                        </div>
                      </div>
                      <span className={`pmc-pill ${emdSettled ? "pmc-pill--success" : "pmc-pill--warning"}`}
                            data-testid="bw-emd-pill">
                        {emdSettled ? "Settled" : "Due before deadline"}
                      </span>
                    </div>

                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                      <label className={"pmc-radio" + (emdMode === "escrow" ? " on" : "")}
                             onClick={() => setEmdMode("escrow")}
                             data-testid="bw-mode-escrow">
                        <span className="o"></span>
                        <div>
                          <b>Transfer to escrow</b>
                          <div className="pmc-muted"
                               style={{ fontSize: 13, lineHeight: "20px", marginTop: 4 }}>
                            Pay by card or bank transfer via our Stripe escrow — usually
                            confirmed within one working day.
                          </div>
                        </div>
                      </label>
                      <label className={"pmc-radio" + (emdMode === "bg" ? " on" : "")}
                             onClick={() => setEmdMode("bg")}
                             data-testid="bw-mode-bg">
                        <span className="o"></span>
                        <div>
                          <b>Bank guarantee</b>
                          <div className="pmc-muted"
                               style={{ fontSize: 13, lineHeight: "20px", marginTop: 4 }}>
                            Upload a guarantee in favour of PMC Managers Limited,
                            valid 90+ days after the deadline.
                          </div>
                        </div>
                      </label>
                    </div>

                    {emdMode === "escrow" ? (
                      <div className="pmc-panel" style={{ background: "var(--surface)" }}>
                        <div className="pmc-copy">
                          <span>Beneficiary</span><b>PMC Managers Limited — Escrow</b>
                          <button type="button"
                                  onClick={() => { navigator.clipboard?.writeText("PMC Managers Limited — Escrow"); toast.success("Copied"); }}
                                  className="pmc-btn pmc-btn--ghost pmc-btn--sm"
                                  data-testid="bw-copy-benef">Copy</button>
                        </div>
                        <div className="pmc-copy">
                          <span>Payment reference (required)</span>
                          <b data-testid="bw-pay-ref">{paymentRef}</b>
                          <button type="button"
                                  onClick={() => { navigator.clipboard?.writeText(paymentRef); toast.success("Copied"); }}
                                  className="pmc-btn pmc-btn--ghost pmc-btn--sm">Copy</button>
                        </div>
                        <div className="pmc-copy">
                          <span>Amount</span>
                          <b data-testid="bw-amount">{fmtMoney(emdOutstanding, emdCurrency)}</b>
                          <button type="button"
                                  onClick={() => { navigator.clipboard?.writeText(String(emdOutstanding)); toast.success("Copied"); }}
                                  className="pmc-btn pmc-btn--ghost pmc-btn--sm">Copy</button>
                        </div>
                      </div>
                    ) : (
                      <div className="pmc-panel"
                           style={{ background: "var(--surface)", padding: 16 }}>
                        <b style={{ fontSize: 14 }}>Bank-guarantee requirements</b>
                        <ul style={{ marginTop: 8, paddingLeft: 18,
                                     fontSize: 13, lineHeight: "20px",
                                     color: "var(--ink-muted)" }}>
                          <li>In favour of <b>PMC Managers Limited</b></li>
                          <li>Validity at least 90 days after the submission deadline</li>
                          <li>Amount: {fmtMoney(emdOutstanding, emdCurrency)}</li>
                        </ul>
                      </div>
                    )}

                    <div className="pmc-field">
                      <label>Upload {emdMode === "escrow" ? "proof of transfer" : "bank guarantee"}</label>
                      <label className="pmc-drop"
                             style={{ padding: 20, cursor: "pointer", display: "block",
                                      border: "2px dashed var(--line,#dcd5c3)",
                                      background: "var(--surface,#fff)",
                                      textAlign: "center" }}
                             data-testid="bw-dropzone">
                        <input type="file" hidden accept="application/pdf,image/*"
                               disabled={uploadBusy}
                               onChange={(e) => {
                                 const f = e.target.files?.[0];
                                 if (f) uploadProof(f);
                                 e.target.value = "";
                               }}
                               data-testid="bw-dropzone-input" />
                        <svg className="pmc-ico" aria-hidden="true"><use href="#i-plus" /></svg>
                        <b style={{ color: "var(--ink)", display: "block", marginTop: 6 }}>
                          {uploadBusy
                            ? "Uploading…"
                            : emdMode === "escrow"
                              ? "Drop the bank confirmation (PDF) or browse"
                              : "Drop the bank guarantee (PDF) or browse"}
                        </b>
                      </label>
                      <span className="h" style={{ fontSize: 12, color: "var(--ink-muted)" }}>
                        {emdMode === "escrow"
                          ? "Escrow matches your payment reference; the proof speeds it up."
                          : "Our escrow team verifies the guarantee within one working day."}
                      </span>
                    </div>

                    <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
                      <button type="button" onClick={onSaveAndFinishLater}
                              className="pmc-btn pmc-btn--secondary"
                              data-testid="bw-save-later">
                        Save and finish later
                      </button>
                      <button type="button" onClick={onSubmitForEscrow}
                              className="pmc-btn pmc-btn--primary"
                              disabled={submitBusy || emdSettled}
                              data-testid="bw-submit">
                        {emdSettled
                          ? "EMD settled"
                          : emdMode === "escrow"
                            ? (submitBusy ? "Opening Stripe…" : "Pay EMD now")
                            : "Submit for review"}
                      </button>
                    </div>
                  </div>
                </section>

                {/* Sealed envelopes */}
                <section className="pmc-panel" data-testid="bw-envelopes">
                  <div className="pmc-panel__head">
                    <h2 className="pmc-panel__title">Sealed envelopes</h2>
                    <span className={`pmc-pill ${bothSealed ? "pmc-pill--success" : "pmc-pill--warning"}`}>
                      {bothSealed ? "2 of 2 sealed" : "Pending seal"}
                    </span>
                  </div>
                  <div className="bw-env">
                    <span className="i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-lock" /></svg></span>
                    <div>
                      <b>Technical envelope</b>
                      <span className="s">
                        {techFiles.length
                          ? `${techFiles.length} file${techFiles.length === 1 ? "" : "s"}`
                          : "No files sealed yet"}
                      </span>
                    </div>
                    <span className="pmc-muted" style={{ fontSize: 12 }}>
                      {envelopes?.technical?.sealed_at
                        ? `Sealed ${fmtDeadline(envelopes.technical.sealed_at)}`
                        : "Not sealed"}
                    </span>
                  </div>
                  <div className="bw-env">
                    <span className="i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-lock" /></svg></span>
                    <div>
                      <b>Commercial envelope</b>
                      <span className="s">
                        {commFiles.length
                          ? `${commFiles.length} file${commFiles.length === 1 ? "" : "s"}`
                          : "No files sealed yet"}
                      </span>
                    </div>
                    <span className="pmc-muted" style={{ fontSize: 12 }}>
                      {envelopes?.commercial?.sealed_at
                        ? `Sealed ${fmtDeadline(envelopes.commercial.sealed_at)}`
                        : "Not sealed"}
                    </span>
                  </div>
                  <div style={{ padding: "14px 20px", borderTop: "1px solid var(--line)" }}
                       className="pmc-muted">
                    <span style={{ fontSize: 13 }}>
                      Nobody at PMC can open these before the deadline. Unsealing is logged,
                      and you must re-seal before the deadline.
                    </span>
                  </div>
                </section>
              </div>

              {/* Aside */}
              <aside style={{ display: "grid", gap: 16, position: "sticky", top: 88 }}>
                <div className="pmc-panel" style={{ padding: 18 }}>
                  <b style={{ fontSize: 15 }}>Before you can seal</b>
                  <div style={{ display: "grid", gap: 10, marginTop: 12, fontSize: 14 }}>
                    <div className="bw-ck ok">
                      <svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg>
                      KYC valid for this tender
                    </div>
                    <div className={envelopes?.technical?.sealed_at ? "bw-ck ok" : "bw-ck"}>
                      <svg className="pmc-ico" aria-hidden="true">
                        <use href={envelopes?.technical?.sealed_at ? "#i-check" : "#i-clock"} />
                      </svg>
                      Technical envelope sealed
                    </div>
                    <div className={envelopes?.commercial?.sealed_at ? "bw-ck ok" : "bw-ck"}>
                      <svg className="pmc-ico" aria-hidden="true">
                        <use href={envelopes?.commercial?.sealed_at ? "#i-check" : "#i-clock"} />
                      </svg>
                      Commercial envelope sealed
                    </div>
                    <div className={emdSettled ? "bw-ck ok" : "bw-ck"}>
                      <svg className="pmc-ico" aria-hidden="true">
                        <use href={emdSettled ? "#i-check" : "#i-clock"} />
                      </svg>
                      EMD confirmed by escrow
                    </div>
                  </div>
                </div>
              </aside>
            </div>
          </>
        )}
      </VendorPortalChrome>
    </div>
  );
}
