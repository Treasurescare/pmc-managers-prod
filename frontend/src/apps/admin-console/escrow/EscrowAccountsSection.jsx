/**
 * EscrowAccountsSection — v53k. Dropdowns instead of free-text for
 * institution, PMC officer, and institution officer. Sources:
 *   - Institution      → GET /api/v1/escrow-institutions (status=approved)
 *   - PMC officer      → GET /api/v1/escrow/signatory-pool (pmc_officers)
 *   - Escrow officer   → signatories of the chosen institution
 * Blocker it fixes: EMD-bearing bids could not advance because the
 * free-text officers in the joint account didn't match any real staff /
 * institution signatory, so the "escrow accept" step had nobody to act.
 */
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { escrowApi, escrowInstitutionsApi, formatApiError, showApiError} from "@/lib/api";
import { InfoDot } from "@/components/InfoDot";

const CURRENCIES = ["USD", "EUR", "GBP", "INR", "KZT", "AED"];
const EMPTY = {
  name: "", institution: "", institution_id: "",
  account_no: "", iban: "", swift: "", currency: "USD",
  pmc_officer:    { name: "", email: "", designation: "", role: "pmc" },
  escrow_officer: { name: "", email: "", designation: "", role: "escrow_institution" },
  active: true, notes: "",
};

// v56c — professional fallback label for accounts with a blank display name
// (legacy rows). Convention: "<Institution> Escrow ••<last4>", else
// "Joint Escrow Account ••<last4>".
function accountLabel(acc) {
  if (acc.name && acc.name.trim()) return acc.name.trim();
  const tail = (acc.account_no || "").slice(-4);
  const inst = (acc.institution || "").trim();
  if (inst) return `${inst} Escrow${tail ? ` ••${tail}` : ""}`;
  return `Joint Escrow Account${tail ? ` ••${tail}` : ""}`;
}

// v56c — country scope of an institution ("Global" when unscoped).
const scopeLabel = (i) =>
  (i.country_scope && i.country_scope.length) ? i.country_scope.join("/") : "Global";
// An institution is in scope for `country` when it's global (no scope) or lists it.
const inScope = (i, country) =>
  !country || !(i.country_scope && i.country_scope.length) || i.country_scope.includes(country);

// Country filter above an institution dropdown. Renders nothing until at
// least one institution actually has a country scope configured.
function CountryFilterSelect({ institutions, value, onChange, testid }) {
  const countries = Array.from(
    new Set((institutions || []).flatMap((i) => i.country_scope || []))
  ).sort();
  if (countries.length === 0) return null;
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)} data-testid={testid}
            className="mb-2 text-xs px-2 py-1 border border-brand-navy/20 bg-white">
      <option value="">All countries</option>
      {countries.map((c) => <option key={c} value={c}>{c}</option>)}
    </select>
  );
}

