import { useEffect, useState } from "react";
import { toast } from "sonner";
import AdminEShell from "./AdminEShell";
import AdminEscrowChart from "./AdminEscrowChart";
import { api, showApiError, uploadsApi } from "@/lib/api";
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
  const [search, setSearch] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [sel, setSel] = useState(null);
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  // v52cx — invite drawer.
  const [inviteOpen, setInviteOpen] = useState(false);

  const load = async () => {
    try {
      const q = status ? `?status=${status}` : "";
      const r = (await api.get(`/api/v1/escrow-institutions${q}`)).data;
      setItems(r.items || []);
    } catch (e) { showApiError(e); }
  };
  useEffect(() => { load(); /* eslint-disable-line */ }, [status]);

  // v52h — client-side filter so the server list call stays simple.
  const filteredItems = items.filter((i) => {
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      const hay = [
        i.legal_name, i.trading_name, i.primary_contact_email,
        i.reg_number, i.owner_account?.email,
      ].filter(Boolean).join(" ").toLowerCase();
      if (!hay.includes(q)) return false;
    }
    const created = (i.created_at || "").slice(0, 10);
    if (fromDate && created && created < fromDate) return false;
    if (toDate && created && created > toDate) return false;
    return true;
  });

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

  // v52e — direct message to the owner account (bell + email).
  const notifyOwner = async () => {
    if (!sel?.account_id) {
      return toast.error("Legacy magic-link draft — no owner account to notify.");
    }
    const title = window.prompt("Notification title (shown in the bell):");
    if (!title) return;
    const body = window.prompt("Message to the owner:");
    if (!body) return;
    try {
      await api.post(`/api/v1/escrow-institutions/${sel.id}/notify-owner`,
                      { title, body, send_email: true });
      toast.success("Owner notified · bell + email dispatched");
    } catch (e) { showApiError(e); }
  };

  const statusChip = (s) => {
    const map = {
      approved: "bg-emerald-50 text-emerald-900 border-emerald-200",
      rejected: "bg-red-50 text-red-900 border-red-200",
      submitted: "bg-amber-50 text-amber-900 border-amber-300",
      under_review: "bg-amber-50 text-amber-900 border-amber-300",
      changes_requested: "bg-orange-100 text-orange-900 border-orange-300",
      needs_clarification: "bg-sky-50 text-sky-900 border-sky-300",
      draft: "bg-slate-50 text-slate-700 border-slate-200",
    };
    return (
      <span className={`inline-block text-[10px] uppercase tracking-widest px-2 py-0.5 border ${map[s] || map.draft}`}>
        {s === "changes_requested" ? "changes pending" : s}
      </span>
    );
  };

  return (
    <div className="min-h-screen" style={{ background: "var(--brand-pale, #F3EFE4)" }}
         data-testid="admin-escrow-insts-page">
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
            <div className="flex items-center gap-2 flex-wrap">
              <button type="button" onClick={() => setInviteOpen(true)}
                      data-testid="admin-escrow-inst-invite-open"
                      className="px-4 py-2 text-xs uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy/90">
                + Invite institution
              </button>
              <input type="search" value={search}
                     onChange={(e) => setSearch(e.target.value)}
                     placeholder="Search name or email…"
                     data-testid="admin-escrow-insts-search"
                     className="px-3 py-2 text-sm border border-brand-navy/20 bg-white w-56" />
              <label className="text-[10px] uppercase tracking-widest text-brand-navy/60">From
                <input type="date" value={fromDate}
                       onChange={(e) => setFromDate(e.target.value)}
                       data-testid="admin-escrow-insts-from"
                       className="ml-1 px-2 py-2 text-sm border border-brand-navy/20 bg-white" />
              </label>
              <label className="text-[10px] uppercase tracking-widest text-brand-navy/60">To
                <input type="date" value={toDate}
                       onChange={(e) => setToDate(e.target.value)}
                       data-testid="admin-escrow-insts-to"
                       className="ml-1 px-2 py-2 text-sm border border-brand-navy/20 bg-white" />
              </label>
              <select value={status} onChange={(e) => setStatus(e.target.value)}
                      data-testid="admin-escrow-insts-filter"
                      className="px-3 py-2 text-sm border border-brand-navy/20 bg-white">
                <option value="">All statuses</option>
                <option value="submitted">Submitted (new)</option>
                <option value="under_review">Under review</option>
                <option value="changes_requested">Changes pending (awaiting approval)</option>
                <option value="needs_clarification">Needs clarification</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
                <option value="draft">Draft</option>
              </select>
              {(search || fromDate || toDate || status) && (
                <button type="button"
                        onClick={() => { setSearch(""); setFromDate(""); setToDate(""); setStatus(""); }}
                        data-testid="admin-escrow-insts-reset"
                        className="px-3 py-2 text-[11px] uppercase tracking-widest text-brand-navy/70 hover:text-brand-navy underline">
                  Reset
                </button>
              )}
            </div>
          </div>

          {inviteOpen && (
            <InviteDrawer onClose={() => setInviteOpen(false)} onInvited={() => { setInviteOpen(false); load(); }} />
          )}

          <div className="grid gap-4 lg:grid-cols-[5fr_7fr]">
            <section className="bg-white border border-brand-navy/15">
              <div className="pmc-label p-4 border-b border-brand-navy/10">
                Pipeline · {filteredItems.length}{filteredItems.length !== items.length ? ` of ${items.length}` : ""}
              </div>              <ul className="divide-y divide-brand-navy/10 max-h-[70vh] overflow-y-auto"
                  data-testid="admin-escrow-insts-list">
                {filteredItems.length === 0 && (
                  <li className="p-6 text-sm text-brand-navy/50">No registrations match this filter yet.</li>
                )}
                {filteredItems.map((i) => (
                  <li key={i.id}>
                    <button onClick={() => { setSel(i); setNotes(i.reviewer_notes || ""); }}
                            data-testid={`admin-escrow-inst-row-${i.id}`}
                            className={`w-full text-left p-4 hover:bg-brand-navy/5 transition-colors ${sel?.id === i.id ? "bg-brand-navy/5" : ""}`}>
                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        <strong className="text-brand-navy">{i.legal_name}</strong>
                        <span className="flex items-center gap-1">
                          {statusChip(i.status)}
                          {i.pending_changes > 0 && (
                            <span className="inline-block text-[10px] uppercase tracking-widest px-2 py-0.5 border bg-orange-100 text-orange-900 border-orange-300"
                                  data-testid={`admin-escrow-inst-pending-${i.id}`}>
                              {i.pending_changes} change{i.pending_changes > 1 ? "s" : ""} pending
                            </span>
                          )}
                        </span>
                      </div>
                      <div className="text-xs text-brand-navy/60 mt-1">
                        {i.country} · reg {i.reg_number || "—"} · {i.primary_contact_email}
                      </div>
                      {i.owner_account && (
                        <div className="text-[10px] text-brand-navy/50 mt-0.5"
                             data-testid={`admin-escrow-inst-owner-${i.id}`}>
                          owner · {i.owner_account.email} ({i.owner_account.status})
                        </div>
                      )}
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
                            <button type="button"
                                    onClick={() => uploadsApi.openFile(d.key).catch(showApiError)}
                                    className="text-[10px] uppercase tracking-widest px-3 py-1 border border-brand-navy/20 hover:bg-brand-navy/5">
                              Open
                            </button>
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

                  <ChangeRequestsPanel iid={sel.id} />

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
                    {sel?.account_id && (
                      <button onClick={notifyOwner} disabled={busy}
                              data-testid="admin-escrow-inst-notify"
                              className="px-5 py-2 text-xs uppercase tracking-widest border border-brand-navy/40 text-brand-navy disabled:opacity-50 hover:bg-brand-navy hover:text-white">
                        Notify owner
                      </button>
                    )}
                  </div>
                </div>
              )}
            </section>
          </div>

          {/* v52f — cross-institution escrow volume chart */}
          <div className="mb-6">
            <AdminEscrowChart />
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

function ValueBox({ label, value, section, tone, viewKey, viewTestId }) {
  // v52k — human-readable diff boxes. Inline styles dodge the global
  // [data-ui="e"] slate→dark remap that was blacking these boxes out.
  const boxStyle = tone === "amber"
    ? { background: "#FFFBEB", border: "1px solid #FDE68A", color: "#0F172A" }
    : { background: "#F8FAFC", border: "1px solid #E2E8F0", color: "#0F172A" };
  return (
    <div>
      <div className="pmc-label text-[9px]">{label}</div>
      <div className="p-2 overflow-auto max-h-40 text-xs rounded-sm" style={boxStyle}>
        {renderFriendly(value, section)}
      </div>
      {viewKey && (
        <button type="button"
                onClick={() => uploadsApi.openFile(viewKey).catch(showApiError)}
                data-testid={viewTestId}
                className="mt-1 px-3 py-1 text-[10px] uppercase tracking-widest border border-brand-navy/40 text-brand-navy hover:bg-brand-pale">
          View proposed file
        </button>
      )}
    </div>
  );
}

function renderFriendly(v, section) {
  if (v == null || v === "") return <span style={{ color: "#94A3B8" }}>—</span>;
  if (section === "documents" && typeof v === "object" && !Array.isArray(v)) {
    return (
      <span>
        <strong>{v.filename || "file"}</strong>
        {v.size_bytes != null && ` · ${Math.max(1, Math.round(v.size_bytes / 1024))} KB`}
        {v.uploaded_at && <span style={{ color: "#64748B" }}>{` · uploaded ${String(v.uploaded_at).slice(0, 10)}`}</span>}
      </span>
    );
  }
  if (typeof v === "string" || typeof v === "number" || typeof v === "boolean") return String(v);
  if (Array.isArray(v)) {
    if (!v.length) return <span style={{ color: "#94A3B8" }}>Empty list</span>;
    return (
      <ul className="space-y-1">
        {v.map((item, i) => (
          <li key={i}>
            {item && typeof item === "object"
              ? Object.entries(item)
                  .filter(([, val]) => val != null && val !== "")
                  .map(([k, val]) => `${k}: ${val}`)
                  .join(" · ")
              : String(item)}
          </li>
        ))}
      </ul>
    );
  }
  return <pre className="whitespace-pre-wrap break-words m-0">{JSON.stringify(v, null, 2)}</pre>;
}

function F({ label, v, mono }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-widest text-slate-500">{label}</div>
      <div className={`text-slate-800 text-sm ${mono ? "font-mono text-xs" : ""}`}>{v || "—"}</div>
    </div>
  );
}

function ChangeRequestsPanel({ iid }) {
  const [rows, setRows] = useState([]);
  const [busy, setBusy] = useState({});

  const load = async () => {
    try {
      const r = (await api.get(`/api/v1/escrow-institutions/${iid}/change-requests`)).data;
      setRows(r.items || []);
    } catch (e) { showApiError(e); }
  };
  useEffect(() => { if (iid) load(); /* eslint-disable-line */ }, [iid]);

  const decide = async (row, action) => {
    const notes = action === "reject"
      ? window.prompt(`Reviewer notes (required for reject):`)
      : window.prompt(`Reviewer notes (optional):`, "") || "";
    if (action === "reject" && !notes) return;
    setBusy((b) => ({ ...b, [row.id]: true }));
    try {
      await api.post(`/api/v1/escrow-institutions/change-requests/${row.id}/${action}`,
                     { reviewer_notes: notes || null });
      toast.success(action === "approve" ? "Change applied" : "Change rejected");
      await load();
    } catch (e) { showApiError(e); }
    finally { setBusy((b) => ({ ...b, [row.id]: false })); }
  };

  if (!rows.length) {
    return (
      <div className="pmc-label text-[10px] text-brand-navy/50"
           data-testid="admin-escrow-change-requests-empty">
        No profile change requests from this institution.
      </div>
    );
  }

  return (
    <div data-testid="admin-escrow-change-requests">
      <div className="pmc-label mb-2">Profile change requests · {rows.length}</div>
      <ul className="divide-y divide-brand-navy/10">
        {rows.map((r) => (
          <li key={r.id} className="py-3"
              data-testid={`admin-escrow-change-request-${r.id}`}>
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <div className="text-sm text-brand-navy">
                <strong>{r.section}</strong> · <code className="text-xs">{r.field_path}</code>
                <span className="ml-2 text-[10px] uppercase tracking-widest text-brand-navy/60">· {r.status}</span>
              </div>
              <div className="text-[10px] text-brand-navy/40">
                {(r.created_at || "").slice(0, 16).replace("T", " ")}
              </div>
            </div>
            <div className="mt-2 grid md:grid-cols-2 gap-3 text-xs">
              <ValueBox label="Current" value={r.current_value} section={r.section} tone="slate" />
              <ValueBox label="Proposed" value={r.proposed_value} section={r.section} tone="amber"
                        viewKey={r.section === "documents" ? r.proposed_value?.key : null}
                        viewTestId={`admin-escrow-change-view-${r.id}`} />
            </div>
            {r.reason && (
              <div className="mt-1 text-xs text-brand-navy/70">Reason: {r.reason}</div>
            )}
            {r.reviewer_notes && (
              <div className="mt-1 text-xs text-brand-navy/70">Reviewer: {r.reviewer_notes}</div>
            )}
            {r.status === "pending" && (
              <div className="mt-2 flex gap-2">
                <button onClick={() => decide(r, "approve")} disabled={busy[r.id]}
                        data-testid={`admin-escrow-change-approve-${r.id}`}
                        className="px-4 py-1.5 text-[10px] uppercase tracking-widest bg-emerald-700 text-white disabled:opacity-50">
                  Approve &amp; apply
                </button>
                <button onClick={() => decide(r, "reject")} disabled={busy[r.id]}
                        data-testid={`admin-escrow-change-reject-${r.id}`}
                        className="px-4 py-1.5 text-[10px] uppercase tracking-widest border border-red-600 text-red-800 disabled:opacity-50">
                  Reject
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * v52cx — InviteDrawer. Admin enters only the primary contact email (and
 * optionally institution name, contact name, type, note). We POST that to
 * /api/v1/escrow-institutions/admin-invite which creates a draft record,
 * generates a magic token and emails the institution a resume link. The
 * institution fills the entire form itself before admin review.
 */
function InviteDrawer({ onClose, onInvited }) {
  const [form, setForm] = useState({
    primary_contact_email: "", legal_name: "", contact_name: "",
    institution_type: "corporate", message: "",
  });
  const [busy, setBusy] = useState(false);
  const upd = (k, v) => setForm((s) => ({ ...s, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    if (!form.primary_contact_email.trim()) return toast.error("Primary contact email is required.");
    setBusy(true);
    try {
      const res = await escrowInstitutionsApi.adminInvite(form);
      if (res.email_sent) {
        toast.success(res.reused
          ? "Magic link re-sent to the existing draft."
          : "Invite email sent — the institution will fill in the details.");
      } else {
        toast.warning("Invite record created, but the email could not be sent. Share the resume link manually from the queue.");
      }
      onInvited && onInvited();
    } catch (err) { showApiError(err); }
    finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-start justify-end"
         data-testid="admin-escrow-inst-invite-drawer" onClick={onClose}>
      <form className="bg-white w-full max-w-md h-full overflow-y-auto p-6 shadow-xl space-y-4"
            onClick={(e) => e.stopPropagation()} onSubmit={submit}>
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-brand-navy">Invite escrow institution</h2>
          <button type="button" onClick={onClose} className="text-brand-navy/50 hover:text-brand-navy">✕</button>
        </div>
        <p className="text-xs text-brand-navy/60">
          Enter the institution's primary contact email. We'll email them a secure link
          to fill out the full registration (KYC, banking, signatories, documents).
          Review and approve from the queue once they submit.
        </p>

        <div>
          <label className="pmc-label text-[10px]">Institution type</label>
          <div className="mt-1 flex gap-4 text-sm">
            {[["corporate", "Corporate (bank / trust)"], ["personal", "Personal trustee"]].map(([k, l]) => (
              <label key={k} className="flex items-center gap-2 cursor-pointer">
                <input type="radio" name="inst-type" value={k}
                       checked={form.institution_type === k}
                       onChange={() => upd("institution_type", k)}
                       data-testid={`admin-escrow-inst-invite-type-${k}`} />
                {l}
              </label>
            ))}
          </div>
        </div>

        <div>
          <label className="pmc-label text-[10px]">Primary contact email <span className="text-red-600">*</span></label>
          <input type="email" required value={form.primary_contact_email}
                 onChange={(e) => upd("primary_contact_email", e.target.value)}
                 data-testid="admin-escrow-inst-invite-email"
                 className="mt-1 w-full border border-brand-navy/20 p-2 text-sm font-mono"
                 placeholder="treasury@partnerbank.com" />
        </div>

        <div>
          <label className="pmc-label text-[10px]">
            {form.institution_type === "personal" ? "Trustee full name" : "Institution legal name"}
            <span className="text-brand-navy/40"> (optional)</span>
          </label>
          <input type="text" value={form.legal_name}
                 onChange={(e) => upd("legal_name", e.target.value)}
                 data-testid="admin-escrow-inst-invite-legal-name"
                 className="mt-1 w-full border border-brand-navy/20 p-2 text-sm"
                 placeholder={form.institution_type === "personal" ? "e.g. Jane Smith" : "e.g. Partner Bank PLC"} />
        </div>

        <div>
          <label className="pmc-label text-[10px]">
            Contact person name <span className="text-brand-navy/40">(optional)</span>
          </label>
          <input type="text" value={form.contact_name}
                 onChange={(e) => upd("contact_name", e.target.value)}
                 data-testid="admin-escrow-inst-invite-contact-name"
                 className="mt-1 w-full border border-brand-navy/20 p-2 text-sm"
                 placeholder="So we address the invite email to a person" />
        </div>

        <div>
          <label className="pmc-label text-[10px]">
            Note to include in the email <span className="text-brand-navy/40">(optional)</span>
          </label>
          <textarea rows={3} value={form.message}
                    onChange={(e) => upd("message", e.target.value)}
                    data-testid="admin-escrow-inst-invite-message"
                    className="mt-1 w-full border border-brand-navy/20 p-2 text-sm"
                    placeholder="Context about which tender / why you're onboarding them…" />
        </div>

        <div className="flex gap-2 pt-2">
          <button type="submit" disabled={busy}
                  data-testid="admin-escrow-inst-invite-send"
                  className="px-5 py-2 text-xs uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy/90 disabled:opacity-50">
            {busy ? "Sending…" : "Send invite"}
          </button>
          <button type="button" onClick={onClose} disabled={busy}
                  className="px-5 py-2 text-xs uppercase tracking-widest border border-brand-navy/20 hover:bg-slate-50">
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}

function NoticeAccountPicker() {
  const [notices, setNotices] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [saving, setSaving] = useState({});
  const [selected, setSelected] = useState({}); // notice_ref -> true for bulk
  const [bulkAccountId, setBulkAccountId] = useState("");
  const [bulkBusy, setBulkBusy] = useState(false);

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
  const selectedCount = Object.values(selected).filter(Boolean).length;
  const allSelected = selectedCount > 0 && selectedCount === live.length;

  const toggleAll = () => {
    if (allSelected) setSelected({});
    else setSelected(Object.fromEntries(live.map((n) => [n.notice_ref, true])));
  };

  const bulkAssign = async () => {
    const refs = live.filter((n) => selected[n.notice_ref]).map((n) => n.notice_ref);
    if (refs.length === 0) return toast.error("Pick at least one notice to bulk-assign.");
    if (!window.confirm(`Assign ${bulkAccountId ? "this escrow account" : "the default (newest active)"} to ${refs.length} notice${refs.length === 1 ? "" : "s"}?`)) return;
    setBulkBusy(true);
    let okN = 0, failN = 0;
    for (const ref of refs) {
      try {
        await api.patch(`/api/v1/notices/${ref}`, { escrow_account_id: bulkAccountId || null });
        setNotices((prev) => prev.map((n) =>
          n.notice_ref === ref ? { ...n, escrow_account_id: bulkAccountId || null } : n));
        okN += 1;
      } catch (e) { failN += 1; }
    }
    setBulkBusy(false);
    setSelected({});
    toast.success(`Bulk assigned ${okN} notice${okN === 1 ? "" : "s"}${failN ? `, ${failN} failed` : ""}`);
  };

  return (
    <section className="mt-8 bg-white border border-brand-navy/15"
             data-testid="notice-account-picker">
      <div className="pmc-label p-4 border-b border-brand-navy/10 flex items-center justify-between gap-2 flex-wrap">
        <span>Notice ↔ Escrow account routing</span>
        <span className="text-[10px] text-brand-navy/50 normal-case tracking-normal">
          Pin a joint account to each published notice. Unassigned notices fall back to the newest active account.
        </span>
      </div>
      {live.length === 0 ? (
        <div className="p-6 text-sm text-brand-navy/50">No published notices yet.</div>
      ) : (
        <>
          <div className="p-3 bg-brand-navy/5 border-b border-brand-navy/10 flex items-center gap-3 flex-wrap text-xs"
               data-testid="notice-account-bulk-bar">
            <span className="text-brand-navy/70">
              {selectedCount} selected
            </span>
            <select value={bulkAccountId} onChange={(e) => setBulkAccountId(e.target.value)}
                    data-testid="notice-account-bulk-select"
                    className="px-2 py-1 border border-brand-navy/20 bg-white min-w-[240px]">
              <option value="">— Use newest active account (default) —</option>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} · {a.institution} · {a.currency}
                </option>
              ))}
            </select>
            <button onClick={bulkAssign} disabled={bulkBusy || selectedCount === 0}
                    data-testid="notice-account-bulk-apply"
                    className="px-3 py-1 text-[10px] uppercase tracking-widest bg-brand-navy text-white disabled:opacity-40">
              {bulkBusy ? "Applying…" : `Apply to ${selectedCount || "selected"}`}
            </button>
          </div>
          <table className="w-full text-sm">
            <thead className="text-left text-[10px] uppercase tracking-widest text-brand-navy/50">
              <tr>
                <th className="p-3 w-10">
                  <input type="checkbox" checked={allSelected} onChange={toggleAll}
                         data-testid="notice-account-select-all" />
                </th>
                <th className="p-3">Notice ref</th>
                <th className="p-3">Title</th>
                <th className="p-3">Escrow account</th>
              </tr>
            </thead>
            <tbody>
              {live.map((n) => (
                <tr key={n.notice_ref} className="border-t border-brand-navy/5"
                    data-testid={`notice-account-row-${n.notice_ref}`}>
                  <td className="p-3">
                    <input type="checkbox" checked={!!selected[n.notice_ref]}
                           onChange={(e) => setSelected((s) => ({ ...s, [n.notice_ref]: e.target.checked }))}
                           data-testid={`notice-account-check-${n.notice_ref}`} />
                  </td>
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
        </>
      )}
    </section>
  );
}
