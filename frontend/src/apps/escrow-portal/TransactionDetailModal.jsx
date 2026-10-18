/**
 * TransactionDetailModal — v54a.
 *
 * Opened from the escrow institution dashboard when a signatory clicks a
 * transaction row (Pending signatures / All transactions). Shows:
 *   • the two signatories (PMC + Institution) and whether each signed
 *   • the DocuSign envelope status + "Open in DocuSign" button when admin
 *     has issued one
 *   • a payment-entries ledger (payment-in / release / refund / fee) with
 *     proof upload + per-entry dual-sign
 *   • the full audit trail
 */
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { escrowMeApi, showApiError } from "@/lib/api";

const KIND_LABEL = {
  emd_in: "Payment-in (EMD received from bidder)",
  release_out: "Payment-out (release to vendor/contractor)",
  refund_out: "Refund (back to bidder)",
  fee_out: "Fee / charge (debit)",
};

const KIND_DIRECTION = {
  emd_in: "in",
  release_out: "out",
  refund_out: "out",
  fee_out: "out",
};

function fmtDate(iso) {
  if (!iso) return "—";
  return String(iso).slice(0, 19).replace("T", " ");
}

export default function TransactionDetailModal({ txId, onClose }) {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const dialogRef = useRef(null);

  const reload = () => {
    escrowMeApi.getTransaction(txId)
      .then(setData)
      .catch((e) => { showApiError(e); onClose?.(); });
  };

  useEffect(() => { if (txId) reload(); /* eslint-disable-next-line */ }, [txId]);
  useEffect(() => {
    const esc = (e) => e.key === "Escape" && onClose?.();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [onClose]);

  if (!txId) return null;

  const snap = data?.escrow_account_snapshot || {};
  const pmc = snap.pmc_officer || {};
  const esc = snap.escrow_officer || {};
  const sigs = data?.signatures || {};
  const pmcSig = sigs.pmc || {};
  const escSig = sigs.escrow_institution || {};
  const envelope = data?.docusign_envelope;
  const entries = data?.payment_entries || [];

  const openDocuSign = async () => {
    // v56d — Safari blocks window.open() that runs AFTER an await (outside the
    // click gesture). Open a blank tab synchronously, then navigate it once the
    // recipient-view URL arrives. Falls back to same-tab if the popup is blocked.
    const win = window.open("", "_blank");
    setBusy(true);
    try {
      const r = await escrowMeApi.getDocuSignUrl(txId);
      if (r?.url) {
        if (win) win.location.href = r.url;
        else window.location.href = r.url;
      } else {
        if (win) win.close();
        toast.info("Open your DocuSign email to sign", {
          description: r?.message || "DocuSign emailed the hosted-signing "
            + "link to the institution officer when the envelope was issued.",
          duration: 12000,
        });
      }
    } catch (e) {
      if (win) win.close();
      showApiError(e, { fallbackTitle: "Could not open DocuSign" });
    } finally { setBusy(false); }
  };

  const signEntry = async (peid, action) => {
    const confirm = action === "approve"
      ? "Approve this payment entry as the institution signatory?"
      : "Reject this payment entry?";
    if (!window.confirm(confirm)) return;
    try {
      await escrowMeApi.signPaymentEntry(peid, { action });
      toast.success(action === "approve" ? "Signed" : "Rejected");
      reload();
    } catch (e) { showApiError(e, { fallbackTitle: "Sign failed" }); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 overflow-y-auto"
         data-testid="escrow-tx-modal"
         onClick={(e) => { if (e.target === dialogRef.current) onClose?.(); }}
         ref={dialogRef}>
      <div className="my-10 w-[min(960px,95vw)] bg-white border border-brand-navy/15 shadow-2xl">
        {/* Header */}
        <div className="flex items-start justify-between px-6 py-4 border-b border-brand-navy/10">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-brand-navy/60">
              Escrow transaction
            </div>
            <h2 className="font-serif text-xl text-brand-navy">
              {data?.bid_ref || "Loading…"}
              <span className="ml-3 text-sm text-brand-navy/60">{data?.notice_ref}</span>
            </h2>
          </div>
          <button type="button" onClick={onClose}
                  data-testid="escrow-tx-modal-close"
                  className="text-brand-navy/60 hover:text-brand-navy text-2xl leading-none">×</button>
        </div>

        {!data ? (
          <div className="p-10 text-center text-sm text-brand-navy/50">Loading transaction…</div>
        ) : (
          <div className="p-6 space-y-6">
            {/* Summary */}
            <section className="grid md:grid-cols-4 gap-3 text-sm">
              <KV label="Amount" value={`${data.amount?.toLocaleString?.()} ${data.currency}`}/>
              <KV label="Status" value={data.status}/>
              <KV label="Received" value={fmtDate(data.received_at)}/>
              <KV label="Bank ref / UTR" value={data.reference || "—"} mono/>
            </section>

            {/* Signatories + DocuSign */}
            <section>
              <h3 className="font-serif text-brand-navy mb-2">Signatories &amp; DocuSign</h3>
              <div className="grid md:grid-cols-2 gap-3">
                <SignatureCard side="PMC officer" officer={pmc} sig={pmcSig}/>
                <SignatureCard side="Institution officer" officer={esc} sig={escSig}/>
              </div>
              <div className="mt-3 p-3 bg-brand-pale border border-brand-navy/10 text-sm">
                {envelope ? (
                  <div className="flex items-center justify-between gap-3 flex-wrap">
                    <div>
                      <div className="text-[11px] uppercase tracking-widest text-brand-navy/60">
                        DocuSign envelope
                      </div>
                      <div>
                        Status: <b>{envelope.status}</b> ·{" "}
                        <span className="text-xs text-brand-navy/60">
                          sent {fmtDate(envelope.created_at)}
                        </span>
                      </div>
                      <div className="text-xs text-brand-navy/60 mt-1">
                        PMC signs as <code>{pmc.email}</code> · Institution signs as <code>{esc.email}</code>.
                        DocuSign emails the hosted link to both parties; you can also click below.
                      </div>
                    </div>
                    <button type="button" onClick={openDocuSign} disabled={busy}
                            data-testid="escrow-tx-docusign-open"
                            className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40">
                      {busy ? "Opening…" : "Open in DocuSign to sign"}
                    </button>
                  </div>
                ) : (
                  <div className="text-brand-navy/70">
                    <b>No DocuSign document yet.</b> PMC admin has not issued a DocuSign
                    envelope for this transaction. Once they do, it will show up here with
                    an <b>Open in DocuSign</b> button and you will also receive the
                    hosted-signing email from DocuSign.
                  </div>
                )}
              </div>
            </section>

            {/* Payment entries */}
            <section>
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-serif text-brand-navy">Payment entries</h3>
                <button type="button" onClick={() => setShowForm((v) => !v)}
                        data-testid="escrow-pe-toggle"
                        className="px-3 py-1.5 text-[11px] uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-navy hover:text-white">
                  {showForm ? "Cancel" : "Add payment entry"}
                </button>
              </div>
              {showForm && (
                <PaymentEntryForm txId={txId}
                                   onSaved={() => { setShowForm(false); reload(); }}
                                   currency={data.currency}/>
              )}
              {entries.length === 0 && !showForm && (
                <div className="p-5 border border-brand-navy/10 bg-brand-pale text-sm text-brand-navy/60">
                  No payment entries yet. Use <b>Add payment entry</b> to record the EMD
                  you received from the bidder, any release/refund you make, or escrow
                  fees you deducted. Each entry must be signed by both the PMC officer
                  and your institution before it is treated as posted.
                </div>
              )}
              {entries.map((pe) => (
                <PaymentEntryRow key={pe.id} pe={pe} onSign={signEntry}/>
              ))}
            </section>

            {/* Audit trail */}
            <section>
              <h3 className="font-serif text-brand-navy mb-2">Audit trail</h3>
              <ol className="text-xs border-l-2 border-brand-navy/15 pl-3 space-y-1"
                  data-testid="escrow-tx-audit">
                {(data.audit_trail || []).map((e, i) => (
                  <li key={i} className="text-brand-navy/80">
                    <span className="font-mono text-[11px] text-brand-navy/50 mr-2">
                      {fmtDate(e.at)}
                    </span>
                    <b>{e.event}</b>
                    {e.by && <> · <code>{e.by}</code></>}
                    {e.intended_action && <> · action <code>{e.intended_action}</code></>}
                    {e.amount != null && <> · {e.currency} {e.amount}</>}
                    {e.envelope_id && <> · envelope <code>{String(e.envelope_id).slice(0, 8)}…</code></>}
                    {e.comment && <> · <em>{e.comment}</em></>}
                  </li>
                ))}
                {(data.audit_trail || []).length === 0 && (
                  <li className="italic text-brand-navy/40">No events yet.</li>
                )}
              </ol>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}

function KV({ label, value, mono }) {
  return (
    <div className="p-3 border border-brand-navy/10 bg-brand-pale">
      <div className="text-[10px] uppercase tracking-widest text-brand-navy/60">{label}</div>
      <div className={"mt-0.5 " + (mono ? "font-mono text-xs" : "font-semibold text-brand-navy")}>
        {value || "—"}
      </div>
    </div>
  );
}

function SignatureCard({ side, officer, sig }) {
  const ok = !!sig?.signed_at;
  return (
    <div className={"p-3 border " + (ok ? "bg-emerald-50 border-emerald-200" : "bg-brand-pale border-brand-navy/10")}>
      <div className="text-[10px] uppercase tracking-widest text-brand-navy/60">{side}</div>
      <div className="font-semibold text-brand-navy">{officer?.name || "—"}</div>
      <div className="text-xs font-mono text-brand-navy/60">{officer?.email || "—"}</div>
      <div className="mt-1 text-xs">
        {ok ? (
          <span className="text-emerald-700">
            Signed <b>{sig.action}</b> at {fmtDate(sig.signed_at)}
            {sig.via === "magic_link" && <> · via magic link</>}
          </span>
        ) : (
          <span className="text-brand-navy/50 italic">Awaiting signature</span>
        )}
      </div>
    </div>
  );
}

function PaymentEntryRow({ pe, onSign }) {
  const [expand, setExpand] = useState(false);
  const sigs = pe.signatures || {};
  const pmcOk = !!(sigs.pmc?.signed_at);
  const instOk = !!(sigs.escrow_institution?.signed_at);
  const amt = `${pe.amount?.toLocaleString?.()} ${pe.currency}`;
  return (
    <div className="border border-brand-navy/10 p-3 mt-2" data-testid={`escrow-pe-row-${pe.id}`}>
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <div className="text-sm">
            <span className="font-semibold">{amt}</span>
            <span className="mx-2 text-brand-navy/40">·</span>
            <span>{KIND_LABEL[pe.kind] || pe.kind}</span>
          </div>
          <div className="text-xs text-brand-navy/60 mt-0.5">
            {fmtDate(pe.dated_on)}
            {pe.bank_reference && <> · ref <code className="font-mono">{pe.bank_reference}</code></>}
            {pe.counterparty_name && <> · {pe.counterparty_name}</>}
          </div>
          {pe.notes && <div className="text-xs text-brand-navy/70 mt-1">{pe.notes}</div>}
        </div>
        <div className="text-right">
          <div className="text-[10px] uppercase tracking-widest text-brand-navy/60">
            {pe.status}
          </div>
          <div className="text-xs mt-0.5">
            PMC <span className={pmcOk ? "text-emerald-600" : "text-brand-navy/40"}>{pmcOk ? "✓" : "·"}</span>
            {" "}· Inst <span className={instOk ? "text-emerald-600" : "text-brand-navy/40"}>{instOk ? "✓" : "·"}</span>
          </div>
        </div>
      </div>
      <div className="mt-2 flex gap-2 flex-wrap">
        {!instOk && pe.status === "pending_signatures" && (
          <>
            <button type="button" onClick={() => onSign(pe.id, "approve")}
                    data-testid={`escrow-pe-sign-approve-${pe.id}`}
                    className="px-3 py-1 text-[11px] uppercase tracking-widest border border-emerald-500 text-emerald-800 bg-emerald-50 hover:bg-emerald-100">
              Sign · approve
            </button>
            <button type="button" onClick={() => onSign(pe.id, "reject")}
                    data-testid={`escrow-pe-sign-reject-${pe.id}`}
                    className="px-3 py-1 text-[11px] uppercase tracking-widest border border-red-400 text-red-700 hover:bg-red-50">
              Reject
            </button>
          </>
        )}
        {pe.proof?.data_url && (
          <a href={pe.proof.data_url} target="_blank" rel="noopener noreferrer"
             className="px-3 py-1 text-[11px] uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-navy hover:text-white">
            View proof {pe.proof.filename ? `· ${pe.proof.filename}` : ""}
          </a>
        )}
        <button type="button" onClick={() => setExpand((v) => !v)}
                className="ml-auto text-xs text-brand-navy/70 underline hover:text-brand-navy">
          {expand ? "Hide trail" : "Show trail"}
        </button>
      </div>
      {expand && (
        <ol className="mt-2 text-[11px] border-l-2 border-brand-navy/15 pl-3 space-y-1">
          {(pe.audit_trail || []).map((e, i) => (
            <li key={i}>
              <span className="font-mono text-brand-navy/50 mr-1">{fmtDate(e.at)}</span>
              <b>{e.event}</b>{e.by && <> · <code>{e.by}</code></>}{e.action && <> · {e.action}</>}
              {e.comment && <> · <em>{e.comment}</em></>}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

function PaymentEntryForm({ txId, onSaved, currency }) {
  const [form, setForm] = useState({
    kind: "emd_in", amount: "", currency: currency || "USD",
    dated_on: "", bank_reference: "", counterparty_name: "",
    counterparty_account: "", notes: "",
    proof_data_url: "", proof_filename: "",
  });
  const [busy, setBusy] = useState(false);
  const direction = KIND_DIRECTION[form.kind];

  const onFile = (f) => {
    if (!f) return;
    if (f.size > 2 * 1024 * 1024) {
      toast.error("Proof file must be under 2 MB");
      return;
    }
    const r = new FileReader();
    r.onload = () => setForm((s) => ({ ...s, proof_data_url: r.result, proof_filename: f.name }));
    r.readAsDataURL(f);
  };

  const submit = async () => {
    const amt = Number(form.amount);
    if (!amt || amt <= 0) return toast.error("Enter a positive amount");
    if (!form.currency) return toast.error("Currency is required");
    setBusy(true);
    try {
      await escrowMeApi.createPaymentEntry(txId, {
        direction, kind: form.kind, amount: amt,
        currency: form.currency.toUpperCase(),
        dated_on: form.dated_on || null,
        bank_reference: form.bank_reference || null,
        counterparty_name: form.counterparty_name || null,
        counterparty_account: form.counterparty_account || null,
        notes: form.notes || null,
        proof_data_url: form.proof_data_url || null,
        proof_filename: form.proof_filename || null,
      });
      toast.success("Payment entry recorded — waiting on dual signatures");
      onSaved?.();
    } catch (e) { showApiError(e, { fallbackTitle: "Could not record entry" }); }
    finally { setBusy(false); }
  };

  return (
    <div className="mb-3 p-4 border border-brand-navy/15 bg-white grid md:grid-cols-3 gap-3" data-testid="escrow-pe-form">
      <label className="md:col-span-3"><span className="pmc-label">Entry type</span>
        <select value={form.kind} data-testid="escrow-pe-kind"
                onChange={(e) => setForm({ ...form, kind: e.target.value })}
                className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white text-sm">
          {Object.entries(KIND_LABEL).map(([k, label]) => (
            <option key={k} value={k}>{label}</option>
          ))}
        </select>
      </label>
      <label><span className="pmc-label">Amount</span>
        <input type="number" step="0.01" value={form.amount} data-testid="escrow-pe-amount"
               onChange={(e) => setForm({ ...form, amount: e.target.value })}
               className="mt-1 w-full px-3 py-2 border border-brand-navy/20 text-sm"/>
      </label>
      <label><span className="pmc-label">Currency</span>
        <input value={form.currency} data-testid="escrow-pe-currency"
               onChange={(e) => setForm({ ...form, currency: e.target.value })}
               className="mt-1 w-full px-3 py-2 border border-brand-navy/20 text-sm"/>
      </label>
      <label><span className="pmc-label">Dated on</span>
        <input type="date" value={form.dated_on}
               onChange={(e) => setForm({ ...form, dated_on: e.target.value })}
               className="mt-1 w-full px-3 py-2 border border-brand-navy/20 text-sm"/>
      </label>
      <label><span className="pmc-label">Bank reference / UTR</span>
        <input value={form.bank_reference} data-testid="escrow-pe-ref"
               onChange={(e) => setForm({ ...form, bank_reference: e.target.value })}
               className="mt-1 w-full px-3 py-2 border border-brand-navy/20 text-sm"/>
      </label>
      <label><span className="pmc-label">Counterparty name</span>
        <input value={form.counterparty_name}
               placeholder={direction === "in" ? "Bidder / payer" : "Beneficiary"}
               onChange={(e) => setForm({ ...form, counterparty_name: e.target.value })}
               className="mt-1 w-full px-3 py-2 border border-brand-navy/20 text-sm"/>
      </label>
      <label><span className="pmc-label">Counterparty account</span>
        <input value={form.counterparty_account}
               onChange={(e) => setForm({ ...form, counterparty_account: e.target.value })}
               className="mt-1 w-full px-3 py-2 border border-brand-navy/20 text-sm"/>
      </label>
      <label className="md:col-span-3"><span className="pmc-label">Notes</span>
        <input value={form.notes}
               onChange={(e) => setForm({ ...form, notes: e.target.value })}
               className="mt-1 w-full px-3 py-2 border border-brand-navy/20 text-sm"/>
      </label>
      <label className="md:col-span-3"><span className="pmc-label">Proof (receipt / wire slip · max 2 MB)</span>
        <input type="file" accept="application/pdf,image/*" data-testid="escrow-pe-proof"
               onChange={(e) => onFile(e.target.files?.[0])}
               className="mt-1 w-full text-sm"/>
        {form.proof_filename && (
          <div className="text-xs text-brand-navy/60 mt-1">Attached: {form.proof_filename}</div>
        )}
      </label>
      <div className="md:col-span-3 flex justify-end">
        <button type="button" onClick={submit} disabled={busy} data-testid="escrow-pe-save"
                className="px-5 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40">
          {busy ? "Saving…" : "Record payment entry"}
        </button>
      </div>
    </div>
  );
}