export default function EscrowAccountsSection({ accounts, onReload }) {
  const [showNew, setShowNew] = useState(false);
  const [acc, setAcc] = useState(EMPTY);
  const [pool, setPool] = useState({ pmc_officers: [], institutions: [] });
  const [poolLoading, setPoolLoading] = useState(true);
  const [instFilter, setInstFilter] = useState("");

  useEffect(() => {
    escrowApi.signatoryPool()
      .then((d) => setPool({
        pmc_officers: d.pmc_officers || [],
        institutions: d.institutions || [],
      }))
      .catch((e) => showApiError(e, { fallbackTitle: "Signatory pool unavailable" }))
      .finally(() => setPoolLoading(false));
  }, []);

  const institutionSignatories = useMemo(() => {
    const match = pool.institutions.find((i) => i.id === acc.institution_id);
    return match ? (match.signatories || []) : [];
  }, [pool.institutions, acc.institution_id]);

  const pickInstitution = (id) => {
    const match = pool.institutions.find((i) => i.id === id);
    setAcc({
      ...acc,
      institution_id: id,
      institution: match ? (match.legal_name || "") : "",
      // Reset the escrow officer when institution changes.
      escrow_officer: { name: "", email: "", designation: "", role: "escrow_institution" },
    });
  };

  const pickPmcOfficer = (email) => {
    const s = pool.pmc_officers.find((p) => p.email === email);
    setAcc({
      ...acc,
      pmc_officer: s
        ? { name: s.name, email: s.email, designation: s.designation || "", role: "pmc" }
        : { name: "", email: "", designation: "", role: "pmc" },
    });
  };

  const pickEscrowOfficer = (email) => {
    const s = institutionSignatories.find((x) => x.email === email);
    setAcc({
      ...acc,
      escrow_officer: s
        ? { name: s.name, email: s.email, designation: s.designation || "", role: "escrow_institution" }
        : { name: "", email: "", designation: "", role: "escrow_institution" },
    });
  };

  const create = async () => {
    const miss = [];
    if (!acc.name.trim())              miss.push("Display name");
    if (!acc.institution_id)           miss.push("Institution");
    if (!acc.account_no.trim())        miss.push("Account no.");
    if (!acc.pmc_officer.email)        miss.push("PMC officer");
    if (!acc.escrow_officer.email)     miss.push("Escrow officer");
    if (miss.length) {
      toast.error(`Please fill in: ${miss.join(", ")}`);
      return;
    }
    if (acc.pmc_officer.email.toLowerCase() ===
        acc.escrow_officer.email.toLowerCase()) {
      toast.error("PMC and Escrow officer must be different people.");
      return;
    }
    try {
      // Backend ignores institution_id but accepts institution (legal_name)
      // which is auto-populated when the admin picks from the dropdown.
      const { institution_id: _ignore, ...payload } = acc; // eslint-disable-line no-unused-vars
      await escrowApi.createAccount({ ...payload, currency: acc.currency.toUpperCase() });
      toast.success("Joint escrow account created");
      setShowNew(false);
      setAcc(EMPTY);
      onReload();
    } catch (e) { showApiError(e); }
  };

  const noPmcPool = !poolLoading && pool.pmc_officers.length === 0;
  const noInstPool = !poolLoading && pool.institutions.length === 0;

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="pmc-label">Joint escrow accounts</div>
          <div className="text-xs text-brand-navy/60">
            Each account is operated by two officers — PMC + Escrow Institution — and both must sign every release.
          </div>
        </div>
        <button onClick={() => setShowNew(!showNew)} data-testid="escrow-new-acc-toggle"
                className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
          {showNew ? "Cancel" : "New joint account"}
        </button>
      </div>

      {showNew && (
        <div className="border border-brand-navy/20 bg-white p-6 grid gap-3 md:grid-cols-3 mb-4" data-testid="escrow-new-acc-form">
          {(noPmcPool || noInstPool) && (
            <div className="md:col-span-3 border border-amber-400 bg-amber-50 px-4 py-3 text-xs text-amber-900"
                 data-testid="escrow-pool-empty-warning">
              {noPmcPool && (
                <div><b>No PMC signatories configured yet.</b> Go to Masters → Staff and
                tick <b>Escrow signatory</b> on each staff member who can co-sign EMD releases.</div>
              )}
              {noInstPool && (
                <div className="mt-1"><b>No approved escrow institutions yet.</b> Go to
                Escrow institutions, invite / approve one, and its signatories will appear here.</div>
              )}
            </div>
          )}

          <label><span className="pmc-label">Display name<InfoDot tip="Internal label for the joint account." /></span>
            <input value={acc.name} onChange={(e) => setAcc({ ...acc, name: e.target.value })}
                   data-testid="escrow-acc-name" className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>

          <label><span className="pmc-label">Institution (bank / trustee)<InfoDot tip="Approved escrow institutions, tagged with the country scope set on each institution. Use the country filter to narrow the list." /></span>
            <CountryFilterSelect institutions={pool.institutions} value={instFilter} onChange={setInstFilter} testid="escrow-acc-inst-country" />
            <select value={acc.institution_id} onChange={(e) => pickInstitution(e.target.value)}
                    data-testid="escrow-acc-inst"
                    className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white">
              <option value="">— Choose an approved institution —</option>
              {pool.institutions.filter((i) => inScope(i, instFilter)).map((i) => (
                <option key={i.id} value={i.id}>{i.legal_name} · {scopeLabel(i)}</option>
              ))}
            </select></label>

          <label><span className="pmc-label">Account no.</span>
            <input value={acc.account_no} onChange={(e) => setAcc({ ...acc, account_no: e.target.value })}
                   data-testid="escrow-acc-no" className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>

          <label><span className="pmc-label">IBAN</span>
            <input value={acc.iban} onChange={(e) => setAcc({ ...acc, iban: e.target.value })}
                   className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>

          <label><span className="pmc-label">SWIFT / BIC</span>
            <input value={acc.swift} onChange={(e) => setAcc({ ...acc, swift: e.target.value })}
                   className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>

          <label><span className="pmc-label">Currency</span>
            <select value={acc.currency} onChange={(e) => setAcc({ ...acc, currency: e.target.value })}
                    className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white">
              {CURRENCIES.map((c) => <option key={c}>{c}</option>)}
            </select></label>

          <fieldset className="md:col-span-3 border border-brand-navy/10 p-3">
            <legend className="pmc-label px-2">PMC officer</legend>
            <div className="text-[11px] text-brand-navy/60 mb-2">
              Only active staff flagged as <b>Escrow signatory</b> appear here.
              Add / edit the flag in Masters → Staff.
            </div>
            <select value={acc.pmc_officer.email}
                    onChange={(e) => pickPmcOfficer(e.target.value)}
                    data-testid="escrow-pmc-select"
                    className="w-full px-3 py-2 border border-brand-navy/20 bg-white">
              <option value="">— Choose a PMC signatory —</option>
              {pool.pmc_officers.map((p) => (
                <option key={p.email} value={p.email}>
                  {p.name} · {p.email}{p.designation ? ` · ${p.designation}` : ""}
                </option>
              ))}
            </select>
          </fieldset>

          <fieldset className="md:col-span-3 border border-brand-navy/10 p-3">
            <legend className="pmc-label px-2">Escrow-institution officer</legend>
            <div className="text-[11px] text-brand-navy/60 mb-2">
              Signatories of the institution picked above. Add / remove them from the institution's own dashboard.
            </div>
            <select value={acc.escrow_officer.email}
                    onChange={(e) => pickEscrowOfficer(e.target.value)}
                    disabled={!acc.institution_id}
                    data-testid="escrow-eo-select"
                    className="w-full px-3 py-2 border border-brand-navy/20 bg-white disabled:opacity-50">
              <option value="">
                {acc.institution_id ? "— Choose an institution signatory —" : "Pick an institution first"}
              </option>
              {institutionSignatories.map((s) => (
                <option key={s.email} value={s.email}>
                  {s.name} · {s.email}{s.designation ? ` · ${s.designation}` : ""}
                </option>
              ))}
            </select>
          </fieldset>

          <div className="md:col-span-3 flex justify-end">
            <button onClick={create} data-testid="escrow-acc-save"
                    className="px-6 py-2 text-[11px] uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90">
              Create joint account
              <InfoDot tip="Both signatories are picked from managed lists — no free-text emails, so the escrow-accept step always finds a real staff / institution officer." />
            </button>
          </div>
        </div>
      )}

      <div className="border border-brand-navy/10 bg-white divide-y divide-brand-navy/10">
        {accounts.length === 0 && <div className="p-6 text-sm text-brand-navy/50">No accounts configured yet.</div>}
        {accounts.map((a) => (
          <AccountRow key={a.id} acc={a} onReload={onReload} pool={pool} />
        ))}
      </div>
    </section>
  );
}


