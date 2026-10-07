/**
 * EscrowTransactionsSection — refactor slice of EscrowPanel.
 * Owns the inbound-EMD form + the ledger with per-officer sign buttons and
 * the final release button. Kept pure UI + calls into escrowApi.
 */
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { adminApi, bidApi, escrowApi, showApiError } from "@/lib/api";
import { InfoDot } from "@/components/InfoDot";
import { useListPager } from "@/components/ListPager";

const ACTIONS = ["release_to_contractor", "release_to_vendor", "forfeit"];
const CLOSED = new Set(["released_to_contractor", "released_to_vendor", "forfeited", "cancelled"]);
const EMPTY_TX = {
  bid_ref: "", notice_ref: "", vendor_ref: "", escrow_account_id: "",
  amount: 0, currency: "USD", reference: "", notes: "",
};

function SignatureBox({ label, officer, sig }) {
  const ok = !!sig?.signed_at;
  return (
    <div className={`p-2 border ${ok ? "bg-emerald-50 border-emerald-200" : "bg-brand-pale border-brand-navy/10"}`}>
      <div className="text-[10px] uppercase tracking-widest text-brand-navy/60">
        {label} · {officer?.name}
      </div>
      {ok
        ? <div>Signed <b>{sig.action}</b> at {sig.signed_at?.slice(0, 19).replace("T", " ")}</div>
        : <div className="text-brand-navy/50 italic">Awaiting signature</div>}
    </div>
  );
}

