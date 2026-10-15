/**
 * EscrowInstitutionProfile — v52g.
 *
 * Full read-only view of the institution record with a "Request change"
 * button on every editable field. All proposed edits are stored as
 * pending change-requests and only applied once a PMC admin approves
 * them (see backend/routers/escrow_profile_changes.py).
 *
 * Scope decided with the user:
 *   - All five sections editable (core, signatories, banking, documents).
 *   - Changes allowed at every stage, including drafts.
 *   - Unlimited field-level requests.
 *   - Admin review happens inside the existing Admin → Escrow
 *     Institutions detail panel.
 */
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api, showApiError, uploadsApi } from "@/lib/api";

const CORE_FIELDS = [
  ["legal_name", "Legal name"],
  ["trading_name", "Trading name"],
  ["country", "Country (ISO-2)"],
  ["registered_address", "Registered address"],
  ["address_line1", "Address line 1"],
  ["address_line2", "Address line 2"],
  ["city", "City"],
  ["state_name", "State / province"],
  ["postal_code", "Postal / ZIP"],
  ["reg_number", "Registration number"],
  ["tax_id", "Tax ID"],
  ["gst_or_vat", "GST / VAT"],
  ["regulator", "Regulator"],
  ["licence_number", "Licence number"],
  ["licence_expiry", "Licence expiry"],
  ["website", "Website"],
  ["primary_contact_email", "Primary contact email"],
  ["primary_contact_phone", "Primary contact phone"],
  ["mobile_phone", "Mobile phone"],
  ["office_phone", "Office telephone"],
  ["primary_contact_name", "Primary contact name"],
];

const DOC_SLOTS = [
  ["incorporation_certificate", "Certificate of incorporation / trust deed"],
  ["regulatory_licence", "Regulatory licence"],
  ["tax_registration", "Tax / GST / VAT registration"],
  ["audited_financials_y1", "Audited financials — year 1"],
  ["audited_financials_y2", "Audited financials — year 2"],
  ["insurance_indemnity", "Insurance & indemnity cover"],
  ["letterhead_sample", "Letterhead sample"],
  ["signatory_authority_resolution", "Signatory authority resolution"],
];