// v54a — single-row Edit for an existing joint escrow account.
// Lets the admin re-bind the account to any approved escrow institution
// master (fixes the "escrow officer dropdown is empty forever" bug when
// the account's free-text institution name doesn't match any master).
function AccountRow({ acc, onReload, pool }) {
  const [editing, setEditing] = useState(false);
  const [pmc, setPmc] = useState(acc.pmc_officer || { name: "", email: "", designation: "", role: "pmc" });
  const [esc, setEsc] = useState(acc.escrow_officer || { name: "", email: "", designation: "", role: "escrow_institution" });
  const [institutionId, setInstitutionId] = useState(acc.institution_id || "");
  const [instFilter, setInstFilter] = useState("");
  const [busy, setBusy] = useState(false);

  // Match on institution_id first (explicit, set on creation / rebind),
  // then fall back to legal_name (legacy accounts).
  const matchedInst = useMemo(() => {
    if (!pool || !pool.institutions) return null;
    if (institutionId) {
      const m = pool.institutions.find((i) => i.id === institutionId);
      if (m) return m;
    }
    return pool.institutions.find((i) =>
      (i.legal_name || "").trim().toLowerCase() === (acc.institution || "").trim().toLowerCase()
    );
  }, [pool, acc.institution, institutionId]);

  // v53l — compute signatory-health badges from the pool.
  const health = useMemo(() => {
    if (!pool) return null;
    const pmcEmail = (acc.pmc_officer?.email || "").toLowerCase();
    const escEmail = (acc.escrow_officer?.email || "").toLowerCase();
    const pmcOk = !!(pool.pmc_officers || []).find((p) => p.email === pmcEmail);
    const escOk = !!matchedInst && !!(matchedInst.signatories || []).find((s) => s.email === escEmail);
    const institutionOk = !!matchedInst;
    const anyBad = !pmcOk || !escOk || !institutionOk;
    return { pmcOk, escOk, institutionOk, anyBad };
  }, [pool, matchedInst, acc.pmc_officer, acc.escrow_officer]);

  const runBackfill = async () => {
    if (!window.confirm(
      `Backfill signers on "${accountLabel(acc)}"?\n\n` +
      `This matches the institution name to the escrow institution master,\n` +
      `refreshes the PMC officer from the staff pool (if the email matches),\n` +
      `and swaps the escrow officer to a real institution signatory.\n\n` +
      `All changes are written to the audit trail.`)) return;
    try {
      const r = await escrowApi.backfillSigners(acc.id);
      const d = r.diagnostics || {};
      toast.success(
        `Backfilled · institution: ${d.institution_matched || "ok"} · ` +
        `pmc: ${d.pmc_officer} · escrow: ${d.escrow_officer}`,
        { duration: 8000 });
      onReload?.();
    } catch (e) {
      const detail = e?.response?.data?.detail;
      if (detail && detail.error === "institution_unmatched") {
        const list = (detail.suggestions || []).map((s) => s.legal_name).join(", ");
        toast.error(detail.message || "Institution not found", {
          description: list ? `Closest matches in master: ${list}. Fix the master, or recreate this account.` : undefined,
          duration: 10000, closeButton: true,
        });
      } else {
        showApiError(e, { fallbackTitle: "Backfill failed" });
      }
    }
  };

  const open = () => {
    setPmc({ name: "", email: "", designation: "", role: "pmc", ...(acc.pmc_officer || {}) });
    setEsc({ name: "", email: "", designation: "", role: "escrow_institution", ...(acc.escrow_officer || {}) });
    setInstitutionId(acc.institution_id || "");
    setEditing(true);
  };
  const cancel = () => setEditing(false);

  const save = async () => {
    const emailRx = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
    if (!emailRx.test(pmc.email || "")) return toast.error("PMC officer email is not valid");
    if (!emailRx.test(esc.email || "")) return toast.error("Escrow officer email is not valid");
    if ((pmc.email || "").toLowerCase() === (esc.email || "").toLowerCase()) {
      return toast.error("PMC and Escrow officer emails must be different.");
    }
    if ((pmc.name || "").trim().length < 2) return toast.error("PMC officer name too short");
    if ((esc.name || "").trim().length < 2) return toast.error("Escrow officer name too short");
    const institutionName = matchedInst ? matchedInst.legal_name : acc.institution;
    if (!window.confirm(
      `Update signers on "${accountLabel(acc)}"?\n\n` +
      `  Institution     → ${institutionName}\n` +
      `  PMC officer     → ${pmc.name} <${pmc.email}>\n` +
      `  Escrow officer  → ${esc.name} <${esc.email}>\n\n` +
      `Every change is written to the audit trail.`
    )) return;
    setBusy(true);
    try {
      await escrowApi.patchAccount(acc.id, {
        institution: institutionName,
        institution_id: institutionId || null,
        pmc_officer: {
          name: pmc.name.trim(), email: pmc.email.trim(),
          designation: (pmc.designation || "").trim() || null, role: "pmc",
        },
        escrow_officer: {
          name: esc.name.trim(), email: esc.email.trim(),
          designation: (esc.designation || "").trim() || null, role: "escrow_institution",
        },
      });
      toast.success("Both signers updated · audit-trail rows written");
      setEditing(false);
      onReload?.();
    } catch (e) { showApiError(e, { fallbackTitle: "Update failed" }); }
    finally { setBusy(false); }
  };

  if (!editing) {
    return (
      <div className="p-4 grid gap-3 md:grid-cols-5 items-start" data-testid={`escrow-acc-row-${acc.id}`}>
        <div className="md:col-span-2 min-w-0">
          <div className="font-semibold text-brand-navy flex items-center gap-2 flex-wrap">
            {accountLabel(acc)}
            {health?.anyBad && (
              <span data-testid={`escrow-acc-health-bad-${acc.id}`}
                    title="Current signers do not match the escrow institution master or the PMC signatory pool. Releases on this account will fail until fixed."
                    className="text-[9px] uppercase tracking-widest text-rose-800 bg-rose-50 border border-rose-300 px-1.5 py-0.5">
                signatory required
              </span>
            )}
          </div>
          <div className="text-xs text-brand-navy/60 break-all">
            {acc.institution || <span className="text-rose-700 font-semibold">institution not set</span>}
            {" · "}{acc.account_no || "—"}{" · "}{acc.currency || "—"}
          </div>
          {health?.anyBad && (
            <div className="text-[11px] text-rose-700 mt-1" data-testid={`escrow-acc-health-detail-${acc.id}`}>
              {!health.institutionOk && <div>• Institution does not match any approved master row.</div>}
              {!health.pmcOk && <div>• PMC officer email is not in the escrow-signatory staff pool.</div>}
              {!health.escOk && health.institutionOk && <div>• Escrow officer email is not a signatory of this institution.</div>}
            </div>
          )}
        </div>
        <div className="text-xs min-w-0">
          <div className="pmc-label">PMC officer</div>
          <div className="break-all">
            {acc.pmc_officer?.name} · <span className="font-mono">{acc.pmc_officer?.email}</span>
            {health && !health.pmcOk && <span className="ml-1 text-rose-700">✗</span>}
          </div>
        </div>
        <div className="text-xs min-w-0">
          <div className="pmc-label">Escrow officer</div>
          <div className="break-all">
            {acc.escrow_officer?.name} · <span className="font-mono">{acc.escrow_officer?.email}</span>
            {health && !health.escOk && <span className="ml-1 text-rose-700">✗</span>}
          </div>
        </div>
        <div className="flex md:justify-end gap-2 flex-wrap">
          {health?.anyBad && (
            <button type="button" onClick={runBackfill}
                    data-testid={`escrow-acc-backfill-${acc.id}`}
                    title="Match institution to the master and swap in real signatory emails from the pool."
                    className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-widest bg-rose-700 text-white border border-rose-700 hover:bg-rose-800">
              Backfill
            </button>
          )}
          <button type="button" onClick={open}
                  data-testid={`escrow-acc-edit-${acc.id}`}
                  className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white border border-brand-navy hover:bg-brand-navy-deep">
            Edit signers
          </button>
        </div>
      </div>
    );
  }

  const pmcPool = (pool && pool.pmc_officers) || [];
  const instSigs = matchedInst ? (matchedInst.signatories || []) : [];
  const allInsts = (pool && pool.institutions) || [];
  const pickInstitution = (id) => {
    setInstitutionId(id);
    // Clear the chosen escrow officer; the previous selection may not
    // belong to the newly selected institution.
    setEsc({ name: "", email: "", designation: "", role: "escrow_institution" });
  };
  const pickPmc = (email) => {
    const s = pmcPool.find((p) => p.email === email);
    if (s) setPmc({ name: s.name, email: s.email,
                     designation: s.designation || "", role: "pmc" });
    else setPmc({ name: "", email: "", designation: "", role: "pmc" });
  };
  const pickEsc = (email) => {
    const s = instSigs.find((x) => x.email === email);
    if (s) setEsc({ name: s.name, email: s.email,
                     designation: s.designation || "", role: "escrow_institution" });
    else setEsc({ name: "", email: "", designation: "", role: "escrow_institution" });
  };

  return (
    <div className="p-4 border-l-4 border-brand-navy bg-brand-pale/30" data-testid={`escrow-acc-edit-form-${acc.id}`}>
      <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
        <div>
          <div className="font-semibold text-brand-navy">{accountLabel(acc)}</div>
          <div className="text-xs text-brand-navy/60">{acc.institution} · {acc.account_no} · {acc.currency}</div>
        </div>
        <div className="text-xs text-brand-navy/60">
          Pick signatories from the managed lists — every change is written to the audit ledger.
        </div>
      </div>

      {/* v54a — institution picker. Lets admin rebind an account to any
          approved escrow institution, which auto-unlocks the signatory
          dropdown below (previously a legacy free-text name mismatch
          locked the escrow officer field forever). */}
      <fieldset className="border border-brand-navy/15 p-3 bg-white mb-4">
        <legend className="pmc-label px-2">Escrow institution</legend>
        <div className="text-[11px] text-brand-navy/60 mb-2">
          Only <b>approved</b> institutions are listed. Pick a different one
          here to rebind this account — the escrow officer dropdown will
          repopulate with the newly selected institution&apos;s registered
          signatories (plus its primary contact as a fallback).
        </div>
        <CountryFilterSelect institutions={allInsts} value={instFilter} onChange={setInstFilter} testid={`escrow-edit-inst-country-${acc.id}`} />
        <select value={institutionId || ""} onChange={(e) => pickInstitution(e.target.value)}
                data-testid={`escrow-edit-inst-select-${acc.id}`}
                className="w-full px-3 py-2 border border-brand-navy/20 bg-white">
          <option value="">
            {acc.institution ? `— Keep "${acc.institution}" (unmatched master) —` : "— Choose an approved institution —"}
          </option>
          {allInsts.filter((i) => inScope(i, instFilter)).map((i) => (
            <option key={i.id} value={i.id}>
              {i.legal_name} · {scopeLabel(i)}
              {i.primary_contact_email ? ` · ${i.primary_contact_email}` : ""}
              {" · "}{(i.signatories || []).length} signatory
              {(i.signatories || []).length === 1 ? "" : "ies"}
            </option>
          ))}
        </select>
      </fieldset>

      <div className="grid gap-4 md:grid-cols-2">
        <fieldset className="border border-brand-navy/15 p-3 bg-white">
          <legend className="pmc-label px-2">PMC officer</legend>
          {pmcPool.length === 0 && (
            <div className="text-[11px] text-amber-800 bg-amber-50 border border-amber-200 px-2 py-1 mb-2">
              No staff is flagged as <b>Escrow signatory</b> yet. Go to
              Masters → Staff and tick the flag on at least one active
              staff member, then come back.
            </div>
          )}
          <select value={pmc.email} onChange={(e) => pickPmc(e.target.value)}
                  data-testid={`escrow-edit-pmc-select-${acc.id}`}
                  className="w-full px-3 py-2 border border-brand-navy/20 bg-white">
            <option value="">— Choose a PMC signatory —</option>
            {pmcPool.map((p) => (
              <option key={p.email} value={p.email}>{p.name} · {p.email}</option>
            ))}
          </select>
          {pmc.email && (
            <div className="text-[11px] text-brand-navy/60 mt-2">
              {pmc.name} · <span className="font-mono">{pmc.email}</span>
            </div>
          )}
          {pmc.email && !pmcPool.find((p) => p.email === pmc.email) && (
            <div className="text-[11px] text-amber-800 mt-1">
              Current email is <b>not in the signatory pool</b> — releases
              on this account will fail until you pick someone from the
              dropdown above.
            </div>
          )}
        </fieldset>
        <fieldset className="border border-brand-navy/15 p-3 bg-white">
          <legend className="pmc-label px-2">Escrow-institution officer</legend>
          {!matchedInst && (
            <div className="text-[11px] text-amber-800 bg-amber-50 border border-amber-200 px-2 py-1 mb-2">
              Pick an approved institution above first — the signatory list
              is specific to the chosen institution.
            </div>
          )}
          {matchedInst && instSigs.length === 0 && (
            <div className="text-[11px] text-amber-800 bg-amber-50 border border-amber-200 px-2 py-1 mb-2">
              <b>{matchedInst.legal_name}</b> has no registered signatories
              yet. Open the institution portal and invite one, then come
              back. (Primary contact appears as a fallback here if one is
              configured on the institution.)
            </div>
          )}
          <select value={esc.email} onChange={(e) => pickEsc(e.target.value)}
                  disabled={!matchedInst || instSigs.length === 0}
                  data-testid={`escrow-edit-eo-select-${acc.id}`}
                  className="w-full px-3 py-2 border border-brand-navy/20 bg-white disabled:opacity-50">
            <option value="">— Choose an institution signatory —</option>
            {instSigs.map((s) => (
              <option key={s.email} value={s.email}>
                {s.name} · {s.email}{s.designation ? ` · ${s.designation}` : ""}
              </option>
            ))}
          </select>
          {esc.email && (
            <div className="text-[11px] text-brand-navy/60 mt-2">
              {esc.name} · <span className="font-mono">{esc.email}</span>
            </div>
          )}
        </fieldset>
      </div>
      <div className="mt-3 flex justify-end gap-2 flex-wrap">
        <button type="button" onClick={cancel} disabled={busy}
                data-testid={`escrow-acc-edit-cancel-${acc.id}`}
                className="px-4 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/20 text-brand-navy/80 hover:bg-brand-navy/5 disabled:opacity-40">
          Cancel
        </button>
        <button type="button" onClick={save} disabled={busy}
                data-testid={`escrow-acc-edit-save-${acc.id}`}
                className="px-5 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40">
          {busy ? "Saving…" : "Save institution &amp; both signers"}
        </button>
      </div>
    </div>
  );
}
