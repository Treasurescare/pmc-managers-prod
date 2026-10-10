import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { useUiTheme } from "@/context/UiThemeContext";
import { bidApi, uploadsApi, publicApi, showApiError, BACKEND_URL } from "@/lib/api";
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

/** v51ah — vendor can always see (and re-download) the files THEY submitted
 *  inside each envelope. PMC staff cannot open them before the deadline, but
 *  the owning vendor can. */
function EnvelopeFiles({ files, onView, onRemove, testid }) {
  if (!files?.length) return null;
  return (
    <ul data-testid={testid}
        style={{ listStyle: "none", margin: 0, padding: "0 20px 10px" }}>
      {files.map((f, i) => {
        const name = f.filename || f.name || f.file_name || `File ${i + 1}`;
        const size = f.size_bytes ?? f.size;
        const key = f.key;
        return (
          <li key={i}
              data-testid={`${testid}-row-${i}`}
              style={{ display: "flex", alignItems: "center", gap: 8,
                       padding: "6px 0", borderTop: "1px solid var(--line,#0001)",
                       fontSize: 13 }}>
            <svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg>
            <span style={{ flex: 1, minWidth: 0, overflow: "hidden",
                           textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                  title={name}>{name}</span>
            {size ? (
              <span className="pmc-muted" style={{ fontSize: 11 }}>
                {size >= 1048576
                  ? `${(size / 1048576).toFixed(1)} MB`
                  : `${Math.max(1, Math.round(size / 1024))} KB`}
              </span>
            ) : null}
            {key && (
              <button type="button"
                      onClick={() => onView({ key, filename: name })}
                      className="pmc-btn pmc-btn--ghost pmc-btn--sm"
                      data-testid={`${testid}-view-${i}`}>
                View
              </button>
            )}
            {key && (
              <a href={`${BACKEND_URL}/api/v1/uploads/files/${key}`}
                 download={name}
                 className="pmc-btn pmc-btn--ghost pmc-btn--sm"
                 data-testid={`${testid}-dl-${i}`}>
                Download
              </a>
            )}
            {onRemove && key && (
              <button type="button"
                      onClick={() => onRemove(key)}
                      className="pmc-btn pmc-btn--ghost pmc-btn--sm"
                      data-testid={`${testid}-del-${i}`}>
                Remove
              </button>
            )}
          </li>
        );
      })}
    </ul>
  );
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
  const [proofs, setProofs] = useState([]); // v50w — every uploaded doc, viewable + deletable
  const [preview, setPreview] = useState(null); // v50x — in-page document preview

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
  // v51ax — a bid with emd_due_amount = 0 is already settled (backend sets
  // status "submitted" at creation). The old `emdDue > 0 &&` guard left
  // $0-EMD bids stuck at Step 4 forever (xlsx #14).
  const emdSettled = emdDue <= 0 || emdOutstanding === 0;

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
      // v50w — every uploaded doc lands in the visible list so the vendor can
      // view / re-open / delete it before submitting for escrow check.
      setProofs((p) => [...p, {
        key: pre.key, filename: file.name,
        size: file.size, kind: emdMode,
        uploaded_at: new Date().toISOString(),
      }]);
      toast.success(`${file.name} uploaded`);
    } catch (e) { showApiError(e, { fallbackTitle: "Upload failed" }); }
    finally { setUploadBusy(false); }
  };

  const removeProof = (idx) => setProofs((p) => p.filter((_, i) => i !== idx));

  // v51ai — post-submission envelope file management. Vendors can attach or
  // remove technical / commercial files while the bid is still editable;
  // every change persists via PATCH /bids/{id} and lands on the audit ledger.
  const persistDocuments = async (nextDocs) => {
    try {
      const fresh = await bidApi.update(bid.id, { documents: nextDocs });
      setBid(fresh);
      toast.success("Envelope files updated");
    } catch (e) { showApiError(e, { fallbackTitle: "Could not update envelope" }); }
  };

  const uploadEnvelopeFile = async (kind, file) => {
    if (!file || !bid) return;
    if (file.size > 10 * 1024 * 1024) {
      toast.error("Keep envelope files under 10 MB");
      return;
    }
    try {
      const pre = await uploadsApi.presign(file.name, file.type || "application/pdf",
                                           "bid-docs", file.size);
      await uploadsApi.direct(pre.key, file);
      const docs = Array.isArray(bid.documents) ? [...bid.documents] : [];
      await persistDocuments([...docs, {
        kind, key: pre.key, filename: file.name,
        size_bytes: file.size, uploaded_at: new Date().toISOString(),
      }]);
    } catch (e) { showApiError(e, { fallbackTitle: "Upload failed" }); }
  };

  const removeEnvelopeFile = (key) => {
    if (!bid) return;
    persistDocuments((bid.documents || []).filter((d) => d.key !== key));
  };

  const scrollToEnvelopes = () =>
    document.querySelector('[data-testid="bw-envelopes"]')
      ?.scrollIntoView({ behavior: "smooth", block: "start" });

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
  // v51ah — envelope CONTENT comes from the bid's documents (kind: technical /
  // commercial), uploaded when the bid was composed. The legacy
  // envelopes.*.files field is never populated by the backend, which made
  // every workspace show "No files sealed yet" even for fully submitted bids.
  const docs = Array.isArray(bid?.documents) ? bid.documents : [];
  const techFiles = envelopes?.technical?.files?.length
    ? envelopes.technical.files
    : docs.filter((d) => d.kind === "technical");
  const commFiles = envelopes?.commercial?.files?.length
    ? envelopes.commercial.files
    : docs.filter((d) => d.kind === "commercial");
  const techDone = Boolean(envelopes?.technical?.sealed_at) || techFiles.length > 0;
  const commDone = Boolean(envelopes?.commercial?.sealed_at) || commFiles.length > 0;
  const emdNotRequired = emdDue <= 0;
  const emdDone = emdNotRequired || emdSettled;
  const bothSealed = techDone && commDone;
  // First step still needing the vendor's action — drives the "Your action" marker.
  const firstPending = !techDone ? 2 : !commDone ? 3 : !emdDone ? 4 : 5;
  const paymentRef = bid?.bid_ref || "—";
  const deadline = notice?.submission_deadline || bid?.submission_deadline;
  // v51ai — envelope files can be changed while the bid is anywhere before
  // admin evaluation starts (draft / submitted / emd_pending / emd_paid /
  // escrow_accepted) and the deadline hasn't passed. on_hold and later lock.
  const envEditable = Boolean(bid) &&
    ["draft", "submitted", "emd_pending", "emd_paid", "escrow_accepted"].includes(bid.status) &&
    (!deadline || new Date(deadline) > new Date());

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
                <div className={techDone ? "done" : firstPending === 2 ? "now" : ""}
                     onClick={scrollToEnvelopes}
                     style={{ cursor: "pointer" }}
                     title="View technical envelope files"
                     data-testid="bw-step-2">
                  <span className="d">{techDone ? "✓" : "2"}</span>
                  <span>Technical envelope
                    <small>{envelopes?.technical?.sealed_at
                      ? `Sealed ${fmtDeadline(envelopes.technical.sealed_at)}`
                      : techDone
                        ? "Submitted with bid"
                        : firstPending === 2 ? "Your action" : "Not submitted"}</small>
                  </span>
                </div>
                <div className={commDone ? "done" : firstPending === 3 ? "now" : ""}
                     onClick={scrollToEnvelopes}
                     style={{ cursor: "pointer" }}
                     title="View commercial envelope files"
                     data-testid="bw-step-3">
                  <span className="d">{commDone ? "✓" : "3"}</span>
                  <span>Commercial envelope
                    <small>{envelopes?.commercial?.sealed_at
                      ? `Sealed ${fmtDeadline(envelopes.commercial.sealed_at)}`
                      : commDone
                        ? "Submitted with bid"
                        : firstPending === 3 ? "Your action" : "Not submitted"}</small>
                  </span>
                </div>
                <div className={emdDone ? "done" : firstPending === 4 ? "now" : ""}>
                  <span className="d">{emdDone ? "✓" : "4"}</span>
                  <span>EMD / bank guarantee
                    <small>{emdNotRequired ? "Not required" : emdSettled ? "Settled" : "Your action"}</small>
                  </span>
                </div>
                {(() => {
                  // v51bc — $0 EMD bids reach "submitted" immediately; the
                  // vendor has no further action and admin review auto-starts.
                  // Mark step 5 done so the workspace doesn't look like it's
                  // waiting on them.
                  const inReview = ["under_review","technical_cleared","emd_paid",
                                     "escrow_accepted","awarded"].includes(bid.status);
                  const zeroEmdSubmitted = emdNotRequired && bothSealed &&
                    ["submitted","under_review","technical_cleared","awarded"].includes(bid.status);
                  const step5Done = inReview || zeroEmdSubmitted;
                  return (
                    <div className={step5Done ? "done" : ""} data-testid="bw-step-5">
                      <span className="d">{step5Done ? "✓" : "5"}</span>
                      <span>Review, sign &amp; seal
                        <small>
                          {step5Done
                            ? (zeroEmdSubmitted
                                ? "In PMC review queue — nothing more for you"
                                : "Admin review in progress")
                            : emdNotRequired
                              ? "Starts the moment both envelopes are sealed"
                              : "Starts after EMD is confirmed"}
                        </small>
                      </span>
                    </div>
                  );
                })()}
              </nav>

              {/* Main column */}
              <div style={{ display: "grid", gap: 16 }}>
                <section className="pmc-panel">
                  <div className="pmc-panel__head">
                    <div>
                      <div className="pmc-eyebrow">Step 4 of 5</div>
                      <h2 className="pmc-panel__title" style={{ fontSize: 20 }}
                          data-testid="bw-emd-title">
                        {emdNotRequired
                          ? "Earnest Money Deposit — not required"
                          : "Pay the Earnest Money Deposit"}
                      </h2>
                    </div>
                  </div>
                  <div className="pmc-panel__body" style={{ display: "grid", gap: 16 }}>
                    {emdNotRequired ? (
                      <div className="pmc-callout" data-testid="bw-emd-not-required"
                           style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                        <svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg>
                        <div>
                          <b>No EMD required for this tender.</b>
                          <div className="pmc-muted" style={{ fontSize: 13, marginTop: 4 }}>
                            The buyer set the Earnest Money Deposit to zero — nothing to pay
                            or upload here. This step is already complete; your bid moves
                            straight to review, sign &amp; seal.
                          </div>
                          <button type="button" onClick={onSaveAndFinishLater}
                                  className="pmc-btn pmc-btn--secondary" style={{ marginTop: 10 }}
                                  data-testid="bw-save-later-noemd">
                            Save and finish later
                          </button>
                        </div>
                      </div>
                    ) : (<>
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
                        <input type="file" hidden accept="application/pdf"
                               disabled={uploadBusy}
                               onChange={(e) => {
                                 const f = e.target.files?.[0];
                                 if (f && f.type && f.type !== "application/pdf") {
                                   // v51at — enforce PDF-only for technical/commercial envelope proofs
                                   // (xlsx bug row 2). Accept header was permissive before.
                                   e.target.value = "";
                                   return alert("Only PDF files are accepted for bid envelope uploads.");
                                 }
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

                      {/* v50w — uploaded documents list: viewable, deletable, multi-file */}
                      {proofs.length > 0 && (
                        <div data-testid="bw-proof-list"
                             style={{ marginTop: 10, border: "1px solid var(--line,#dcd5c3)",
                                      borderRadius: "var(--radius-sm,6px)",
                                      background: "var(--surface,#fff)" }}>
                          <div className="pmc-eyebrow"
                               style={{ padding: "10px 14px 6px" }}>
                            Uploaded ({proofs.length})
                          </div>
                          {proofs.map((doc, idx) => (
                            <div key={doc.key}
                                 data-testid={`bw-proof-row-${idx}`}
                                 style={{ display: "flex", alignItems: "center",
                                          gap: 10, padding: "8px 14px",
                                          borderTop: "1px solid var(--line,#0001)",
                                          fontSize: 13 }}>
                              <svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg>
                              <span style={{ flex: 1, minWidth: 0,
                                             overflow: "hidden", textOverflow: "ellipsis",
                                             whiteSpace: "nowrap", fontWeight: 600 }}
                                    title={doc.filename}>
                                {doc.filename}
                              </span>
                              <span className="pmc-muted" style={{ fontSize: 11 }}>
                                {doc.size >= 1048576
                                  ? `${(doc.size / 1048576).toFixed(1)} MB`
                                  : `${Math.max(1, Math.round(doc.size / 1024))} KB`}
                              </span>
                              <button type="button" onClick={() => setPreview(doc)}
                                      className="pmc-btn pmc-btn--ghost pmc-btn--sm"
                                      data-testid={`bw-proof-view-${idx}`}>
                                View
                              </button>
                              <button type="button" onClick={() => removeProof(idx)}
                                      className="pmc-btn pmc-btn--ghost pmc-btn--sm"
                                      data-testid={`bw-proof-del-${idx}`}>
                                Delete
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
                      <button type="button" onClick={onSaveAndFinishLater}
                              className="pmc-btn pmc-btn--secondary"
                              data-testid="bw-save-later">
                        Save and finish later
                      </button>
                      {/* v50x — hide the EMD submit action entirely when the
                          tender requires no EMD (emd_due_amount = 0). */}
                      {emdDue <= 0 ? (
                        <span className="pmc-muted" style={{ fontSize: 13, alignSelf: "center" }}
                              data-testid="bw-no-emd">
                          No EMD required for this bid
                        </span>
                      ) : (
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
                      )}
                    </div>
                    </>)}
                  </div>
                </section>

                {/* Sealed envelopes */}
                <section className="pmc-panel" data-testid="bw-envelopes">
                  <div className="pmc-panel__head">
                    <h2 className="pmc-panel__title">Sealed envelopes</h2>
                    <span className={`pmc-pill ${bothSealed ? "pmc-pill--success" : "pmc-pill--warning"}`}>
                      {bothSealed ? "2 of 2 submitted" : "Pending submission"}
                    </span>
                  </div>
                  {bid.status === "on_hold" && (
                    <div className="pmc-callout pmc-callout--warn" data-testid="bw-on-hold"
                         style={{ margin: "0 20px 12px" }}>
                      <b>This bid is on hold by PMC.</b>{" "}
                      You can't change envelope files until the tender desk resumes it
                      (Bidding ops → Resume). Questions: tenders@pmcmanagers.com.
                    </div>
                  )}
                  <div className="bw-env">
                    <span className="i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-lock" /></svg></span>
                    <div>
                      <b>Technical envelope</b>
                      <span className="s">
                        {techFiles.length
                          ? `${techFiles.length} file${techFiles.length === 1 ? "" : "s"}`
                          : "No files submitted yet"}
                      </span>
                    </div>
                    <span className="pmc-muted" style={{ fontSize: 12 }}>
                      {envelopes?.technical?.sealed_at
                        ? `Sealed ${fmtDeadline(envelopes.technical.sealed_at)}`
                        : techFiles.length ? "Submitted with bid" : "Not submitted"}
                    </span>
                  </div>
                  <EnvelopeFiles files={techFiles} onView={setPreview}
                                 onRemove={envEditable ? removeEnvelopeFile : undefined}
                                 testid="bw-tech-files" />
                  {envEditable && (
                    <div style={{ padding: "0 20px 12px" }}>
                      <label className="pmc-btn pmc-btn--secondary pmc-btn--sm"
                             style={{ cursor: "pointer", display: "inline-block" }}
                             data-testid="bw-tech-add">
                        <input type="file" hidden accept="application/pdf,image/*"
                               onChange={(e) => {
                                 const f = e.target.files?.[0];
                                 if (f) uploadEnvelopeFile("technical", f);
                                 e.target.value = "";
                               }} />
                        + Add technical file
                      </label>
                    </div>
                  )}
                  <div className="bw-env">
                    <span className="i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-lock" /></svg></span>
                    <div>
                      <b>Commercial envelope</b>
                      <span className="s">
                        {commFiles.length
                          ? `${commFiles.length} file${commFiles.length === 1 ? "" : "s"}`
                          : "No files submitted yet"}
                      </span>
                    </div>
                    <span className="pmc-muted" style={{ fontSize: 12 }}>
                      {envelopes?.commercial?.sealed_at
                        ? `Sealed ${fmtDeadline(envelopes.commercial.sealed_at)}`
                        : commFiles.length ? "Submitted with bid" : "Not submitted"}
                    </span>
                  </div>
                  <EnvelopeFiles files={commFiles} onView={setPreview}
                                 onRemove={envEditable ? removeEnvelopeFile : undefined}
                                 testid="bw-comm-files" />
                  {envEditable && (
                    <div style={{ padding: "0 20px 12px" }}>
                      <label className="pmc-btn pmc-btn--secondary pmc-btn--sm"
                             style={{ cursor: "pointer", display: "inline-block" }}
                             data-testid="bw-comm-add">
                        <input type="file" hidden accept="application/pdf,image/*"
                               onChange={(e) => {
                                 const f = e.target.files?.[0];
                                 if (f) uploadEnvelopeFile("commercial", f);
                                 e.target.value = "";
                               }} />
                        + Add commercial file
                      </label>
                    </div>
                  )}
                  <div style={{ padding: "14px 20px", borderTop: "1px solid var(--line)" }}
                       className="pmc-muted">
                    <span style={{ fontSize: 13 }}>
                      You can view and download your own files any time. Nobody at PMC can
                      open them before the deadline; any unseal or replacement is logged on
                      the audit ledger.
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
                    <div className={techDone ? "bw-ck ok" : "bw-ck"}>
                      <svg className="pmc-ico" aria-hidden="true">
                        <use href={techDone ? "#i-check" : "#i-clock"} />
                      </svg>
                      {envelopes?.technical?.sealed_at
                        ? "Technical envelope sealed"
                        : "Technical envelope submitted"}
                    </div>
                    <div className={commDone ? "bw-ck ok" : "bw-ck"}>
                      <svg className="pmc-ico" aria-hidden="true">
                        <use href={commDone ? "#i-check" : "#i-clock"} />
                      </svg>
                      {envelopes?.commercial?.sealed_at
                        ? "Commercial envelope sealed"
                        : "Commercial envelope submitted"}
                    </div>
                    <div className={emdDone ? "bw-ck ok" : "bw-ck"}>
                      <svg className="pmc-ico" aria-hidden="true">
                        <use href={emdDone ? "#i-check" : "#i-clock"} />
                      </svg>
                      {emdNotRequired
                        ? "EMD not required for this tender"
                        : "EMD confirmed by escrow"}
                    </div>
                  </div>
                </div>
              </aside>
            </div>

            {/* v50x — in-page document preview (no more new-tab navigation).
                The key is appended raw: encodeURIComponent turned "/" into
                %2F, which CloudFront/nginx reject with a 404 — the "new page
                shows nothing" bug the vendor hit. */}
            {preview && (
              <>
                <div className="pmc-drawer-scrim" style={{ display: "block" }}
                     onClick={() => setPreview(null)} />
                <div role="dialog" aria-modal="true" data-testid="bw-proof-preview"
                     style={{ position: "fixed", inset: "5vh 6vw", zIndex: 70,
                              background: "var(--surface,#fff)",
                              border: "1px solid var(--line,#0001)",
                              borderRadius: "var(--radius-md,8px)",
                              boxShadow: "0 24px 60px rgba(0,0,0,.35)",
                              display: "flex", flexDirection: "column",
                              overflow: "hidden" }}>
                  <div style={{ display: "flex", justifyContent: "space-between",
                                alignItems: "center", gap: 12,
                                padding: "10px 14px",
                                borderBottom: "1px solid var(--line,#0001)" }}>
                    <b style={{ fontSize: 14, minWidth: 0, overflow: "hidden",
                                textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                       data-testid="bw-proof-preview-name">
                      {preview.filename}
                    </b>
                    <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
                      <a href={`${BACKEND_URL}/api/v1/uploads/files/${preview.key}`}
                         target="_blank" rel="noopener noreferrer"
                         className="pmc-btn pmc-btn--secondary pmc-btn--sm"
                         data-testid="bw-proof-preview-open-tab">
                        Open in new tab
                      </a>
                      <button type="button" onClick={() => setPreview(null)}
                              className="pmc-btn pmc-btn--ghost pmc-btn--sm"
                              data-testid="bw-proof-preview-close">
                        Close
                      </button>
                    </div>
                  </div>
                  {/\.(png|jpe?g|gif|webp)$/i.test(preview.filename) ? (
                    <img src={`${BACKEND_URL}/api/v1/uploads/files/${preview.key}`}
                         alt={preview.filename}
                         style={{ flex: 1, objectFit: "contain",
                                  background: "var(--surface-sunken,#f6f3ea)" }}
                         data-testid="bw-proof-preview-img" />
                  ) : (
                    <iframe src={`${BACKEND_URL}/api/v1/uploads/files/${preview.key}`}
                            title={preview.filename}
                            style={{ flex: 1, border: 0,
                                     background: "var(--surface-sunken,#f6f3ea)" }}
                            data-testid="bw-proof-preview-frame" />
                  )}
                </div>
              </>
            )}
          </>
        )}
      </VendorPortalChrome>
    </div>
  );
}
