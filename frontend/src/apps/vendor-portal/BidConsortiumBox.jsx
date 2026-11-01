import { useState } from "react";
import { Link } from "react-router-dom";
import { consortiumApi, showApiError } from "@/lib/api";
import ConsortiumCard from "./ConsortiumCard";

export default function BidConsortiumBox({ noticeRef, me, items, reload, bidAs, setBidAs }) {
  const [name, setName] = useState("");
  const lead = items.find((c) => c.is_lead && c.status !== "withdrawn");
  const joined = items.find((c) => !c.is_lead && c.status !== "withdrawn" && (c.members || []).some((m) => m.vendor_id === me && m.status !== "declined"));
  const create = () => consortiumApi.create({ notice_ref: noticeRef, name }).then(() => { reload(); setBidAs("consortium"); }).catch(showApiError);
  if (joined) {
    return (
      <div className="border border-amber-300 bg-amber-50 rounded-md p-3 text-sm" data-testid="bid-consortium-member-note">
        You are a member of the consortium <b>{joined.name}</b> led by {joined.lead_company}. The lead submits one bid for the whole team, so you can't bid alone. <Link className="underline" to="/vendor/consortia">Open my consortia</Link>
      </div>);
  }
  return (
    <div className="border rounded-md p-3 space-y-2 bg-slate-50" data-testid="bid-consortium">
      <div className="text-sm font-semibold text-slate-900">This tender accepts consortium bids</div>
      <div className="flex gap-4 text-sm">
        <label className="flex gap-1 items-center"><input type="radio" checked={bidAs === "alone"} onChange={() => setBidAs("alone")} disabled={!!lead} data-testid="bid-as-alone" />Bid alone</label>
        <label className="flex gap-1 items-center"><input type="radio" checked={bidAs === "consortium"} onChange={() => setBidAs("consortium")} data-testid="bid-as-consortium" />Bid as consortium lead</label>
      </div>
      {lead && <div className="text-xs text-slate-600">You lead a consortium on this tender, so the bid goes in on its behalf. Withdraw it to bid alone.</div>}
      {bidAs === "consortium" && !lead && (
        <div className="flex gap-2 flex-wrap">
          <input className="border rounded-md px-2 py-1.5 text-sm" placeholder="Consortium name" value={name} onChange={(e) => setName(e.target.value)} data-testid="bid-consortium-name" />
          <button type="button" className="px-3 py-1.5 bg-slate-900 text-white rounded-md text-sm" onClick={create} data-testid="bid-consortium-create">Form consortium</button>
        </div>)}
      {lead && <ConsortiumCard c={lead} me={me} onChange={reload} />}
    </div>);
}
