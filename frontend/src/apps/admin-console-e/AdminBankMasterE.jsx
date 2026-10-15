import { useEffect, useState } from "react";
import { toast } from "sonner";
import AdminEShell from "./AdminEShell";
import { api, showApiError } from "@/lib/api";

/**
 * AdminBankMasterE — v52e. Review-and-curate screen for banks that
 * registrants have added via the escrow banking "+ Add" affordance.
 *
 * Backend contract:
 *   GET  /api/v1/masters/banks-admin/suggested
 *   POST /api/v1/masters/banks-admin/{id}/approve  { swift_prefix, currencies[], aliases[] }
 *   POST /api/v1/masters/banks-admin/{id}/merge    { target_id }
 *   DEL  /api/v1/masters/banks-admin/{id}
 *   GET  /api/v1/masters/banks?country_code=XX     (same-country merge targets)
 */
export default function AdminBankMasterE() {
  const [items, setItems] = useState([]);
  const [sel, setSel] = useState(null);
  const [targets, setTargets] = useState([]);
  const [edit, setEdit] = useState({ swift_prefix: "", currencies: "", aliases: "" });
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const r = (await api.get("/api/v1/masters/banks-admin/suggested")).data;
      setItems(r.items || []);
    } catch (e) { showApiError(e); }
  };
  useEffect(() => { load(); }, []);

  useEffect(() => {
    if (!sel) return;
    setEdit({
      swift_prefix: sel.swift_prefix || "",
      currencies: (sel.currencies || []).join(", "),
      aliases: (sel.aliases || []).join(", "),
    });
    api.get("/api/v1/masters/banks", { params: { country_code: sel.country_code, limit: 200 } })
      .then((r) => setTargets(r.data.filter((b) => b._id !== sel._id)))
      .catch(() => setTargets([]));
  }, [sel]);

  const approve = async () => {
    if (!sel) return;
    setBusy(true);
    try {
      await api.post(`/api/v1/masters/banks-admin/${sel._id}/approve`, {
        swift_prefix: edit.swift_prefix.trim() || null,
        currencies: edit.currencies.split(",").map((s) => s.trim()).filter(Boolean),
        aliases: edit.aliases.split(",").map((s) => s.trim()).filter(Boolean),
      });
      toast.success(`${sel.name} promoted to curated roster`);
      setSel(null);
      load();
    } catch (e) { showApiError(e); }
    finally { setBusy(false); }
  };

  const mergeInto = async (target) => {
    if (!sel) return;
    if (!window.confirm(`Merge "${sel.name}" into "${target.name}"? The suggestion will be deleted; "${sel.name}" becomes an alias of the target so searches still match.`)) return;
    setBusy(true);
    try {
      await api.post(`/api/v1/masters/banks-admin/${sel._id}/merge`,
                      { target_id: target._id });
      toast.success(`Merged into ${target.name}`);
      setSel(null);
      load();
    } catch (e) { showApiError(e); }
    finally { setBusy(false); }
  };

  const reject = async () => {
    if (!sel) return;
    if (!window.confirm(`Reject the suggestion "${sel.name}" (${sel.country_code})? It will be removed from the bank list.`)) return;
    setBusy(true);
    try {
      await api.delete(`/api/v1/masters/banks-admin/${sel._id}`);
      toast.success("Suggestion rejected");
      setSel(null);
      load();
    } catch (e) { showApiError(e); }
    finally { setBusy(false); }
  };

  return (
    <AdminEShell active="Masters" crumb="Procurement / Masters / Suggested banks">
      <div className="p-6" data-testid="admin-bank-master-page">
        <div className="flex items-start justify-between gap-4 mb-4 flex-wrap">
          <div>
            <h1 className="text-2xl font-semibold text-brand-navy">Suggested banks curation</h1>
            <p className="text-sm text-brand-navy/60 mt-1">
              Review banks that escrow registrants have added via the “+ Add bank”
              affordance. Approve to promote into the curated roster, merge into an
              existing entry if it’s a duplicate, or reject if it’s spam / wrong.
            </p>
          </div>
          <div className="text-xs text-brand-navy/70 bg-white border border-brand-navy/15 px-3 py-2"
               data-testid="admin-bank-master-count">
            {items.length} pending
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          <section className="lg:col-span-2 bg-white border border-brand-navy/15"
                   data-testid="admin-bank-master-list">
            {items.length === 0 ? (
              <div className="p-6 text-sm text-brand-navy/50">
                No pending suggestions. Everything curated — nice.
              </div>
            ) : (
              <ul className="divide-y divide-brand-navy/10">
                {items.map((b) => (
                  <li key={b._id}>
                    <button type="button"
                            onClick={() => setSel(b)}
                            data-testid={`admin-bank-suggested-${b._id}`}
                            className={"text-left w-full px-4 py-3 hover:bg-brand-pale " +
                                        (sel?._id === b._id ? "bg-brand-pale" : "")}>
                      <div className="flex items-center justify-between gap-2">
                        <strong className="text-brand-navy">{b.name}</strong>
                        <span className="text-[10px] uppercase tracking-widest text-brand-navy/60">
                          {b.country_code}
                        </span>
                      </div>
                      <div className="text-xs text-brand-navy/60 mt-0.5">
                        swift {b.swift_prefix || "—"} · {(b.currencies || []).join(", ") || "no currencies"}
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="lg:col-span-3 bg-white border border-brand-navy/15 p-6"
                   data-testid="admin-bank-master-detail">
            {!sel && (
              <div className="text-sm text-brand-navy/50">
                Pick a suggestion to review it.
              </div>
            )}
            {sel && (
              <div className="space-y-5">
                <div>
                  <div className="text-[10px] uppercase tracking-widest text-brand-navy/60">Bank</div>
                  <h2 className="text-xl font-semibold text-brand-navy mt-1">{sel.name}</h2>
                  <div className="text-xs text-brand-navy/60">
                    {sel.country_code} · submitted via public registration
                  </div>
                </div>

                <div className="grid gap-3 md:grid-cols-3 text-sm">
                  <label>
                    <span className="block text-[10px] uppercase tracking-widest text-brand-navy/70">SWIFT prefix</span>
                    <input className="mt-1 w-full px-2 py-1 border border-brand-navy/20 font-mono text-xs"
                           value={edit.swift_prefix}
                           data-testid="admin-bank-swift"
                           onChange={(e) => setEdit({ ...edit, swift_prefix: e.target.value.toUpperCase() })} />
                  </label>
                  <label>
                    <span className="block text-[10px] uppercase tracking-widest text-brand-navy/70">Currencies (comma-sep)</span>
                    <input className="mt-1 w-full px-2 py-1 border border-brand-navy/20 text-xs"
                           value={edit.currencies}
                           data-testid="admin-bank-currencies"
                           onChange={(e) => setEdit({ ...edit, currencies: e.target.value })}
                           placeholder="e.g. GBP, EUR, USD" />
                  </label>
                  <label>
                    <span className="block text-[10px] uppercase tracking-widest text-brand-navy/70">Aliases (comma-sep)</span>
                    <input className="mt-1 w-full px-2 py-1 border border-brand-navy/20 text-xs"
                           value={edit.aliases}
                           data-testid="admin-bank-aliases"
                           onChange={(e) => setEdit({ ...edit, aliases: e.target.value })}
                           placeholder="e.g. Revolut Ltd, Revolut UK" />
                  </label>
                </div>

                <div className="flex flex-wrap gap-2">
                  <button type="button" onClick={approve} disabled={busy}
                          data-testid="admin-bank-approve"
                          className="px-4 py-2 text-xs uppercase tracking-widest bg-emerald-700 text-white hover:bg-emerald-800 disabled:opacity-50">
                    {busy ? "…" : "Approve → curated"}
                  </button>
                  <button type="button" onClick={reject} disabled={busy}
                          data-testid="admin-bank-reject"
                          className="px-4 py-2 text-xs uppercase tracking-widest border border-red-700 text-red-700 hover:bg-red-700 hover:text-white disabled:opacity-50">
                    Reject
                  </button>
                </div>

                <div>
                  <div className="text-[10px] uppercase tracking-widest text-brand-navy/70 mb-1">
                    Looks like a duplicate? Merge into another {sel.country_code} bank:
                  </div>
                  {targets.length === 0 ? (
                    <div className="text-xs text-brand-navy/50">
                      No other banks for {sel.country_code} to merge into.
                    </div>
                  ) : (
                    <ul className="divide-y divide-brand-navy/10 border border-brand-navy/10 max-h-56 overflow-auto"
                        data-testid="admin-bank-merge-list">
                      {targets.map((t) => (
                        <li key={t._id}
                            className="flex items-center justify-between px-3 py-2 text-sm">
                          <div>
                            <strong>{t.name}</strong>
                            <div className="text-[11px] text-brand-navy/50 font-mono">
                              {t.swift_prefix || "no swift"} · {(t.currencies || []).join(", ") || "no currencies"}
                            </div>
                          </div>
                          <button type="button" onClick={() => mergeInto(t)} disabled={busy}
                                  data-testid={`admin-bank-merge-into-${t._id}`}
                                  className="px-2 py-1 text-[10px] uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-navy hover:text-white">
                            Merge into
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            )}
          </section>
        </div>
      </div>
    </AdminEShell>
  );
}
