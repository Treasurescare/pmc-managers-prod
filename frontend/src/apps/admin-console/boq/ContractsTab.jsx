import { toast } from "sonner";
import { contractApi, formatApiError } from "@/lib/api";

/**
 * ContractsTab — extracted from BOQContractsPanel. Renders the contract list
 * plus the new-contract form. Awarded-bid dropdown drives vendor + notice_ref.
 */
export default function ContractsTab({
  contracts, awardedBids, showNewContract, setShowNewContract,
  contractDraft, setContractDraft, onReload,
}) {
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
      onReload();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const completeMilestone = async (contract, order) => {
    try {
      await contractApi.completeMilestone(contract.id, order);
      toast.success("Milestone completed");
      onReload();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  return (
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
  );
}
