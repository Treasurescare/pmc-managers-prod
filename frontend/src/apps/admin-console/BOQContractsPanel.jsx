import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { boqApi, contractApi, bidApi, showApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import BOQTemplatesTab from "./boq/BOQTemplatesTab";
import ContractsTab from "./boq/ContractsTab";
import { useListPager } from "@/components/ListPager";

/**
 * BOQContractsPanel — v51ag.
 * Search + status + created-date filters that actually work for both tabs.
 * Date inputs enforce created_to >= created_from.
 */
export default function BOQContractsPanel() {
  const { t } = useI18n();
  const [tab, setTab] = useState("boq");
  const [templates, setTemplates] = useState([]);
  const [contracts, setContracts] = useState([]);
  const [awardedBids, setAwardedBids] = useState([]);
  const [showNewTmpl, setShowNewTmpl] = useState(false);
  const [tmplDraft, setTmplDraft] = useState({ name: "", notice_ref: "", currency: "USD" });
  const [selectedTmpl, setSelectedTmpl] = useState(null);
  const [showNewContract, setShowNewContract] = useState(false);
  // v51ag — filters shared across tabs
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [cFrom, setCFrom] = useState("");
  const [cTo, setCTo] = useState("");
  const [contractDraft, setContractDraft] = useState({
    notice_ref: "", bid_id: "", vendor_id: "", title: "", value: 0,
    currency: "USD", start_date: "", end_date: "",
    milestones: [{ order: 1, title: "Kickoff", amount: 0, due_date: "" }],
  });

  const load = useCallback(async () => {
    try {
      const [t, c, b] = await Promise.all([
        boqApi.listTemplates().catch(() => []),
        contractApi.list().catch(() => []),
        bidApi.list({ status: "awarded" }).catch(() => []),
      ]);
      setTemplates(t); setContracts(c); setAwardedBids(b);
    } catch (e) { showApiError(e); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const q = search.trim().toLowerCase();

  const inDateRange = (d) => {
    if (!d) return !cFrom && !cTo ? true : true;  // keep missing dates visible
    const only = d.slice(0, 10);
    if (cFrom && only < cFrom) return false;
    if (cTo   && only > cTo)   return false;
    return true;
  };

  const filteredTemplates = useMemo(() => templates.filter((x) => {
    if (q) {
      const hay = [x.name, x.notice_ref, x.currency, x.description]
        .filter(Boolean).join(" ").toLowerCase();
      if (!hay.includes(q)) return false;
    }
    if (status && (x.status || "").toLowerCase() !== status) return false;
    return inDateRange(x.created_at);
  }), [templates, q, status, cFrom, cTo]);

  const filteredContracts = useMemo(() => contracts.filter((c) => {
    if (q) {
      const hay = [c.title, c.notice_ref, c.vendor_name, c.vendor_ref, c.currency,
                   String(c.value ?? "")]
        .filter(Boolean).join(" ").toLowerCase();
      if (!hay.includes(q)) return false;
    }
    if (status && (c.status || "").toLowerCase() !== status) return false;
    return inDateRange(c.created_at || c.start_date);
  }), [contracts, q, status, cFrom, cTo]);

  const boqPager = useListPager(filteredTemplates, { testid: "boq-pager" });
  const contractsPager = useListPager(filteredContracts, { testid: "contract-pager" });

  const STATUS_OPTS_BY_TAB = {
    boq: ["draft", "published", "archived"],
    contracts: ["draft", "signed", "active", "completed", "cancelled"],
  };

  const clearFilters = () => { setSearch(""); setStatus(""); setCFrom(""); setCTo(""); };

  return (
    <div data-testid="admin-boq-panel">
      <div className="flex gap-2 mb-4 border-b items-center">
        {[["boq", t("panels.boq.tab_boq")], ["contracts", t("panels.boq.tab_contracts")]].map(([k, l]) => (
          <button key={k} onClick={() => { setTab(k); setStatus(""); }}
            className={`px-4 py-2 text-xs uppercase tracking-widest ${tab === k ? "border-b-2 border-brand-navy font-semibold" : "text-slate-500"}`}
            data-testid={`boq-tab-${k}`}>{l}</button>
        ))}
      </div>

      {/* v51ag — richer filter bar */}
      <div className="bg-white border border-brand-navy/15 rounded px-3 py-3 mb-4 flex flex-wrap items-end gap-3"
           data-testid="boq-filter-bar">
        <label className="flex flex-col flex-1 min-w-[220px]">
          <span className="pmc-label text-[10px]">Search</span>
          <input value={search} onChange={(e) => setSearch(e.target.value)}
                 placeholder={tab === "boq"
                   ? "Template name, notice ref, currency…"
                   : "Contract title, vendor, notice ref, value…"}
                 data-testid="boq-search"
                 className="mt-1 px-2 py-1.5 border border-brand-navy/15 text-sm"/>
        </label>
        <label className="flex flex-col min-w-[150px]">
          <span className="pmc-label text-[10px]">Status</span>
          <select value={status} onChange={(e) => setStatus(e.target.value)}
                  data-testid="boq-status"
                  className="mt-1 px-2 py-1.5 border border-brand-navy/15 text-sm bg-white">
            <option value="">All</option>
            {STATUS_OPTS_BY_TAB[tab].map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col">
          <span className="pmc-label text-[10px]">Created from</span>
          <input type="date" value={cFrom}
                 max={cTo || undefined}
                 onChange={(e) => {
                   const v = e.target.value;
                   if (v && cTo && v > cTo) {
                     toast.error('"Created from" cannot be later than "Created to"');
                     return;
                   }
                   setCFrom(v);
                 }}
                 data-testid="boq-cfrom"
                 className="mt-1 px-2 py-1.5 border border-brand-navy/15 text-sm"/>
        </label>
        <label className="flex flex-col">
          <span className="pmc-label text-[10px]">Created to</span>
          <input type="date" value={cTo}
                 min={cFrom || undefined}
                 onChange={(e) => {
                   const v = e.target.value;
                   if (v && cFrom && v < cFrom) {
                     toast.error('"Created to" cannot be earlier than "Created from"');
                     return;
                   }
                   setCTo(v);
                 }}
                 data-testid="boq-cto"
                 className="mt-1 px-2 py-1.5 border border-brand-navy/15 text-sm"/>
        </label>
        <button type="button" onClick={clearFilters}
                data-testid="boq-clear"
                className="px-3 py-2 text-[10px] uppercase tracking-widest border border-brand-navy/20 text-brand-navy/70 hover:bg-brand-navy/5">
          Clear
        </button>
      </div>

      {tab === "boq" && (
        <>
          <BOQTemplatesTab
            templates={boqPager.paged}
            showNewTmpl={showNewTmpl} setShowNewTmpl={setShowNewTmpl}
            tmplDraft={tmplDraft} setTmplDraft={setTmplDraft}
            selectedTmpl={selectedTmpl} setSelectedTmpl={setSelectedTmpl}
            onReload={load}
          />
          {boqPager.controls}
        </>
      )}

      {tab === "contracts" && (
        <>
          <ContractsTab
            contracts={contractsPager.paged}
            awardedBids={awardedBids}
            showNewContract={showNewContract} setShowNewContract={setShowNewContract}
            contractDraft={contractDraft} setContractDraft={setContractDraft}
            onReload={load}
          />
          {contractsPager.controls}
        </>
      )}
    </div>
  );
}