function TransactionRow({ t, onSign, onRelease, onCancel }) {
  const sigs = t.signatures || {};
  const pmc = sigs.pmc || {};
  const esc = sigs.escrow_institution || {};
  const bothMatch = pmc.action && pmc.action === esc.action;
  const sideMismatch = pmc.action && esc.action && pmc.action !== esc.action;
  const closed = CLOSED.has(t.status);
  const [showTrail, setShowTrail] = useState(false);
  // 2026-09-19 — governance flag from backend (same email on both officers).
  // Fallback to snapshot check for older cached responses that predate the flag.
  const snap = t.escrow_account_snapshot || {};
  const snapPmcEmail = (snap.pmc_officer?.email || "").toLowerCase();
  const snapEscEmail = (snap.escrow_officer?.email || "").toLowerCase();
  const sameEmail = t.governance_ok === false || (snapPmcEmail && snapPmcEmail === snapEscEmail);
  // v51ag — expose row metadata so the parent MoneyFilterBar can filter by
  // tender/vendor text, status pill and created date.
  const createdAt = (t.received_at || t.created_at || "").slice(0, 10);
  return (
    <div className="p-4"
         data-testid={`escrow-tx-row-${t.id}`}
         data-row="1"
         data-status={(t.status || "").toLowerCase()}
         data-created-at={createdAt}
         data-creator={(t.recorded_by || "").toLowerCase()}
         data-tender-ref={t.notice_ref || t.bid_ref || ""}>
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <div>
          <span className="font-mono text-xs text-brand-navy-soft">{t.bid_ref}</span>
          <span className="mx-2 text-brand-navy/30">→</span>
          <span className="font-semibold text-brand-navy">{t.amount} {t.currency}</span>
          <span className="ml-3 text-[10px] uppercase tracking-widest px-2 py-0.5 bg-brand-pale text-brand-navy">{t.status}</span>
        </div>
        <div className="text-[11px] text-brand-navy/50">
          {snap.name} · received {(t.received_at || "").slice(0, 10)}
        </div>
      </div>
      {sameEmail && !closed && (
        <div className="mt-3 p-3 border border-red-300 bg-red-50 text-xs text-red-900 space-y-1"
             data-testid={`escrow-tx-governance-warn-${t.id}`}>
          <div className="font-semibold uppercase tracking-widest text-[10px]">⚠ Release blocked — same officer on both sides</div>
          <div>
            The joint account for this bid has the same email
            (<code className="font-mono">{snapPmcEmail || t.same_email_email}</code>)
            on both the PMC officer and the Escrow officer. Dual-signature is
            impossible until the two officers are distinct people, so
            <b> nothing will trigger no matter how many times you click Sign</b>.
          </div>
          <div>
            To unblock: go to <b>Joint Escrow Accounts</b> above → open this
            account → set the <b>Escrow officer</b> to a different email (an
            independent trustee at the escrow institution). Then come back and
            sign again on both sides.
          </div>
        </div>
      )}
      <div className="mt-2 grid gap-3 md:grid-cols-2 text-xs">
        <SignatureBox label="PMC officer" officer={snap.pmc_officer} sig={pmc}/>
        <SignatureBox label="Escrow officer" officer={snap.escrow_officer} sig={esc}/>
      </div>
      {!closed && (
        <div className="mt-3 border-t border-brand-navy/10 pt-3 space-y-2">
          {/* v51ag — tell the admin which officer side their email will map to */}
          <OfficerIdentityHint snap={snap} />
          <div className="flex flex-wrap gap-2">
          {ACTIONS.map((a) => (
            <button key={a} onClick={() => onSign(t, a)}
                    disabled={sameEmail}
                    data-testid={`escrow-sign-${a}-${t.id}`}
                    title={sameEmail ? "Fix the same-email governance issue above first" : `Sign this transaction with action: ${a.replace(/_/g, " ")}. Requires the officer's authentication.`}
                    className="px-3 py-1 text-[11px] uppercase tracking-widest border border-brand-navy/40 text-brand-navy hover:bg-brand-navy hover:text-white disabled:opacity-40 disabled:cursor-not-allowed">
              Sign · {a.replace(/_/g, " ")}
            </button>
          ))}
          <button onClick={() => onCancel(t)}
                  data-testid={`escrow-cancel-${t.id}`}
                  title="Cancel this ledger row (e.g. a duplicate). Only works before a release fires."
                  className="px-3 py-1 text-[11px] uppercase tracking-widest border border-red-400 text-red-700 hover:bg-red-50">
            Cancel row
          </button>
          <button onClick={() => onRelease(t)} disabled={!bothMatch || sameEmail}
                  data-testid={`escrow-release-${t.id}`}
                  title="Enabled only when BOTH officers have signed the identical action. Triggers the ledger release and the audit record."
                  className="ml-auto px-3 py-1 text-[11px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40 disabled:cursor-not-allowed">
            Release ({sameEmail ? "blocked — fix officers" : bothMatch ? "unlocked" : "needs both signatures"})
          </button>
          </div>
          {sideMismatch && (
            <div className="mt-3 p-3 bg-amber-50 border border-amber-300 text-xs text-amber-900"
                 data-testid={`escrow-tx-mismatch-${t.id}`}>
              <strong>Action mismatch — release blocked.</strong> PMC signed
              <code className="mx-1">{pmc.action}</code>, Escrow signed
              <code className="mx-1">{esc.action}</code>. Both officers must sign the
              <em> same </em>action for the release to fire. Whichever side wants
              to change needs to click the matching Sign button to overwrite their
              current signature.
            </div>
          )}
        </div>
      )}
      <div className="mt-3 flex items-center justify-between gap-2 flex-wrap text-xs">
        <button type="button" onClick={() => setShowTrail((v) => !v)}
                data-testid={`escrow-tx-trail-toggle-${t.id}`}
                className="text-brand-navy/70 underline hover:text-brand-navy">
          {showTrail ? "Hide" : "Show"} signature audit trail
          ({(t.audit_trail || []).length} event{(t.audit_trail || []).length === 1 ? "" : "s"})
        </button>
      </div>
      {showTrail && (
        <ol className="mt-2 space-y-1 text-xs border-l-2 border-brand-navy/15 pl-3"
            data-testid={`escrow-tx-trail-${t.id}`}>
          {(t.audit_trail || []).map((e, i) => (
            <li key={i} className="text-brand-navy/80">
              <span className="font-mono text-[11px] text-brand-navy/50 mr-2">
                {(e.at || "").slice(0, 19).replace("T", " ")}
              </span>
              <strong>{e.event}</strong>
              {e.by && <> · by <code className="text-brand-navy/70">{e.by}</code></>}
              {e.intended_action && <> · action <code>{e.intended_action}</code></>}
              {e.amount != null && <> · {e.currency} {e.amount}</>}
              {e.comment && <> · <em>{e.comment}</em></>}
            </li>
          ))}
          {(t.audit_trail || []).length === 0 && (
            <li className="italic text-brand-navy/40">No events yet.</li>
          )}
        </ol>
      )}
    </div>
  );
}

