import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { boqApi, contractApi, bidApi, formatApiError } from "@/lib/api";

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

  const createTemplate = async () => {
    if (!tmplDraft.name) return toast.error("Name required");
    try {
      await boqApi.createTemplate({ ...tmplDraft, items: [] });
      toast.success("Template created");
      setShowNewTmpl(false); setTmplDraft({ name: "", notice_ref: "", currency: "USD" });
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const importExcel = async (tmpl, file) => {
    try {
      const r = await boqApi.importExcel(tmpl.id, file);
      toast.success(`Imported ${r.items} items`);
      load();
      if (selectedTmpl?.id === tmpl.id) setSelectedTmpl(await boqApi.getTemplate(tmpl.id));
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const viewTemplate = async (tmpl) => setSelectedTmpl(await boqApi.getTemplate(tmpl.id));

  const createContract = async () => {
    const bid = awardedBids.find((b) => b.id === contractDraft.bid_id);
    if (!bid) return toast.error("Pick an awarded bid");
    const payload = {
      ...contractDraft,
      notice_ref: bid.notice_ref,
      vendor_id: bid.vendor_id,
      value: Number(contractDraft.value),
      milestones: contractDraft.milestones.map((m, i) => ({
        ...m, order: i + 1, amount: Number(m.amount || 0),
        due_date: m.due_date ? new Date(m.due_date).toISOString() : new Date().toISOString(),
      })),
      obligations: [],
      start_date: contractDraft.start_date ? new Date(contractDraft.start_date).toISOString() : new Date().toISOString(),
      end_date: contractDraft.end_date ? new Date(contractDraft.end_date).toISOString() : new Date().toISOString(),
    };
    try {
      await contractApi.create(payload);
      toast.success("Contract created");
      setShowNewContract(false);
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const completeMilestone = async (contract, order) => {
    try {
      await contractApi.completeMilestone(contract.id, order);
      toast.success("Milestone completed");
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

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
        <>
          <div className="flex justify-between mb-4">
            <div className="text-sm text-brand-navy/70">{templates.length} BOQ templates</div>
            <button onClick={() => setShowNewTmpl(!showNewTmpl)} data-testid="boq-new-toggle"
              className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white">
              {showNewTmpl ? "Cancel" : "New BOQ Template"}
            </button>
          </div>
          {showNewTmpl && (
            <div className="bg-white border p-4 mb-4 grid gap-2 md:grid-cols-3" data-testid="boq-new-form">
              <input placeholder="Template name" value={tmplDraft.name}
                onChange={(e) => setTmplDraft({ ...tmplDraft, name: e.target.value })}
                className="px-3 py-2 border" data-testid="boq-name" />
              <input placeholder="Linked notice ref (optional)" value={tmplDraft.notice_ref}
                onChange={(e) => setTmplDraft({ ...tmplDraft, notice_ref: e.target.value })}
                className="px-3 py-2 border" data-testid="boq-notice-ref" />
              <input placeholder="Currency" value={tmplDraft.currency}
                onChange={(e) => setTmplDraft({ ...tmplDraft, currency: e.target.value })}
                className="px-3 py-2 border" />
              <button onClick={createTemplate} data-testid="boq-create"
                className="md:col-span-3 px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy-soft text-white">
                Create
              </button>
            </div>
          )}
          <div className="bg-white border">
            {templates.map((t) => (
              <div key={t.id} className="border-b p-3 flex justify-between items-center"
                data-testid={`boq-row-${t.id}`}>
                <div>
                  <div className="font-semibold text-sm">{t.name}</div>
                  <div className="text-xs text-slate-500">
                    {t.notice_ref || "—"} · {(t.items || []).length} items · {t.currency}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <label className="px-3 py-1.5 text-xs border cursor-pointer">
                    Import Excel
                    <input type="file" accept=".xlsx,.xls" hidden
                      onChange={(e) => e.target.files?.[0] && importExcel(t, e.target.files[0])}
                      data-testid={`boq-import-${t.id}`} />
                  </label>
                  <button onClick={() => viewTemplate(t)} data-testid={`boq-view-${t.id}`}
                    className="text-xs border px-3 py-1.5">View</button>
                </div>
              </div>
            ))}
          </div>
          {selectedTmpl && (
            <div className="mt-4 bg-white border p-4" data-testid="boq-viewer">
              <div className="font-serif text-lg">{selectedTmpl.name}</div>
              <table className="w-full text-xs mt-2">
                <thead className="text-slate-500">
                  <tr><th className="text-left">Sl.</th><th className="text-left">Description</th>
                    <th>Unit</th><th>Qty</th><th className="text-right">Unit Rate</th></tr>
                </thead>
                <tbody>
                  {(selectedTmpl.items || []).map((it, i) => (
                    <tr key={`boq-item-${it.sl_no ?? i}`} className="border-t">
                      <td className="py-1">{it.sl_no}</td><td>{it.description}</td>
                      <td className="text-center">{it.unit}</td>
                      <td className="text-center">{it.quantity}</td>
                      <td className="text-right">{it.unit_rate?.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {tab === "contracts" && (
        <>
          <div className="flex justify-between mb-4">
            <div className="text-sm text-brand-navy/70">{contracts.length} contracts</div>
            <button onClick={() => setShowNewContract(!showNewContract)} data-testid="contract-new-toggle"
              className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white">
              {showNewContract ? "Cancel" : "New Contract"}
            </button>
          </div>
          {showNewContract && (
            <div className="bg-white border p-4 mb-4 grid gap-2 md:grid-cols-2" data-testid="contract-new-form">
              <label className="text-sm md:col-span-2">
                <span>Awarded bid</span>
                <select value={contractDraft.bid_id}
                  onChange={(e) => setContractDraft({ ...contractDraft, bid_id: e.target.value })}
                  className="mt-1 w-full px-3 py-2 border" data-testid="contract-bid">
                  <option value="">Select…</option>
                  {awardedBids.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.bid_ref} — {b.company_name || b.vendor_email} — {b.price_currency} {b.price_amount?.toLocaleString()}
                    </option>
                  ))}
                </select>
              </label>
              <input placeholder="Contract title" value={contractDraft.title}
                onChange={(e) => setContractDraft({ ...contractDraft, title: e.target.value })}
                className="px-3 py-2 border" data-testid="contract-title" />
              <input type="number" placeholder="Value" value={contractDraft.value}
                onChange={(e) => setContractDraft({ ...contractDraft, value: e.target.value })}
                className="px-3 py-2 border" data-testid="contract-value" />
              <input type="date" placeholder="Start" value={contractDraft.start_date}
                onChange={(e) => setContractDraft({ ...contractDraft, start_date: e.target.value })}
                className="px-3 py-2 border" />
              <input type="date" placeholder="End" value={contractDraft.end_date}
                onChange={(e) => setContractDraft({ ...contractDraft, end_date: e.target.value })}
                className="px-3 py-2 border" />
              <button onClick={createContract} data-testid="contract-create"
                className="md:col-span-2 px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy-soft text-white">
                Create contract
              </button>
            </div>
          )}
          <div className="bg-white border">
            {contracts.map((c) => (
              <div key={c.id} className="border-b p-3" data-testid={`contract-row-${c.contract_ref}`}>
                <div className="flex justify-between">
                  <div>
                    <div className="font-mono text-xs text-brand-navy-soft">{c.contract_ref}</div>
                    <div className="text-sm font-semibold">{c.title}</div>
                    <div className="text-xs text-slate-500">
                      {c.currency} {(c.value || 0).toLocaleString()} · status {c.status}
                    </div>
                  </div>
                </div>
                {c.milestones?.length > 0 && (
                  <div className="mt-2 grid grid-cols-3 gap-2">
                    {c.milestones.map((m) => (
                      <div key={m.order} className="border p-2 text-xs">
                        <div>{m.title}</div>
                        <div className="text-slate-500">{m.status}</div>
                        {m.status !== "completed" && (
                          <button onClick={() => completeMilestone(c, m.order)}
                            data-testid={`milestone-${c.contract_ref}-${m.order}`}
                            className="mt-1 text-[10px] bg-emerald-600 text-white px-2 py-0.5">
                            Mark complete
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {contracts.length === 0 && (
              <div className="p-6 text-sm text-slate-500">No contracts yet.</div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
