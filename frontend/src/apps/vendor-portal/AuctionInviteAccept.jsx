import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { reverseAuctionApi, vendorApi, showApiError } from "@/lib/api";
import TopBar from "@/apps/shared/TopBar";

/**
 * v46b — Auction invitation landing page.
 *
 * Route: /vendor/auction/invite/:token
 * Flow: 1) resolve invite → shows auction summary
 *       2) if signed in as invited email → auto-accept + redirect to room
 *       3) otherwise → prompt to sign in
 */
export default function AuctionInviteAccept() {
  const { token } = useParams();
  const nav = useNavigate();
  const [inv, setInv]         = useState(null);
  const [me, setMe]           = useState(null);
  const [error, setError]     = useState(null);
  const [busy, setBusy]       = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await reverseAuctionApi.resolveInvite(token);
        if (!cancelled) setInv(r);
      } catch (e) {
        if (!cancelled) setError(e?.response?.data?.detail || "Invalid or expired invitation");
      }
      try {
        const v = await vendorApi.me();
        if (!cancelled) setMe(v);
      } catch {
        /* not signed in */
      }
    })();
    return () => { cancelled = true; };
  }, [token]);

  const accept = async () => {
    setBusy(true);
    try {
      const r = await reverseAuctionApi.acceptInvite(token);
      toast.success(`Joined as ${r.alias}`);
      nav(`/vendor/auction/${r.auction_id}`, { replace: true });
    } catch (e) { showApiError(e); }
    finally { setBusy(false); }
  };

  const goLogin = () => {
    // Round-trip via login — comes back to this URL after auth
    const redirect = encodeURIComponent(window.location.pathname);
    nav(`/vendor/login?redirect=${redirect}`);
  };

  return (
    <div className="min-h-screen bg-brand-pale" data-testid="auction-invite-page">
      <TopBar />
      <main className="max-w-2xl mx-auto px-6 py-16">
        {error && (
          <div className="border-2 border-red-500 bg-red-50 p-6 text-red-900" data-testid="ai-error">
            <div className="pmc-label mb-1">Invitation error</div>
            <div className="text-sm">{error}</div>
          </div>
        )}

        {!error && !inv && (
          <div className="text-brand-navy/60">Resolving invitation…</div>
        )}

        {inv && (
          <div className="border border-brand-navy/10 bg-white p-8">
            <div className="pmc-label">Reverse auction invitation</div>
            <h1 className="font-display text-3xl mt-2 text-brand-navy">{inv.title}</h1>
            <div className="text-sm text-brand-navy-soft font-mono mt-1">{inv.notice_ref}</div>

            <dl className="grid gap-3 sm:grid-cols-3 mt-6 text-sm">
              <div>
                <dt className="pmc-label">Status</dt>
                <dd className="font-semibold text-brand-navy mt-1 uppercase">{inv.status}</dd>
              </div>
              <div>
                <dt className="pmc-label">Starting price</dt>
                <dd className="font-mono text-brand-navy mt-1">{inv.currency} {inv.starting_price?.toLocaleString?.() ?? inv.starting_price}</dd>
              </div>
              <div>
                <dt className="pmc-label">Floor price</dt>
                <dd className="font-mono text-brand-navy mt-1">{inv.currency} {inv.floor_price?.toLocaleString?.() ?? inv.floor_price}</dd>
              </div>
            </dl>

            {me ? (
              me.email?.toLowerCase() === (inv.email || "").toLowerCase() ? (
                <button type="button" onClick={accept} disabled={busy}
                        data-testid="ai-accept"
                        className="mt-8 px-8 py-3 text-[12px] font-semibold uppercase tracking-widest bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-40">
                  {busy ? "Joining…" : "Accept & join auction"}
                </button>
              ) : (
                <div className="mt-8 border border-amber-500 bg-amber-50 p-4 text-sm text-amber-900" data-testid="ai-wrong-vendor">
                  This invitation is for <b>{inv.email}</b> — you are signed in as
                  <b> {me.email}</b>. Sign out and back in as {inv.email} to accept.
                </div>
              )
            ) : (
              <div className="mt-8">
                <div className="text-sm text-brand-navy/70">
                  This invitation is for <b>{inv.email}</b>. Sign in as that vendor
                  to accept and join the live room.
                </div>
                <button type="button" onClick={goLogin}
                        data-testid="ai-login"
                        className="mt-3 px-8 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
                  Sign in as vendor
                </button>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
