import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { boqApi, contractApi, bidApi, formatApiError, showApiError} from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import BOQTemplatesTab from "./boq/BOQTemplatesTab";
import ContractsTab from "./boq/ContractsTab";

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
  const [search, setSearch] = useState("");
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

  return (
    <div data-testid="admin-boq-panel">
      <div className="flex gap-2 mb-4 border-b items-center">
        {[["boq", t("panels.boq.tab_boq")], ["contracts", t("panels.boq.tab_contracts")]].map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`px-4 py-2 text-xs uppercase tracking-widest ${tab === k ? "border-b-2 border-brand-navy font-semibold" : "text-slate-500"}`}
            data-testid={`boq-tab-${k}`}>{l}</button>
        ))}
        <input value={search} onChange={(e) => setSearch(e.target.value)}
          placeholder={tab === "boq" ? "Search templates by name or notice ref…" : "Search contracts by title or notice ref…"}
          data-testid="boq-search"
          className="ml-auto mb-1 px-3 py-1.5 border border-brand-navy/20 text-sm bg-white min-w-[240px]" />
      </div>

      {tab === "boq" && (
        <BOQTemplatesTab
          templates={(() => { const q = search.trim().toLowerCase(); return q
            ? templates.filter((x) => (x.name || "").toLowerCase().includes(q)
                || (x.notice_ref || "").toLowerCase().includes(q))
            : templates; })()}
          showNewTmpl={showNewTmpl} setShowNewTmpl={setShowNewTmpl}
          tmplDraft={tmplDraft} setTmplDraft={setTmplDraft}
          selectedTmpl={selectedTmpl} setSelectedTmpl={setSelectedTmpl}
          onReload={load}
        />
      )}

      {tab === "contracts" && (
        <ContractsTab
          contracts={(() => { const q = search.trim().toLowerCase(); return q
            ? contracts.filter((c) => (c.title || "").toLowerCase().includes(q)
                || (c.notice_ref || "").toLowerCase().includes(q)
                || (c.vendor_name || "").toLowerCase().includes(q))
            : contracts; })()}
          awardedBids={awardedBids}
          showNewContract={showNewContract} setShowNewContract={setShowNewContract}
          contractDraft={contractDraft} setContractDraft={setContractDraft}
          onReload={load}
        />
      )}
    </div>
  );
}
