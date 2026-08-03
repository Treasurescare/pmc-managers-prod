import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { boqApi, contractApi, bidApi, formatApiError } from "@/lib/api";
import BOQTemplatesTab from "./boq/BOQTemplatesTab";
import ContractsTab from "./boq/ContractsTab";

export default function BOQContractsPanel() {
  const [tab, setTab] = useState("boq");
  const [templates, setTemplates] = useState([]);
  const [contracts, setContracts] = useState([]);
  const [awardedBids, setAwardedBids] = useState([]);
  const [showNewTmpl, setShowNewTmpl] = useState(false);
  const [tmplDraft, setTmplDraft] = useState({ name: "", notice_ref: "", currency: "USD" });
  const [selectedTmpl, setSelectedTmpl] = useState(null);
  const [showNewContract, setShowNewContract] = useState(false);
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
    } catch (e) { toast.error(formatApiError(e)); }
  }, []);
  useEffect(() => { load(); }, [load]);

  return (
    <div data-testid="admin-boq-panel">
      <div className="flex gap-2 mb-4 border-b">
        {[["boq", "BOQ Templates"], ["contracts", "Contracts"]].map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`px-4 py-2 text-xs uppercase tracking-widest ${tab === k ? "border-b-2 border-brand-navy font-semibold" : "text-slate-500"}`}
            data-testid={`boq-tab-${k}`}>{l}</button>
        ))}
      </div>

      {tab === "boq" && (
        <BOQTemplatesTab
          templates={templates}
          showNewTmpl={showNewTmpl} setShowNewTmpl={setShowNewTmpl}
          tmplDraft={tmplDraft} setTmplDraft={setTmplDraft}
          selectedTmpl={selectedTmpl} setSelectedTmpl={setSelectedTmpl}
          onReload={load}
        />
      )}

      {tab === "contracts" && (
        <ContractsTab
          contracts={contracts} awardedBids={awardedBids}
          showNewContract={showNewContract} setShowNewContract={setShowNewContract}
          contractDraft={contractDraft} setContractDraft={setContractDraft}
          onReload={load}
        />
      )}
    </div>
  );
}
