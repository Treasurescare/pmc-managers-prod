/**
 * v53j — Admin "Recently awarded reverse auctions" panel. Lists every
 * closed+awarded auction with winner company, saving %, pipeline stage.
 * Mounted at /admin/e/awarded-auctions.
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { reverseAuctionApi, showApiError } from "@/lib/api";
import AdminEShell from "./AdminEShell";

const STAGE_LABELS = {
  emd_pending: "EMD pending",
  emd_paid: "EMD paid",
  escrow_accepted: "Escrow accepted",
  admin_flagged: "Flagged to certifier",
  certifier_cleared: "Certifier cleared",
  legal_cleared: "Legal cleared",
  accounting_cleared: "Accounting cleared",
  awarded: "Awarded (final)",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
  unknown: "Unknown",
};

export default function AdminAwardedAuctionsE() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    reverseAuctionApi.awardedList()
      .then((d) => setRows(d.items || []))
      .catch(showApiError)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen" style={{ background: "var(--brand-pale, #F3EFE4)" }}>
      <AdminEShell active="Awarded auctions"
                   crumb={<>Money &amp; compliance / <b>Awarded reverse auctions</b></>}>
        <div className="pmc-page" data-testid="awarded-auctions-page">
          <div className="pmc-page__head">
            <h1 className="pmc-page__title">Awarded reverse auctions</h1>
            <p className="pmc-page__lead">
              Every reverse auction that has been awarded, with winning
              company, savings versus starting price, and the current stage
              of the derived bid in the approval pipeline.
            </p>
          </div>
          <div className="pmc-panel">
            <div className="pmc-panel__body">
              {loading && <div style={{ padding: 16 }}>Loading…</div>}
              {!loading && rows.length === 0 && (
                <div style={{ padding: 24, color: "var(--on-chrome-muted)" }}>
                  No awarded reverse auctions yet. Awards appear here once
                  you click <strong>Award winner</strong> on a closed round.
                </div>
              )}
              {!loading && rows.length > 0 && (
                <table className="w-full text-sm" data-testid="awarded-auctions-table">
                  <thead>
                    <tr className="text-left border-b border-brand-navy/10 text-[11px] uppercase tracking-widest text-brand-navy/60">
                      <th className="py-2 pr-3">Auction</th>
                      <th className="py-2 pr-3">Winner</th>
                      <th className="py-2 pr-3 text-right">Final price</th>
                      <th className="py-2 pr-3 text-right">Saving</th>
                      <th className="py-2 pr-3">Pipeline stage</th>
                      <th className="py-2 pr-3">Awarded on</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r) => (
                      <tr key={r.auction_id} data-testid={`awarded-row-${r.auction_id}`}
                          className="border-b border-brand-navy/5 align-top">
                        <td className="py-3 pr-3">
                          <div className="font-semibold text-brand-navy">
                            <Link to={`/admin/e/auctions`} className="hover:underline">
                              {r.title}
                            </Link>
                          </div>
                          <div className="text-xs text-brand-navy/60">{r.notice_ref}</div>
                          {r.bid_ref && (
                            <div className="text-[11px] font-mono text-brand-navy/50 mt-1">
                              {r.bid_ref}
                            </div>
                          )}
                        </td>
                        <td className="py-3 pr-3">
                          <div className="text-brand-navy">
                            {r.winner_company || "—"}
                          </div>
                          <div className="text-xs text-brand-navy/60">
                            {r.winner_email || ""}
                          </div>
                        </td>
                        <td className="py-3 pr-3 text-right font-mono tabular-nums">
                          {r.currency} {Number(r.winning_price || 0).toLocaleString()}
                          <div className="text-[11px] text-brand-navy/50">
                            from {r.currency} {Number(r.starting_price || 0).toLocaleString()}
                          </div>
                        </td>
                        <td className="py-3 pr-3 text-right">
                          <span className={"font-mono tabular-nums font-semibold " +
                                           (r.saving_pct >= 10 ? "text-emerald-700" :
                                            r.saving_pct >= 1  ? "text-brand-navy" :
                                                                "text-brand-navy/50")}>
                            {r.saving_pct?.toFixed(1)}%
                          </span>
                        </td>
                        <td className="py-3 pr-3">
                          <span data-testid={`awarded-stage-${r.auction_id}`}
                                className={"inline-block text-[11px] uppercase tracking-widest px-2 py-0.5 border " +
                                  (r.pipeline_stage === "awarded"
                                    ? "border-emerald-500 text-emerald-700 bg-emerald-50"
                                    : "border-brand-navy/20 text-brand-navy bg-white")}>
                            {STAGE_LABELS[r.pipeline_stage] || r.pipeline_stage}
                          </span>
                        </td>
                        <td className="py-3 pr-3 text-xs text-brand-navy/70">
                          {r.awarded_at ? r.awarded_at.slice(0, 10) : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      </AdminEShell>
    </div>
  );
}
