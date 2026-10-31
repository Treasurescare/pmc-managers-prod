import { useEffect, useState } from "react";
import { agentApi, showApiError } from "@/lib/api";

export const BoardTable = ({ rows, showId }) => (
  <table className="w-full text-sm bg-white border border-brand-navy/15" data-testid="leaderboard-table">
    <thead><tr className="text-[10px] uppercase tracking-widest text-brand-navy/60 text-left"><th className="p-2">Rank</th><th className="p-2">Partner</th><th className="p-2 text-right">Approved suppliers</th><th className="p-2 text-right">Invites sent</th></tr></thead>
    <tbody>
      {rows.map((r) => (
        <tr key={showId ? r.id : `${r.rank}-${r.code}`} className={"border-t " + (r.is_me ? "bg-brand-gold/10 font-semibold" : "")} data-testid={`leaderboard-row-${r.code}`}>
          <td className="p-2">#{r.rank}</td><td className="p-2">{r.label || r.name}{showId && <span className="text-xs text-brand-navy/60"> · {r.code}</span>}{r.is_me && " (you)"}</td>
          <td className="p-2 text-right">{r.approved}</td><td className="p-2 text-right">{r.invites}</td>
        </tr>))}
      {!rows.length && <tr><td colSpan={4} className="p-4 text-center text-brand-navy/60">No partners yet.</td></tr>}
    </tbody>
  </table>
);

export default function PartnerLeaderboard() {
  const [b, setB] = useState(null);
  useEffect(() => { agentApi.leaderboard().then(setB).catch(showApiError); }, []);
  if (!b) return <div className="text-sm text-brand-navy/50">Loading…</div>;
  return (
    <div className="space-y-3" data-testid="partner-leaderboard">
      <div className="bg-white border border-brand-gold p-4" data-testid="leaderboard-me">
        <div className="text-[10px] uppercase tracking-widest text-brand-navy/60">This month · {b.month}</div>
        <div className="text-2xl font-semibold">#{b.me?.rank} <span className="text-sm font-normal text-brand-navy/70">of {b.partners} partners</span></div>
        <div className="text-sm">{b.me?.approved} supplier{b.me?.approved === 1 ? "" : "s"} approved · {b.me?.invites} invite{b.me?.invites === 1 ? "" : "s"} sent</div>
      </div>
      <BoardTable rows={b.rows} />
      <p className="text-xs text-brand-navy/60">Ranked by suppliers approved this month, then invites sent.{b.show_names ? "" : " Other partners are shown by partner code."}</p>
    </div>
  );
}