/** v51ag — small identity banner inside each pending transaction so the
 *  admin can see which officer side the signature will be recorded against.
 *  The sign endpoint only accepts the officer emails listed on the account.
 */
function OfficerIdentityHint({ snap }) {
  const pmcEmail = (snap.pmc_officer?.email || "");
  const escEmail = (snap.escrow_officer?.email || "");
  const [me, setMe] = useState("");
  useEffect(() => {
    adminApi.me().then((d) => setMe(d?.email || "")).catch(() => {});
  }, []);
  const meLc = me.toLowerCase();
  const asPmc = meLc && meLc === pmcEmail.toLowerCase();
  const asEsc = meLc && meLc === escEmail.toLowerCase();
  const neither = me && !asPmc && !asEsc && pmcEmail && escEmail;
  return (
    <div className={"text-[11px] px-2 py-1.5 border " + (
      neither ? "bg-amber-50 border-amber-300 text-amber-900"
              : "bg-brand-pale border-brand-navy/15 text-brand-navy/80"
    )} data-testid="escrow-identity-hint">
      <b>You are logged in as:</b> {me || "— (sign-in required)"}
      {asPmc && <> · will sign as <b>PMC officer</b> ({pmcEmail})</>}
      {asEsc && <> · will sign as <b>Escrow officer</b> ({escEmail})</>}
      {neither && (
        <> · ⚠ You are NOT one of the two officers on this account. The sign button will
          be rejected by the backend. Officers on record are
          PMC <code className="font-mono">{pmcEmail}</code> and
          Escrow <code className="font-mono">{escEmail}</code>. Those two people must
          each log in separately and sign the same action for Release to fire.</>
      )}
    </div>
  );
}

