import TopBar from "@/apps/shared/TopBar";
import PmcFooter from "@/components/PmcFooter";

export default function AboutUs() {
  return (
    <div className="min-h-screen bg-brand-pale flex flex-col" data-testid="page-about">
      <TopBar />
      <main className="flex-1">
        <section className="max-w-4xl mx-auto px-6 lg:px-10 pt-16 pb-10">
          <div className="pmc-label text-brand-gold">Who we are</div>
          <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl text-brand-navy leading-tight mt-3">
            The world's most trusted public-procurement authority.
          </h1>
          <p className="mt-6 text-lg text-brand-navy/75 leading-relaxed">
            Since 2018, PMC Managers Limited has designed, published and
            adjudicated over <b className="text-brand-navy">1,400 public tenders</b> across 11
            jurisdictions — from healthcare townships in Kazakhstan to
            highway packages in India, gas-turbine retrofits in the UK, and
            desalination framework agreements in the UAE. We are the
            operational engine that governments, sovereign wealth funds,
            and Big-4 advisors rely on when the bid must be fair, defensible
            and irrevocable.
          </p>
        </section>

        <section className="bg-white border-y border-brand-navy/10 py-14">
          <div className="max-w-4xl mx-auto px-6 lg:px-10 grid gap-10 md:grid-cols-3">
            {[
              ["1,400+", "Tenders published", "Since 2018 across 11 countries"],
              ["USD 62B", "Contracted value", "Aggregate award value to date"],
              ["11", "Jurisdictions", "KZ · IN · GB · AE · US · SA · NG · PL · TR · RU · UZ"],
            ].map(([n, l, sub]) => (
              <div key={l}>
                <div className="font-display text-5xl text-brand-navy">{n}</div>
                <div className="pmc-label text-brand-gold mt-2">{l}</div>
                <div className="text-sm text-brand-navy/70 mt-2">{sub}</div>
              </div>
            ))}
          </div>
        </section>

        <section className="max-w-4xl mx-auto px-6 lg:px-10 py-16">
          <h2 className="font-display text-3xl text-brand-navy">A one-stop lifecycle engine.</h2>
          <p className="mt-4 text-brand-navy/75 leading-relaxed">
            Every tender we publish moves through the same immutable spine —
            notice, corrigenda, registration, EMD, bid, evaluation, award,
            DocuSign, invoicing, and post-contract audit — with a full audit
            trail written on every write. Nine role-based portals sit on top
            of that spine, so the escrow agent, the certifier, the legal
            counsel, the accounting officer, the technical evaluator and the
            committee can all act in parallel without stepping on each other.
          </p>
          <ul className="mt-6 grid gap-3 text-brand-navy/85 md:grid-cols-2">
            <li>· AI-drafted DPR ingestion (v46g deep-dive)</li>
            <li>· Country-first master templates</li>
            <li>· Reverse auctions with spectator link</li>
            <li>· Vendor trust badges + moderated public reviews</li>
            <li>· Flexible fee slabs, escrow, refunds</li>
            <li>· DocuSign-signed contracts</li>
          </ul>
        </section>
      </main>
      <PmcFooter />
    </div>
  );
}