export default function EscrowInstitutionProfile({ account, inst, onInvited }) {
  const iid = inst?.id;
  const [full, setFull] = useState(null);
  const [requests, setRequests] = useState([]);
  const [editor, setEditor] = useState(null); // { section, field_path, label, current }
  const canInvite = inst?.status === "approved";
  const [inv, setInv] = useState({ name: "", designation: "", email: "", phone: "" });
  const [inviting, setInviting] = useState(false);

  const refresh = async () => {
    if (!iid) return;
    try {
      const [a, b] = await Promise.all([
        api.get(`/api/v1/escrow-institutions/${iid}/admin-view-public`),
        api.get(`/api/v1/escrow-accounts/me/change-requests`),
      ]);
      setFull(a.data || {});
      setRequests(b.data?.items || []);
    } catch (err) { showApiError(err); }
  };
  useEffect(() => { refresh(); /* eslint-disable-next-line */ }, [iid]);

  const openEditor = (section, field_path, label, current) =>
    setEditor({ section, field_path, label, current });

  const invite = async (e) => {
    e.preventDefault();
    setInviting(true);
    try {
      await api.post("/api/v1/escrow-accounts/me/signatories/invite", {
        name: inv.name.trim(), designation: inv.designation.trim(),
        email: inv.email.trim(), phone: inv.phone.trim() || undefined,
      });
      toast.success(`${inv.name} invited — password-claim email sent`);
      setInv({ name: "", designation: "", email: "", phone: "" });
      onInvited?.();
    } catch (err) { showApiError(err); }
    finally { setInviting(false); }
  };

  if (!full) {
    return <div className="text-sm text-brand-navy/50">Loading institution profile…</div>;
  }

  const pendingByPath = new Map(
    requests.filter((r) => r.status === "pending").map((r) => [r.field_path, r])
  );

  return (
    <div data-testid="escrow-profile-tab">
      <h1 className="font-serif text-2xl text-brand-navy mb-1">Institution profile</h1>
      <p className="text-sm text-brand-navy/60 mb-5">
        Full view of your registered details. Changes stay pending until PMC approves them.
      </p>

      {requests.length > 0 && (
        <section className="bg-white border border-brand-navy/15 p-4 mb-5"
                 data-testid="escrow-change-requests">
          <div className="pmc-label mb-2">My change requests · {requests.length}</div>
          <ul className="divide-y divide-brand-navy/10">
            {requests.map((r) => (
              <li key={r.id} className="py-2 flex items-start justify-between gap-3"
                  data-testid={`escrow-change-req-${r.id}`}>
                <div className="min-w-0">
                  <div className="text-sm text-brand-navy">
                    <strong>{r.section}</strong> · <code className="text-xs">{r.field_path}</code>{" "}
                    <span className="text-[10px] uppercase tracking-widest text-brand-navy/60">· {r.status}</span>
                  </div>
                  <div className="text-xs text-brand-navy/60 mt-0.5 break-words">
                    {r.section === "documents" && r.proposed_value && typeof r.proposed_value === "object" ? (
                      <>
                        <span className="text-brand-navy/50">New file:</span>{" "}
                        <strong>{r.proposed_value.filename || "—"}</strong>
                        {r.proposed_value.size_bytes != null && (
                          <span> · {Math.max(1, Math.round(r.proposed_value.size_bytes / 1024))} KB</span>
                        )}
                        {r.proposed_value.key && (
                          <button type="button"
                                  data-testid={`escrow-change-req-view-${r.id}`}
                                  onClick={() => uploadsApi.openFile(r.proposed_value.key).catch(showApiError)}
                                  className="ml-2 text-[11px] uppercase tracking-widest text-brand-navy underline hover:no-underline">
                            View
                          </button>
                        )}
                      </>
                    ) : (
                      <>
                        <span className="text-brand-navy/50">Proposed:</span>{" "}
                        <code>{renderValue(r.proposed_value)}</code>
                      </>
                    )}
                  </div>
                  {r.reason && <div className="text-xs text-brand-navy/60 mt-0.5">Reason: {r.reason}</div>}
                  {r.reviewer_notes && <div className="text-xs text-brand-navy/60 mt-0.5">Reviewer: {r.reviewer_notes}</div>}
                </div>
                {r.status === "pending" && (
                  <button type="button"
                          data-testid={`escrow-change-req-cancel-${r.id}`}
                          onClick={async () => {
                            try {
                              await api.delete(`/api/v1/escrow-accounts/me/change-requests/${r.id}`);
                              toast.success("Request cancelled");
                              refresh();
                            } catch (err) { showApiError(err); }
                          }}
                          className="text-[11px] uppercase tracking-widest text-red-700 hover:underline">
                    Cancel
                  </button>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Core profile */}
      <section className="bg-white border border-brand-navy/15 p-5 mb-5">
        <div className="pmc-label mb-3">Core details</div>
        <div className="grid md:grid-cols-2 gap-4">
          {CORE_FIELDS.map(([k, label]) => (
            <FieldRow key={k}
                      label={label}
                      value={full[k]}
                      pending={pendingByPath.get(k)}
                      testId={`escrow-field-${k}`}
                      onEdit={() => openEditor("core", k, label, full[k] || "")} />
          ))}
        </div>
      </section>

      {/* Signatories */}
      <section className="bg-white border border-brand-navy/15 p-5 mb-5">
        <div className="flex items-center justify-between mb-3">
          <div className="pmc-label">Named signatories · {(full.signatories || []).length}</div>
          <button type="button"
                  data-testid="escrow-field-request-signatories"
                  onClick={() => openEditor("signatories", "signatories",
                                             "Signatories list",
                                             JSON.stringify(full.signatories || [], null, 2))}
                  className="text-[11px] uppercase tracking-widest text-brand-navy hover:underline">
            Request change
          </button>
        </div>
        {(full.signatories || []).length === 0 ? (
          <div className="text-xs text-brand-navy/50">No signatories on file.</div>
        ) : (
          <ul className="divide-y divide-brand-navy/10 text-sm">
            {(full.signatories || []).map((s, i) => (
              <li key={i} className="py-2">
                <strong>{s.name || "—"}</strong> · {s.designation || "—"}
                <div className="text-xs text-brand-navy/60">{s.email || "—"} · {s.phone || "—"}</div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Banking */}
      <section className="bg-white border border-brand-navy/15 p-5 mb-5">
        <div className="flex items-center justify-between mb-3">
          <div className="pmc-label">Banking coordinates · {(full.banking || []).length}</div>
          <button type="button"
                  data-testid="escrow-field-request-banking"
                  onClick={() => openEditor("banking", "banking",
                                             "Banking list",
                                             JSON.stringify(full.banking || [], null, 2))}
                  className="text-[11px] uppercase tracking-widest text-brand-navy hover:underline">
            Request change
          </button>
        </div>
        {(full.banking || []).length === 0 ? (
          <div className="text-xs text-brand-navy/50">No banking coordinates on file.</div>
        ) : (
          <ul className="divide-y divide-brand-navy/10 text-sm">
            {(full.banking || []).map((b, i) => (
              <li key={i} className="py-2">
                <strong>{b.account_name || "—"}</strong> · {b.institution_name || "—"} ({b.currency || "—"})
                <div className="text-xs text-brand-navy/60 font-mono">
                  Acct {b.account_number || "—"} · IBAN {b.iban || "—"} · SWIFT {b.swift || "—"}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Documents */}
      <section className="bg-white border border-brand-navy/15 p-5 mb-5">
        <div className="pmc-label mb-3">KYC documents</div>
        <ul className="divide-y divide-brand-navy/10 text-sm">
          {DOC_SLOTS.map(([slot, label]) => {
            const meta = (full.documents || {})[slot];
            const pending = pendingByPath.get(`documents.${slot}`);
            return (
              <li key={slot} className="py-2 flex items-center justify-between gap-3"
                  data-testid={`escrow-field-doc-${slot}`}>
                <div className="min-w-0">
                  <div className="text-brand-navy">{label}</div>
                  <div className="text-xs text-brand-navy/60 truncate">
                    {meta?.filename || "—"}
                    {meta?.uploaded_at ? ` · uploaded ${meta.uploaded_at.slice(0, 10)}` : ""}
                  </div>
                  {pending && (
                    <div className="text-[11px] text-amber-800 mt-1">Pending replacement: {pending.proposed_value?.filename}</div>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {meta?.key && (
                    <button type="button"
                            data-testid={`escrow-doc-view-${slot}`}
                            onClick={() => uploadsApi.openFile(meta.key).catch(showApiError)}
                            className="px-3 py-1 text-[11px] uppercase tracking-widest border border-brand-navy/40 text-brand-navy hover:bg-brand-pale">
                      View
                    </button>
                  )}
                  <DocReplaceButton slot={slot} label={label}
                                    onReady={(newMeta) =>
                                      openEditor("documents", `documents.${slot}`, label, newMeta)} />
                </div>
              </li>
            );
          })}
        </ul>
      </section>

      {/* Signatory invite */}
      <section className="bg-white border border-brand-navy/15 p-5" data-testid="escrow-invite-section">
        <h2 className="font-serif text-lg text-brand-navy mb-1">Invite a teammate as signatory</h2>
        <p className="text-xs text-brand-navy/60 mb-4">
          {canInvite
            ? "They'll get a password-claim email and can co-sign EMD releases on your joint accounts once set up."
            : `Available once PMC approves your institution (current status: ${inst?.status || "draft"}).`}
        </p>
        <form onSubmit={invite} className={"grid gap-3 md:grid-cols-4 " + (!canInvite ? "opacity-50 pointer-events-none" : "")}>
          <input placeholder="Full name" value={inv.name}
                 data-testid="escrow-invite-name"
                 onChange={(e) => setInv({ ...inv, name: e.target.value })}
                 className="px-3 py-2 border border-brand-navy/20 text-sm" required minLength={2} />
          <input placeholder="Designation" value={inv.designation}
                 data-testid="escrow-invite-designation"
                 onChange={(e) => setInv({ ...inv, designation: e.target.value })}
                 className="px-3 py-2 border border-brand-navy/20 text-sm" required minLength={2} />
          <input placeholder="Email" type="email" value={inv.email}
                 data-testid="escrow-invite-email"
                 onChange={(e) => setInv({ ...inv, email: e.target.value })}
                 className="px-3 py-2 border border-brand-navy/20 text-sm" required />
          <input placeholder="Phone (optional)" value={inv.phone}
                 data-testid="escrow-invite-phone"
                 onChange={(e) => setInv({ ...inv, phone: e.target.value })}
                 className="px-3 py-2 border border-brand-navy/20 text-sm" />
          <div className="md:col-span-4 flex justify-end">
            <button type="submit" disabled={inviting || !canInvite}
                    data-testid="escrow-invite-submit"
                    className="px-5 py-2 text-xs uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy/90 disabled:opacity-50">
              {inviting ? "Inviting…" : "Send invite"}
            </button>
          </div>
        </form>
      </section>

      {editor && (
        <ChangeRequestModal editor={editor} iid={iid}
                            onClose={() => setEditor(null)}
                            onSubmitted={() => { setEditor(null); refresh(); }} />
      )}
    </div>
  );
}

function FieldRow({ label, value, pending, onEdit, testId }) {
  return (
    <div className="flex items-start justify-between gap-3" data-testid={testId}>
      <div className="min-w-0">
        <div className="text-[10px] uppercase tracking-widest text-brand-navy/60">{label}</div>
        <div className="text-sm text-brand-navy break-words">{value || "—"}</div>
        {pending && (
          <div className="text-[11px] text-amber-800 mt-1">
            Pending: <code>{renderValue(pending.proposed_value)}</code>
          </div>
        )}
      </div>
      <button type="button" onClick={onEdit}
              data-testid={`${testId}-request`}
              className="text-[11px] uppercase tracking-widest text-brand-navy hover:underline shrink-0">
        Request change
      </button>
    </div>
  );
}

function DocReplaceButton({ slot, label, onReady }) {
  const [busy, setBusy] = useState(false);
  const upload = async (file) => {
    setBusy(true);
    try {
      const meta = await uploadsApi.uploadFile(file, { scope: "escrow-docs" });
      onReady(meta);
    } catch (err) { showApiError(err); }
    finally { setBusy(false); }
  };
  return (
    <label className="px-3 py-1 text-[11px] uppercase tracking-widest border border-brand-navy/40 text-brand-navy cursor-pointer hover:bg-brand-pale shrink-0"
           data-testid={`escrow-doc-replace-${slot}`}>
      {busy ? "…" : "Replace"}
      <input type="file" className="hidden"
             onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
    </label>
  );
}

function ChangeRequestModal({ editor, iid, onClose, onSubmitted }) {
  const isSignatories = editor.section === "signatories";
  const isBanking = editor.section === "banking";
  const isDoc = editor.section === "documents";
  const [proposed, setProposed] = useState(() => {
    if (isDoc) return editor.current; // meta object from upload
    return editor.current || "";
  });
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    try {
      let value = proposed;
      if (isSignatories || isBanking) {
        try { value = JSON.parse(proposed || "[]"); }
        catch { toast.error("Proposed value must be valid JSON."); setBusy(false); return; }
        if (!Array.isArray(value)) { toast.error("Expected a JSON array."); setBusy(false); return; }
      }
      await api.post("/api/v1/escrow-accounts/me/change-requests", {
        section: editor.section,
        field_path: editor.field_path,
        current_value: isDoc ? undefined : editor.current,
        proposed_value: value,
        reason: reason || undefined,
      });
      toast.success("Change request submitted — awaiting PMC review");
      onSubmitted();
    } catch (err) { showApiError(err); }
    finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4"
         onClick={onClose} data-testid="escrow-change-modal">
      <div className="bg-white max-w-xl w-full p-5" onClick={(e) => e.stopPropagation()}>
        <div className="pmc-label mb-1">Request change</div>
        <h2 className="font-serif text-lg text-brand-navy mb-3">{editor.label}</h2>
        <div className="text-xs text-brand-navy/60 mb-3">
          Field path: <code>{editor.field_path}</code>
        </div>

        {isDoc ? (
          <div className="mb-3 text-sm">
            <div className="pmc-label mb-1">Proposed replacement</div>
            <div className="text-xs text-brand-navy/70">
              {proposed?.filename ? `${proposed.filename}` : "No file selected"}
            </div>
          </div>
        ) : (isSignatories || isBanking) ? (
          <>
            <div className="pmc-label mb-1 text-[10px]">Current (JSON)</div>
            <pre className="text-[11px] bg-brand-pale p-2 overflow-auto max-h-32 mb-3">{editor.current || "[]"}</pre>
            <div className="pmc-label mb-1 text-[10px]">Proposed (JSON array)</div>
            <textarea rows={8} value={proposed} onChange={(e) => setProposed(e.target.value)}
                      data-testid="escrow-change-modal-proposed"
                      className="w-full border border-brand-navy/20 p-2 text-xs font-mono" />
          </>
        ) : (
          <>
            <div className="pmc-label mb-1 text-[10px]">Current</div>
            <div className="text-sm text-brand-navy/70 mb-3 break-words">{editor.current || "—"}</div>
            <div className="pmc-label mb-1 text-[10px]">Proposed</div>
            <input type="text" value={proposed} onChange={(e) => setProposed(e.target.value)}
                   data-testid="escrow-change-modal-proposed"
                   className="w-full border border-brand-navy/20 p-2 text-sm" autoFocus />
          </>
        )}

        <div className="mt-3">
          <div className="pmc-label mb-1 text-[10px]">Reason (optional)</div>
          <textarea rows={3} value={reason} onChange={(e) => setReason(e.target.value)}
                    data-testid="escrow-change-modal-reason"
                    className="w-full border border-brand-navy/20 p-2 text-sm"
                    placeholder="Why does this need to change?" />
        </div>

        <div className="mt-4 flex justify-end gap-2">
          <button type="button" onClick={onClose} disabled={busy}
                  className="px-4 py-2 text-xs uppercase tracking-widest border border-brand-navy/20">
            Cancel
          </button>
          <button type="button" onClick={submit} disabled={busy}
                  data-testid="escrow-change-modal-submit"
                  className="px-5 py-2 text-xs uppercase tracking-widest bg-brand-navy text-white disabled:opacity-50">
            {busy ? "Sending…" : "Submit for PMC review"}
          </button>
        </div>

        <input type="hidden" value={iid} readOnly />
      </div>
    </div>
  );
}

function renderValue(v) {
  if (v == null) return "—";
  if (typeof v === "string") return v;
  try { return JSON.stringify(v); } catch { return String(v); }
}
