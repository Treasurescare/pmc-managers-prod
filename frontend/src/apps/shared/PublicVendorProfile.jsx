import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { toast } from "sonner";
import { vendorRatingsApi, tenderProApi, showApiError } from "@/lib/api";
import { VendorTrustBadge } from "@/components/VendorTrustBadge";
import TopBar from "@/apps/shared/TopBar";
import Footer from "@/apps/shared/Footer";

/**
 * v46 — Public vendor profile page.
 * Anonymised aggregate + moderated review comments + a public buyer review
 * form. All submissions are queued for PMC moderation before they appear.
 */
export default function PublicVendorProfile() {
  const { vendorRef } = useParams();
  const [agg, setAgg]         = useState(null);
  const [rubrics, setRubrics] = useState([]);
  const [criteriaSet, setCriteriaSet] = useState(null);
  const [reviewer, setReviewer] = useState({ name: "", email: "", company: "" });
  const [scores, setScores]   = useState({});
  const [comment, setComment] = useState("");
  const [busy, setBusy]       = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const load = useCallback(async () => {
    try {
      const a = await vendorRatingsApi.publicAggregate(vendorRef);
      setAgg(a);
    } catch (e) { showApiError(e); }
    // Public list of criteria sets is not exposed; use the default rubric on
    // the public form. Falling back gracefully if none is configured yet.
    try {
      const list = await tenderProApi.listCriteriaSets();
      setRubrics(list);
      const def = list.find((s) => s.is_default) || list[0];
      if (def) {
        setCriteriaSet(def);
        const init = {};
        (def.criteria || []).forEach((c) => { init[c.code] = c.scale_min; });
        setScores(init);
      }
    } catch {
      // Public users are not authorised for the master — that's fine, the
      // backend will fall back to its default rubric.
    }
  }, [vendorRef]);

  useEffect(() => { load(); }, [load]);

  const submit = async () => {
    if (!reviewer.name.trim() || !reviewer.email.trim()) {
      return toast.error("Name and email are required so we can verify your review.");
    }
    if (!criteriaSet) {
      return toast.error("Rating rubric is not configured yet — please try again later.");
    }
    setBusy(true);
    try {
      const res = await vendorRatingsApi.publicSubmit({
        vendor_ref: vendorRef,
        criteria_set_id: criteriaSet.id,
        reviewer_name: reviewer.name.trim(),
        reviewer_email: reviewer.email.trim().toLowerCase(),
        reviewer_company: reviewer.company.trim() || null,
        scores,
        comment: comment.trim() || null,
      });
      toast.success(res.message || "Thanks — your review is pending moderation.");
      setSubmitted(true);
    } catch (e) { showApiError(e); }
    finally { setBusy(false); }
  };

  if (!agg) return (
    <div className="min-h-screen bg-brand-pale">
      <TopBar />
      <div className="p-16 text-center text-brand-navy/60">Loading…</div>
    </div>
  );

  return (
    <div className="min-h-screen bg-brand-pale flex flex-col" data-testid="public-vendor-profile">
      <TopBar />
      <main className="flex-1 max-w-5xl mx-auto w-full px-4 sm:px-6 lg:px-10 py-10 sm:py-14">
        <Link to="/" className="text-xs text-brand-navy-soft hover:underline uppercase tracking-widest">
          ← Back to notice board
        </Link>
        <header className="mt-4">
          <div className="pmc-label text-brand-navy-soft">{agg.vendor_ref}</div>
          <h1 className="font-display text-4xl sm:text-5xl text-brand-navy mt-2">
            {agg.company_name}
          </h1>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <VendorTrustBadge tier={agg.badge} score={agg.average_score ?? "—"} count={agg.count}
                                testid="public-vendor-badge" />
            {agg.country && <span className="text-xs text-brand-navy/60">Country · {agg.country}</span>}
          </div>
        </header>

        {/* Aggregate breakdown */}
        <section className="mt-8 grid gap-4 sm:grid-cols-3">
          <div className="border border-brand-navy/10 bg-white p-5">
            <div className="pmc-label">Overall score</div>
            <div className="font-display text-3xl text-brand-navy mt-1">
              {agg.average_score ?? "—"}<span className="text-base text-brand-navy/50">/100</span>
            </div>
            <div className="text-xs text-brand-navy/50 mt-1">from {agg.count} approved review{agg.count === 1 ? "" : "s"}</div>
          </div>
          <div className="border border-brand-navy/10 bg-white p-5">
            <div className="pmc-label">Reviewers</div>
            <ul className="mt-2 text-sm space-y-1">
              <li className="flex justify-between"><span>PMC management</span><span className="font-mono">{agg.by_reviewer_kind?.pmc_admin ?? 0}</span></li>
              <li className="flex justify-between"><span>Peer vendors</span><span className="font-mono">{agg.by_reviewer_kind?.peer_vendor ?? 0}</span></li>
              <li className="flex justify-between"><span>Public buyers</span><span className="font-mono">{agg.by_reviewer_kind?.public_buyer ?? 0}</span></li>
            </ul>
          </div>
          <div className="border border-brand-navy/10 bg-white p-5">
            <div className="pmc-label">Criteria averages</div>
            {Object.keys(agg.criteria_averages || {}).length === 0
              ? <div className="text-xs text-brand-navy/50 mt-2">No criteria averages yet.</div>
              : <ul className="mt-2 text-sm space-y-1">
                  {Object.entries(agg.criteria_averages || {}).map(([code, val]) => (
                    <li key={code} className="flex justify-between"><span className="capitalize">{code}</span><span className="font-mono">{val}/100</span></li>
                  ))}
                </ul>}
          </div>
        </section>

        {/* Recent comments */}
        {(agg.recent_comments || []).length > 0 && (
          <section className="mt-10">
            <div className="pmc-label mb-3">Recent moderated comments</div>
            <div className="space-y-3">
              {agg.recent_comments.map((c, i) => (
                <div key={i} className="border border-brand-navy/10 bg-white p-4"
                     data-testid={`public-comment-${i}`}>
                  <div className="flex justify-between items-baseline text-xs text-brand-navy/60">
                    <span className="capitalize">{(c.reviewer_kind || "").replace("_", " ")} · anonymised</span>
                    <span className="font-mono">{c.score}/100</span>
                  </div>
                  <p className="text-sm text-brand-navy mt-2 whitespace-pre-line">{c.comment}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Public review form */}
        <section className="mt-12 border-t border-brand-navy/10 pt-8">
          <div className="pmc-label">Leave a review</div>
          <h2 className="font-display text-2xl text-brand-navy mt-1">
            Rate <span className="text-brand-navy-soft">{agg.company_name}</span>
          </h2>
          <p className="text-sm text-brand-navy/60 mt-2 max-w-2xl">
            Your name and email are used only for verification and are never published.
            All public reviews go through PMC moderation before they appear.
          </p>

          {submitted ? (
            <div className="mt-6 border border-emerald-500/60 bg-emerald-50 p-5 text-sm text-emerald-900"
                 data-testid="public-review-submitted">
              Thanks — your review has been queued for PMC moderation. It will appear here
              once approved.
            </div>
          ) : (
            <div className="mt-6 grid gap-4 md:grid-cols-2 bg-white border border-brand-navy/10 p-5">
              <label className="text-xs uppercase tracking-widest text-brand-navy/60">
                Your full name
                <input value={reviewer.name} onChange={(e) => setReviewer({ ...reviewer, name: e.target.value })}
                       data-testid="pv-reviewer-name"
                       className="mt-1 w-full px-3 py-2 border normal-case tracking-normal" />
              </label>
              <label className="text-xs uppercase tracking-widest text-brand-navy/60">
                Your email (verification only, never shown)
                <input type="email" value={reviewer.email} onChange={(e) => setReviewer({ ...reviewer, email: e.target.value })}
                       data-testid="pv-reviewer-email"
                       className="mt-1 w-full px-3 py-2 border normal-case tracking-normal" />
              </label>
              <label className="text-xs uppercase tracking-widest text-brand-navy/60 md:col-span-2">
                Your company (optional)
                <input value={reviewer.company} onChange={(e) => setReviewer({ ...reviewer, company: e.target.value })}
                       data-testid="pv-reviewer-company"
                       className="mt-1 w-full px-3 py-2 border normal-case tracking-normal" />
              </label>

              {criteriaSet && (
                <div className="md:col-span-2">
                  <div className="pmc-label mt-2 mb-3">
                    Score each criterion · rubric: {criteriaSet.name}
                  </div>
                  <div className="grid gap-3">
                    {(criteriaSet.criteria || []).map((c) => (
                      <div key={c.code} className="grid grid-cols-[1fr_auto_auto] items-center gap-3 border-b border-brand-navy/5 py-2">
                        <div>
                          <div className="text-sm text-brand-navy">{c.label}</div>
                          {c.description && <div className="text-xs text-brand-navy/50">{c.description}</div>}
                        </div>
                        <input type="range" min={c.scale_min} max={c.scale_max} step={1}
                               value={scores[c.code] ?? c.scale_min}
                               onChange={(e) => setScores({ ...scores, [c.code]: parseInt(e.target.value, 10) })}
                               data-testid={`pv-score-${c.code}`}
                               className="w-40" />
                        <span className="font-mono text-brand-navy w-14 text-right">
                          {scores[c.code] ?? c.scale_min}/{c.scale_max}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <label className="md:col-span-2 text-xs uppercase tracking-widest text-brand-navy/60">
                Comment (optional, max 2000 chars)
                <textarea value={comment} onChange={(e) => setComment(e.target.value)} rows={4}
                          maxLength={2000}
                          data-testid="pv-comment"
                          className="mt-1 w-full px-3 py-2 border normal-case tracking-normal" />
              </label>

              <div className="md:col-span-2 flex justify-end">
                <button onClick={submit} disabled={busy || !criteriaSet}
                        data-testid="pv-submit"
                        className="px-6 py-3 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40">
                  {busy ? "Submitting…" : "Submit review for moderation"}
                </button>
              </div>
            </div>
          )}
        </section>
      </main>
      <Footer />
    </div>
  );
}
