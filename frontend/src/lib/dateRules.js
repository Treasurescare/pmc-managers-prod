/**
 * v52t — shared tender/notice date-chain validation.
 * Enforced live in Tender Builder (red hints), at create/publish gates,
 * and mirrored server-side in backend/routers/date_rules.py.
 */

const LABELS = {
  publish_date: "Publish Date",
  pre_bid_date: "Pre-Bid Meeting Date",
  doc_dl_start: "Document Download / Sale Start",
  doc_dl_end: "Document Download / Sale End",
  clarif_start: "Clarification Start",
  clarif_end: "Clarification End",
  sub_start: "Bid Submission Start",
  sub_end: "Bid Submission End",
  bid_award_date: "Bid Award Date",
};

const parse = (v) => {
  if (!v) return null;
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? null : d;
};

export const DATE_FIELD_LABELS = LABELS;

/**
 * Returns an array of human-readable violation strings (empty = valid).
 * Only pairs where BOTH dates are set are checked, so partially-filled
 * drafts stay editable. `requireToday` gates the "not in the past" checks
 * (skipped when editing legacy notices whose dates legitimately passed).
 */
export function tenderDateChainViolations(h = {}, { requireToday = true } = {}) {
  const errs = [];
  const get = (k) => parse(h[k]);
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());

  const subEnd = get("sub_end");
  if (requireToday && subEnd && subEnd < now)
    errs.push("Bid Submission End Date must be today or later");
  const pub = get("publish_date");
  if (requireToday && pub && pub < startOfToday)
    errs.push("Publish Date cannot be in the past");

  const order = (laterKey, earlierKey, { strict = false } = {}) => {
    const later = get(laterKey);
    const earlier = get(earlierKey);
    if (!later || !earlier) return;
    const bad = strict ? later <= earlier : later < earlier;
    if (bad)
      errs.push(`${LABELS[laterKey]} must be ${strict ? "after" : "on or after"} ${LABELS[earlierKey]}`);
  };

  order("pre_bid_date", "publish_date");
  order("doc_dl_start", "pre_bid_date");
  order("doc_dl_end", "doc_dl_start");
  order("clarif_start", "doc_dl_end");
  order("clarif_end", "clarif_start", { strict: true });
  order("sub_start", "clarif_end");
  order("sub_end", "sub_start");
  order("bid_award_date", "sub_end");
  return errs;
}