export default function EscrowTransactionsSection({ accounts, txs, onReload }) {
  const [showNew, setShowNew] = useState(false);
  const [tx, setTx] = useState(EMPTY_TX);
  // v51ak — bid picker for the inbound-EMD form: admins shouldn't have to
  // memorise bid refs. Bids with a paid EMD float to the top; picking one
  // auto-fills notice ref, vendor ref, amount and currency (all editable).
  const [bids, setBids] = useState([]);
  useEffect(() => {
    if (!showNew) return;
    bidApi.list({}).then((d) => {
      const items = Array.isArray(d) ? d : (d?.items || []);
      const live = items.filter((b) => !["withdrawn", "rejected"].includes(b.status));
      const paid = (b) => Number(b.emd_paid_amount || 0) > 0;
      setBids([...live].sort((a, b) => Number(paid(b)) - Number(paid(a))));
    }).catch(() => {});
  }, [showNew]);
  const activeAccounts = useMemo(() => accounts.filter((a) => a.active), [accounts]);
  const { paged, controls } = useListPager(txs, { testid: "escrow-tx-pager" });

  const createTx = async () => {
    if (!tx.escrow_account_id) return toast.error("Pick an escrow account");
    if (!tx.bid_ref || !tx.amount) return toast.error("Bid ref and amount are required");
    try {
      await escrowApi.initTransaction({ ...tx, amount: Number(tx.amount),
                                          currency: tx.currency.toUpperCase() });
      toast.success("EMD receipt recorded");
      setShowNew(false);
      setTx(EMPTY_TX);
      onReload();
    } catch (e) { showApiError(e, { fallbackTitle: "EMD receipt failed" }); }
  };

  const signAction = async (t, action) => {
    // v51ag — identity check: fetch the signed-in admin's email and verify
    // the account's officer snapshot includes it before firing the request.
    const snap = t.escrow_account_snapshot || {};
    const pmcEmail = (snap.pmc_officer?.email || "").toLowerCase();
    const escEmail = (snap.escrow_officer?.email || "").toLowerCase();
    let me = "";
    try { me = ((await adminApi.me())?.email || "").toLowerCase(); } catch {}
    const asPmc = me && me === pmcEmail;
    const asEsc = me && me === escEmail;
    if (me && pmcEmail && escEmail && !asPmc && !asEsc) {
      toast.error(
        "You are not an officer on this joint account — signing will be rejected.",
        {
          description: `Signed in as ${me}. Officers on record: PMC = ${pmcEmail}, ` +
            `Escrow = ${escEmail}. Log in as one of those two accounts, or amend the ` +
            "joint account in the editor above to include your email.",
          duration: 14000,
        },
      );
      return;
    }
    try {
      const result = await escrowApi.sign(t.id, { intended_action: action });
      const sigs = result?.signatures || {};
      const pmc = sigs.pmc || {};
      const esc = sigs.escrow_institution || {};
      const bothSigned = pmc.action && pmc.action === esc.action;
      if (bothSigned) {
        toast.success("Both officers signed — Release is now unlocked", {
          description: `Action: ${action.replace(/_/g, " ")}. Click Release to fire the transfer.`,
          duration: 8000,
        });
      } else {
        const mySide = pmc.signed_at && !esc.signed_at ? "PMC officer"
                     : esc.signed_at && !pmc.signed_at ? "Escrow officer"
                     : "one side";
        const missing = pmc.signed_at ? "the Escrow officer" : "the PMC officer";
        const missingEmail = pmc.signed_at ? snap.escrow_officer?.email : snap.pmc_officer?.email;
        toast.info(`Signed as ${mySide} — awaiting ${missing}`, {
          description:
            `The release will NOT trigger until ${missing}` +
            (missingEmail ? ` (${missingEmail})` : "") +
            ` logs in and also signs "${action.replace(/_/g, " ")}" on this transaction. ` +
            "Nothing has been transferred yet. Share the admin console link with them, " +
            "or amend the joint account above if the officer email is wrong.",
          duration: 14000,
        });
      }
      onReload();
    } catch (e) { showApiError(e, { fallbackTitle: "Sign refused" }); }
  };

  const release = async (t) => {
    const sigs = t.signatures || {};
    const pmc = sigs.pmc || {};
    const esc = sigs.escrow_institution || {};
    if (!pmc.action || pmc.action !== esc.action) {
      toast.error("Release blocked — both officers must sign the same action", {
        description: `Currently: PMC signed "${pmc.action || 'nothing'}", Escrow signed "${esc.action || 'nothing'}". They must match before Release can fire.`,
        duration: 10000,
      });
      return;
    }
    if (!window.confirm(`Release ${t.amount} ${t.currency} — ${pmc.action}?`)) return;
    try {
      await escrowApi.release(t.id, { action: pmc.action });
      toast.success("Release recorded — ledger closed", {
        description: `${t.amount} ${t.currency} · ${pmc.action.replace(/_/g, " ")} · ${t.bid_ref}. The bank rail will pick up this state next reconciliation cycle.`,
        duration: 8000,
      });
      onReload();
    } catch (e) { showApiError(e, { fallbackTitle: "Release failed" }); }
  };

  const cancelTx = async (t) => {
    if (!window.confirm(`Cancel this escrow transaction for ${t.bid_ref}? Use this to clear duplicates or mis-entries. The row stays in the audit trail.`)) return;
    try {
      await escrowApi.cancel(t.id);
      toast.success("Transaction cancelled — ledger row cleared");
      onReload();
    } catch (e) { showApiError(e, { fallbackTitle: "Cancel failed" }); }
  };

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="pmc-label">EMD transactions ledger</div>
          <div className="text-xs text-brand-navy/60">
            Inbound EMD receipts; each release requires both officers to sign the same action.
          </div>
        </div>
        <button onClick={() => setShowNew(!showNew)} data-testid="escrow-new-tx-toggle"
                disabled={activeAccounts.length === 0}
                className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40">
          {showNew ? "Cancel" : "Record inbound EMD"}
        </button>
      </div>

      {showNew && (
        <div className="border border-brand-navy/20 bg-white p-6 grid gap-3 md:grid-cols-3 mb-4" data-testid="escrow-new-tx-form">
          <label className="md:col-span-1"><span className="pmc-label">Escrow account</span>
            <select value={tx.escrow_account_id}
                    onChange={(e) => setTx({ ...tx, escrow_account_id: e.target.value })}
                    data-testid="escrow-tx-acc"
                    className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white">
              <option value="">Select…</option>
              {activeAccounts.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select></label>
          <label><span className="pmc-label">Bid<InfoDot tip="Pick the bid this EMD payment belongs to. Bids with a paid EMD float to the top. Picking a bid auto-fills notice ref, vendor ref, amount and currency — all still editable. Choose 'Manual entry' to type a ref by hand." /></span>
            <select value={tx.bid_ref && bids.some((b) => b.bid_ref === tx.bid_ref) ? tx.bid_ref : (tx.bid_ref ? "__manual" : "")}
                    onChange={(e) => {
                      const v = e.target.value;
                      if (v === "__manual") { setTx({ ...tx, bid_ref: tx.bid_ref, }); return; }
                      const b = bids.find((x) => x.bid_ref === v);
                      if (!b) { setTx({ ...tx, bid_ref: "" }); return; }
                      setTx({
                        ...tx,
                        bid_ref: b.bid_ref || "",
                        notice_ref: b.notice_ref || "",
                        vendor_ref: b.vendor_ref || "",
                        amount: Number(b.emd_paid_amount || b.emd_due_amount || 0) || tx.amount,
                        currency: (b.emd_currency || b.price_currency || tx.currency || "USD").toUpperCase(),
                      });
                    }}
                    data-testid="escrow-tx-bid"
                    className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white">
              <option value="">Select bid…</option>
              {bids.map((b) => (
                <option key={b.id} value={b.bid_ref}>
                  {b.bid_ref} — {b.notice_ref || "—"} · {b.vendor_ref || b.company_name || "—"}
                  {Number(b.emd_paid_amount || 0) > 0
                    ? ` · EMD paid ${Number(b.emd_paid_amount).toLocaleString()} ${(b.emd_currency || b.price_currency || "USD").toUpperCase()}`
                    : ""}
                </option>
              ))}
              <option value="__manual">— Manual entry (type a ref) —</option>
            </select>
            {tx.bid_ref !== "" && !bids.some((b) => b.bid_ref === tx.bid_ref) && (
              <input value={tx.bid_ref}
                     onChange={(e) => setTx({ ...tx, bid_ref: e.target.value })}
                     placeholder="Type bid ref, e.g. PMC-BID-2026-00048"
                     data-testid="escrow-tx-bid-manual"
                     className="mt-2 w-full px-3 py-2 border border-brand-navy/20"/>
            )}
          </label>
          <label><span className="pmc-label">Notice ref</span>
            <input value={tx.notice_ref} onChange={(e) => setTx({ ...tx, notice_ref: e.target.value })}
                   className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
          <label><span className="pmc-label">Vendor ref</span>
            <input value={tx.vendor_ref} onChange={(e) => setTx({ ...tx, vendor_ref: e.target.value })}
                   className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
          <label><span className="pmc-label">Amount</span>
            <input type="number" value={tx.amount || ""}
                   onChange={(e) => setTx({ ...tx, amount: e.target.value })}
                   data-testid="escrow-tx-amount"
                   className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
          <label><span className="pmc-label">Currency</span>
            <input value={tx.currency} onChange={(e) => setTx({ ...tx, currency: e.target.value })}
                   className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
          <label className="md:col-span-3"><span className="pmc-label">Bank reference / UTR</span>
            <input value={tx.reference} onChange={(e) => setTx({ ...tx, reference: e.target.value })}
                   className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
          <div className="md:col-span-3 flex justify-end">
            <button onClick={createTx} data-testid="escrow-tx-save"
                    className="px-6 py-2 text-[11px] uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90">
              Record receipt
            </button>
          </div>
        </div>
      )}

      <div className="border border-brand-navy/10 bg-white divide-y divide-brand-navy/10">
        {txs.length === 0 && <div className="p-6 text-sm text-brand-navy/50">No transactions yet.</div>}
        {paged.map((t) => (
          <TransactionRow key={t.id} t={t} onSign={signAction} onRelease={release} onCancel={cancelTx}/>
        ))}
        {controls}
      </div>
    </section>
  );
}
