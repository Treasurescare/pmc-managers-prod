import { useEffect, useState } from "react";
import { agentApi, showApiError } from "@/lib/api";

const prevMonth = () => { const d = new Date(); d.setUTCDate(1); d.setUTCMonth(d.getUTCMonth() - 1); return d.toISOString().slice(0, 7); };

export const BadgeChip = ({ label }) => (
  <span className="inline-flex items-center gap-1 mr-2 mb-1 px-2 py-0.5 text-[10px] uppercase tracking-widest bg-amber-100 text-amber-900 border border-amber-300" data-testid="partner-badge">★ {label}</span>
);

const MyBadges = () => {
  const [b, setB] = useState(null);
  const [month, setMonth] = useState(prevMonth());
  useEffect(() => { agentApi.badges().then(setB).catch(() => {}); }, []);
  return (
    <div className="bg-white border border-brand-navy/15 p-4 space-y-2" data-testid="partner-badges">
      <div className="text-sm"><b>Badges this month:</b> {b?.this_month?.length ? b.this_month.map((x) => <BadgeChip key={x.key} label={x.label} />) : <span className="text-brand-navy/60">none yet — get suppliers approved to earn one</span>}</div>
      {b?.last_month?.length > 0 && <div className="text-sm"><b>Last month ({b.last}):</b> {b.last_month.map((x) => <BadgeChip key={x.key} label={x.label} />)}</div>}
      <div className="flex gap-2 items-center flex-wrap text-sm">Monthly statement
        <input type="month" className="px-2 py-1 border" value={month} onChange={(e) => setMonth(e.target.value)} data-testid="statement-month" />
        <button type="button" className="pmc-btn pmc-btn--secondary" onClick={() => agentApi.openStatement(`/api/v1/agents/me/statement.pdf?month=${month}`).catch(showApiError)} data-testid="statement-download">Download PDF</button>
        <span className="text-xs text-brand-navy/60">Emailed to you on the 1st of every month.</span></div>
    </div>
  );
};

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
      <MyBadges />
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
