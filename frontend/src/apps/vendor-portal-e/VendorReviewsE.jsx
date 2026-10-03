import { useState } from "react";
import { useUiTheme } from "@/context/UiThemeContext";
import { toast } from "sonner";
import VendorPortalChrome from "./VendorPortalChrome";

/**
 * v50v — Vendor Reviews, rewritten from the static Option-E mockup so the
 * `href="#"` Reply links can't be intercepted by PmcLinkPatcher (which
 * previously routed clicks to the bids catch-all).
 *
 * Static reviews are retained as content until the review service is wired,
 * but every action is now a real React handler.
 */

const REVIEWS = [
  {
    id: "026-0009",
    title: "Medical gas pipeline systems",
    ref: "Contract 026-0009",
    score: 82,
    scoreLabel: "Good",
    comment: "Installation met specification; handover documents complete. One milestone slipped by 6 days, communicated early.",
    author: "PMC contracts team",
    date: "20 Sep 2026",
  },
  {
    id: "wave-1",
    title: "Modular OTs — Wave 1",
    ref: "Debrief",
    score: 78,
    scoreLabel: "Good",
    comment: "Strong method statement; price was not competitive against L1.",
    author: "Evaluation committee",
    date: "9 Sep 2026",
  },
];

function ReplyDialog({ review, onClose, onSend }) {
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const submit = async () => {
    if (!text.trim()) { toast.error("Write a reply before sending"); return; }
    setSending(true);
    try { await onSend(text.trim()); } finally { setSending(false); }
  };
  return (
    <>
      <div className="pmc-drawer-scrim" style={{ display: "block" }} onClick={onClose} />
      <div role="dialog" aria-modal="true" data-testid="review-reply-dialog"
           style={{ position: "fixed", top: "50%", left: "50%",
                    transform: "translate(-50%,-50%)", width: "min(560px,92vw)",
                    background: "var(--surface,#fff)",
                    border: "1px solid var(--line,#0001)",
                    borderRadius: "var(--radius-md,6px)", padding: 24, zIndex: 60,
                    boxShadow: "0 20px 50px rgba(0,0,0,.25)" }}>
        <div className="pmc-eyebrow">Reply to review</div>
        <h2 style={{ margin: "6px 0 4px" }}>{review.title}</h2>
        <div className="pmc-muted" style={{ fontSize: 12, marginBottom: 12 }}>
          {review.author} · {review.date}
        </div>
        <blockquote style={{ fontSize: 13, color: "var(--ink-muted)",
                             background: "var(--surface-sunken,#f6f3ea)",
                             padding: 12, borderRadius: 4, margin: "0 0 16px" }}>
          {review.comment}
        </blockquote>
        <label>
          <span className="pmc-eyebrow">Your reply (moderated)</span>
          <textarea value={text} onChange={(e) => setText(e.target.value)}
                    rows={6} maxLength={1000}
                    className="pmc-input"
                    style={{ width: "100%", marginTop: 4 }}
                    placeholder="Keep it factual. One reply per review."
                    data-testid="review-reply-textarea" />
        </label>
        <div style={{ marginTop: 16, display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button type="button" onClick={onClose}
                  className="pmc-btn pmc-btn--secondary"
                  data-testid="review-reply-cancel">Cancel</button>
          <button type="button" onClick={submit} disabled={sending}
                  className="pmc-btn pmc-btn--primary"
                  data-testid="review-reply-send">
            {sending ? "Sending…" : "Send for moderation"}
          </button>
        </div>
      </div>
    </>
  );
}

export default function VendorReviewsE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  const [replyTo, setReplyTo] = useState(null);

  const sendReply = async (text) => {
    // Review-reply service not wired yet; send via a mailto fallback so the
    // vendor's reply reaches the PMC contracts desk and we log the attempt.
    const mailto = `mailto:tenders@pmcmanagers.com?subject=${encodeURIComponent(`Reply · ${replyTo.ref || replyTo.title}`)}&body=${encodeURIComponent(text)}`;
    window.open(mailto, "_self");
    toast.success("Reply drafted — your mail client is opening with the PMC desk pre-filled");
    setReplyTo(null);
  };

  if (!isE && Legacy) return <Legacy />;
  if (!isE) return null;

  return (
    <div data-testid="vendor-reviews-e" data-pmc-e-page="vendor-reviews-e">
      <VendorPortalChrome active="/vendor/reviews">
        <div className="sp-head">
          <div>
            <div className="pmc-eyebrow">Reviews</div>
            <h1 data-testid="vrev-heading">Your reputation on the board</h1>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "320px minmax(0,1fr)",
                      gap: 24, alignItems: "start" }}>
          <div className="pmc-panel" style={{ padding: 24, textAlign: "center" }}>
            <div className="pmc-figure" style={{ fontSize: 56, lineHeight: "60px" }}>80</div>
            <div style={{ fontWeight: 600 }}>Good</div>
            <div className="pmc-muted" style={{ fontSize: 13, marginBottom: 16 }}>
              from {REVIEWS.length} buyer review{REVIEWS.length === 1 ? "" : "s"}
            </div>
            {[["Quality", 84], ["On time", 76], ["Documentation", 82], ["Communication", 78]].map(([k, v]) => (
              <div key={k}
                   style={{ display: "grid", gridTemplateColumns: "110px 1fr 28px",
                            gap: 10, alignItems: "center", fontSize: 13,
                            marginTop: 8, textAlign: "left" }}>
                <span>{k}</span>
                <span className="bar"><i style={{ width: `${v}%` }}></i></span>
                <b>{v}</b>
              </div>
            ))}
          </div>

          <div style={{ display: "grid", gap: 16 }}>
            {REVIEWS.map((r) => (
              <section key={r.id} className="pmc-panel"
                       style={{ padding: 20 }}
                       data-testid={`vrev-item-${r.id}`}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <div>
                    <b>{r.title}</b>
                    <div className="pmc-ref">{r.ref}</div>
                  </div>
                  <span className="pmc-pill pmc-pill--success">{r.score} · {r.scoreLabel}</span>
                </div>
                <p style={{ margin: "12px 0 0", fontSize: 14, lineHeight: "22px",
                            color: "var(--ink-muted)" }}>
                  “{r.comment}”
                </p>
                <div className="pmc-muted" style={{ fontSize: 12, marginTop: 10,
                                                      display: "flex", alignItems: "center",
                                                      gap: 8 }}>
                  <span>{r.author} · {r.date}</span>·
                  <button type="button" onClick={() => setReplyTo(r)}
                          style={{ background: "transparent", border: 0,
                                   color: "var(--brand-navy,#0B1A14)",
                                   textDecoration: "underline", cursor: "pointer",
                                   padding: 0, fontSize: 12 }}
                          data-testid={`vrev-reply-${r.id}`}>
                    Reply
                  </button>
                </div>
              </section>
            ))}
            <div className="pmc-callout pmc-callout--info">
              <svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg>
              <div>
                Reviews come from buyers after contracts and evaluations, and are moderated
                before publishing. You can reply once to each.
              </div>
            </div>
          </div>
        </div>
      </VendorPortalChrome>

      {replyTo && (
        <ReplyDialog review={replyTo}
                     onClose={() => setReplyTo(null)}
                     onSend={sendReply} />
      )}
    </div>
  );
}
