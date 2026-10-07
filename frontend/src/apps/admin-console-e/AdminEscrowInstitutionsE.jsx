import { useEffect, useState } from "react";
import { toast } from "sonner";
import AdminEShell from "./AdminEShell";
import { api, showApiError } from "@/lib/api";
/**
 * v51am — Admin review queue for Escrow Institution registrations.
 * Lists all institutions with status filter, drill-in panel showing core
 * details, signatories, banking coords and uploaded documents, plus
 * approve / needs-clarification / reject actions. Approve fires the
 * magic-link email automatically (handled server-side).
 */
export default function AdminEscrowInstitutionsE() {
  const [items, setItems] = useState([]);
  const [status, setStatus] = useState("");
  const [sel, setSel] = useState(null);
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const q = status ? `?status=${status}` : "";
      const r = (await api.get(`/api/v1/escrow-institutions${q}`)).data;
      setItems(r.items || []);
    } catch (e) { showApiError(e); }
  };
  useEffect(() => { load(); /* eslint-disable-line */ }, [status]);

  const decide = async (action) => {
    if (!sel) return;
    if (!notes && action !== "approve") {
      return toast.error("Add a reviewer note explaining the decision.");
    }
    setBusy(true);
    try {
      await api.post(`/api/v1/escrow-institutions/${sel.id}/decision`,
                     null, { params: { action, notes: notes || undefined } });
      toast.success(action === "approve" ? "Approved — magic-link email dispatched" :
                     action === "reject" ? "Rejected" : "Clarification requested");
      setSel(null); setNotes("");
      await load();
    } catch (e) { showApiError(e); }
    finally { setBusy(false); }
  };

  const statusChip = (s) => {
    const map = {
      approved: "bg-emerald-50 text-emerald-900 border-emerald-200",
      rejected: "bg-red-50 text-red-900 border-red-200",
      submitted: "bg-amber-50 text-amber-900 border-amber-300",
      under_review: "bg-amber-50 text-amber-900 border-amber-300",
      needs_clarification: "bg-sky-50 text-sky-900 border-sky-300",
      draft: "bg-slate-50 text-slate-700 border-slate-200",
    };
    return (
      <span className={`inline-block text-[10px] uppercase tracking-widest px-2 py-0.5 border ${map[s] || map.draft}`}>
        {s}
      </span>
    );
  };

  return (
    <div className="min-h-screen" style={{ background: "var(--brand-pale, #F3EFE4)" }}>
      <AdminEShell active="Escrow institutions"
                    crumb={<>Money &amp; compliance / <b>Escrow institutions</b></>}>
        <div className="p-6" data-testid="admin-escrow-insts-page">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
            <div>
              <h1 className="text-2xl font-semibold text-brand-navy">Escrow institution registrations</h1>
              <p className="text-sm text-brand-navy/60 mt-1">
                Review banks and trustees applying to hold tender EMD / milestone funds under dual-signature control.
                Approve to issue the signatory magic link automatically.
              </p>
            </div>
            <select value={status} onChange={(e) => setStatus(e.target.value)}
                    data-testid="admin-escrow-insts-filter"
                    className="px-3 py-2 text-sm border border-brand-navy/20 bg-white">
              <option value="">All statuses</option>
              <option value="submitted">Submitted (new)</option>
              <option value="under_review">Under review</option>
              <option value="needs_clarification">Needs clarification</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="draft">Draft</option>
            </select>
          </div>

          <div className="grid gap-4 lg:grid-cols-[5fr_7fr]">
            <section className="bg-white border border-brand-navy/15">
              <div className="pmc-label p-4 border-b border-brand-navy/10">
                Pipeline · {items.length}
              </div>              <ul className="divide-y divide-brand-navy/10 max-h-[70vh] overflow-y-auto"
                  data-testid="admin-escrow-insts-list">
                {items.length === 0 && (
                  <li className="p-6 text-sm text-brand-navy/50">No registrations match this filter yet.</li>
                )}
                {items.map((i) => (
                  <li key={i.id}>
                    <button onClick={() => { setSel(i); setNotes(i.reviewer_notes || ""); }}
                            data-testid={`admin-escrow-inst-row-${i.id}`}
                            className={`w-full text-left p-4 hover:bg-brand-navy/5 transition-colors ${sel?.id === i.id ? "bg-brand-navy/5" : ""}`}>
                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        <strong className="text-brand-navy">{i.legal_name}</strong>
                        {statusChip(i.status)}
                      </div>
                      <div className="text-xs text-brand-navy/60 mt-1">
                        {i.country} · reg {i.reg_number || "—"} · {i.primary_contact_email}
                      </div>
                      <div className="text-[10px] text-brand-navy/40 mt-1">
                        {(i.created_at || "").slice(0, 16).replace("T", " ")}
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            </section>

            <section className="bg-white border border-brand-navy/15 p-6" data-testid="admin-escrow-inst-detail">
              {!sel && <div className="text-sm text-brand-navy/50">Pick a registration to review it.</div>}
              {sel && (
                <div className="space-y-5">
                  <div>
                    <div className="pmc-label">Institution</div>
                    <h2 className="text-xl font-semibold text-brand-navy mt-1">{sel.legal_name}</h2>
                    <div className="mt-1">{statusChip(sel.status)}</div>
                  </div>

                  <div className="grid gap-3 md:grid-cols-2 text-sm">
                    <F label="Trading name" v={sel.trading_name} />
                    <F label="Country" v={sel.country} />
                    <F label="Registration number" v={sel.reg_number} mono />
                    <F label="Tax ID" v={sel.tax_id} mono />
                    <F label="Regulator" v={sel.regulator} />
                    <F label="Licence number" v={sel.licence_number} mono />
                    <F label="Licence expiry" v={sel.licence_expiry} />
                    <F label="Website" v={sel.website} />
                    <F label="Primary contact email" v={sel.primary_contact_email} mono />
                    <F label="Primary contact phone" v={sel.primary_contact_phone} />
                    <div className="md:col-span-2">
                      <F label="Registered address" v={sel.registered_address} />
                    </div>
                  </div>

                  <div>
                    <div className="pmc-label mb-2">Signatories · {(sel.signatories || []).length}</div>
                    <ul className="text-sm space-y-1" data-testid="admin-escrow-inst-signatories">
                      {(sel.signatories || []).map((s, i) => (
                        <li key={i} className="border border-brand-navy/10 p-2">
                          <strong>{s.name}</strong> · {s.designation}
                          <div className="text-xs text-brand-navy/60">{s.email} · {s.phone || "—"}</div>
                        </li>
                      ))}
                      {(sel.signatories || []).length === 0 && <li className="text-xs text-brand-navy/50">No signatories listed.</li>}
                    </ul>
                  </div>

                  <div>
                    <div className="pmc-label mb-2">Banking coordinates · {(sel.banking || []).length}</div>
                    <ul className="text-sm space-y-1" data-testid="admin-escrow-inst-banking">
                      {(sel.banking || []).map((b, i) => (
                        <li key={i} className="border border-brand-navy/10 p-2">
                          <strong>{b.account_name}</strong> · {b.institution_name} ({b.currency})
                          <div className="text-xs text-brand-navy/60 font-mono">
                            Acct {b.account_number} · IBAN {b.iban || "—"} · SWIFT {b.swift || "—"}
                          </div>
                        </li>
                      ))}
                      {(sel.banking || []).length === 0 && <li className="text-xs text-brand-navy/50">No banking coordinates on file.</li>}
                    </ul>
                  </div>

                  <div>
                    <div className="pmc-label mb-2">Uploaded documents</div>
                    <ul className="text-sm space-y-1" data-testid="admin-escrow-inst-documents">
                      {Object.entries(sel.documents || {}).map(([slot, d]) => (
                        <li key={slot} className="border border-brand-navy/10 p-2 flex items-center justify-between gap-2">
                          <div>
                            <strong>{slot.replace(/_/g, " ")}</strong>
                            <div className="text-xs text-brand-navy/60">
                              {d?.filename || "—"} · uploaded {(d?.uploaded_at || "").slice(0, 10)}
                            </div>
                          </div>
                          {d?.key && (
                            <a href={`/api/v1/uploads/files/${d.key}`} target="_blank" rel="noopener noreferrer"
                               className="text-[10px] uppercase tracking-widest px-3 py-1 border border-brand-navy/20 hover:bg-brand-navy/5">
                              Open
                            </a>
                          )}
                        </li>
                      ))}
                      {Object.keys(sel.documents || {}).length === 0 && (
                        <li className="text-xs text-brand-navy/50">No documents uploaded.</li>
                      )}
                    </ul>
                  </div>

                  {sel.reviewer_notes && (
                    <div className="text-xs text-brand-navy/70 border-l-2 border-brand-navy/30 pl-3">
                      Previous reviewer note: <em>{sel.reviewer_notes}</em>
                    </div>
                  )}

                  <div>
                    <label className="pmc-label text-[10px]">Reviewer note (required for reject / clarification)</label>
                    <textarea rows={3} value={notes} onChange={(e) => setNotes(e.target.value)}
                              data-testid="admin-escrow-inst-notes"
                              className="mt-1 w-full border border-brand-navy/20 p-2 text-sm"
                              placeholder="Why are we approving / rejecting / asking for more info?" />
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <button onClick={() => decide("approve")} disabled={busy}
                            data-testid="admin-escrow-inst-approve"
                            className="px-5 py-2 text-xs uppercase tracking-widest bg-emerald-700 text-white disabled:opacity-50 hover:bg-emerald-800">
                      Approve &amp; send magic link
                    </button>
                    <button onClick={() => decide("needs_clarification")} disabled={busy}
                            data-testid="admin-escrow-inst-clarify"
                            className="px-5 py-2 text-xs uppercase tracking-widest border border-sky-600 text-sky-800 disabled:opacity-50 hover:bg-sky-50">
                      Request clarification
                    </button>
                    <button onClick={() => decide("reject")} disabled={busy}
                            data-testid="admin-escrow-inst-reject"
                            className="px-5 py-2 text-xs uppercase tracking-widest border border-red-600 text-red-800 disabled:opacity-50 hover:bg-red-50">
                      Reject
                    </button>
                  </div>
                </div>
              )}
            </section>
          </div>

          {/* v51an — Notice ↔ Escrow account picker. Admin can assign a
              specific joint account to each live notice so the auto-ledger
              routes vendor EMD receipts there. */}
          <NoticeAccountPicker />
        </div>
      </AdminEShell>
    </div>
  );
}

function F({ label, v, mono }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-widest text-slate-500">{label}</div>
      <div className={`text-slate-800 text-sm ${mono ? "font-mono text-xs" : ""}`}>{v || "—"}</div>
    </div>
  );
}

function NoticeAccountPicker() {
  const [notices, setNotices] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [saving, setSaving] = useState({});

  useEffect(() => {
    (async () => {
      try {
        const [nRes, aRes] = await Promise.all([
          api.get("/api/v1/notices/admin/all"),
          api.get("/api/v1/escrow/accounts", { params: { active_only: true } }),
        ]);
        const list = Array.isArray(nRes.data) ? nRes.data : (nRes.data.items || []);
        setNotices(list);
        setAccounts(aRes.data.items || []);
      } catch (e) { showApiError(e); }
    })();
  }, []);

  const save = async (notice_ref, escrow_account_id) => {
    setSaving((s) => ({ ...s, [notice_ref]: true }));
    try {
      await api.patch(`/api/v1/notices/${notice_ref}`, { escrow_account_id: escrow_account_id || null });
      toast.success(escrow_account_id
        ? "Escrow account linked to this notice"
        : "Cleared escrow account on this notice");
      setNotices((prev) => prev.map((n) =>
        n.notice_ref === notice_ref ? { ...n, escrow_account_id } : n));
    } catch (e) { showApiError(e); }
    finally { setSaving((s) => ({ ...s, [notice_ref]: false })); }
  };

  const live = notices.filter((n) => n.is_published).slice(0, 50);

  return (
    <section className="mt-8 bg-white border border-brand-navy/15"
             data-testid="notice-account-picker">
      <div className="pmc-label p-4 border-b border-brand-navy/10 flex items-center justify-between gap-2 flex-wrap">
        <span>Notice ↔ Escrow account routing</span>
        <span className="text-[10px] text-brand-navy/50 normal-case tracking-normal">
          Pin a joint account to each published notice so EMD receipts auto-post to the right ledger.
          Unassigned notices fall back to the newest active account.
        </span>
      </div>
      {live.length === 0 ? (
        <div className="p-6 text-sm text-brand-navy/50">No published notices yet.</div>
      ) : (
        <table className="w-full text-sm">
          <thead className="text-left text-[10px] uppercase tracking-widest text-brand-navy/50">
            <tr>
              <th className="p-3">Notice ref</th>
              <th className="p-3">Title</th>
              <th className="p-3">Escrow account</th>
            </tr>
          </thead>
          <tbody>
            {live.map((n) => (
              <tr key={n.notice_ref} className="border-t border-brand-navy/5"
                  data-testid={`notice-account-row-${n.notice_ref}`}>
                <td className="p-3 font-mono text-xs">{n.notice_ref}</td>
                <td className="p-3 max-w-xs truncate" title={n.title}>{n.title}</td>
                <td className="p-3">
                  <select value={n.escrow_account_id || ""}
                          onChange={(e) => save(n.notice_ref, e.target.value || null)}
                          disabled={saving[n.notice_ref]}
                          data-testid={`notice-account-select-${n.notice_ref}`}
                          className="px-2 py-1 border border-brand-navy/20 text-xs bg-white min-w-[260px]">
                    <option value="">— Use newest active account (default) —</option>
                    {accounts.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.name} · {a.institution} · {a.currency}
                      </option>
                    ))}
                  </select>
                  {saving[n.notice_ref] && (
                    <span className="ml-2 text-[10px] text-brand-navy/50">saving…</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
