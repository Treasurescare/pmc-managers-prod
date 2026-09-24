import TopBar from "@/apps/shared/TopBar";
import PmcFooter from "@/components/PmcFooter";

export default function VisionMission() {
  return (
    <div className="min-h-screen bg-brand-pale flex flex-col" data-testid="page-vision">
      <TopBar />
      <main className="flex-1">
        <section className="max-w-4xl mx-auto px-6 lg:px-10 pt-16 pb-4">
          <div className="pmc-label text-brand-gold">Vision &amp; Mission</div>
          <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl text-brand-navy leading-tight mt-3">
            Every public dollar, spent in the open.
          </h1>
        </section>

        <section className="max-w-4xl mx-auto px-6 lg:px-10 py-10 grid gap-10 md:grid-cols-2">
          <div className="bg-white border border-brand-navy/10 p-8">
            <div className="pmc-label text-brand-gold">Our vision</div>
            <h2 className="font-display text-2xl text-brand-navy mt-2">A borderless
              public-procurement ledger.</h2>
            <p className="mt-4 text-brand-navy/75 leading-relaxed">
              A world where any government, sovereign fund or municipality
              can publish a tender in minutes, evaluate on merit alone, and
              hand the audit trail to any regulator on Earth — instantly,
              verifiably, and without a paper folder ever changing hands.
            </p>
          </div>
          <div className="bg-brand-navy text-white/85 p-8">
            <div className="pmc-label text-brand-gold">Our mission</div>
            <h2 className="font-display text-2xl text-white mt-2">Institutional
              procurement at consumer-software velocity.</h2>
            <p className="mt-4 leading-relaxed">
              We ship the fastest, most defensible tender lifecycle
              platform on the market — AI-drafted DPRs, country-specific
              master templates, reverse auctions, moderated vendor trust
              badges, and DocuSign-native contract close — with every write
              nailed to an immutable audit log.
            </p>
          </div>
        </section>

        <section className="max-w-4xl mx-auto px-6 lg:px-10 py-10">
          <h2 className="font-display text-3xl text-brand-navy">Values we do not
            negotiate on.</h2>
          <div className="mt-6 grid gap-6 md:grid-cols-3">
            {[
              ["Fairness",     "Every bidder sees the same document at the same second."],
              ["Traceability", "Every mutation is written to the audit log — no exceptions."],
              ["Speed",        "AI drafts DPRs in seconds, not weeks."],
              ["Sovereignty",  "Country-first templates respect local regulatory nuance."],
              ["Confidentiality","EMD, technical scoring and pricing are sealed until unseal."],
              ["Auditability", "Any auditor can reconstruct any tender in five clicks."],
            ].map(([v, d]) => (
              <div key={v} className="border-l-2 border-brand-gold pl-4">
                <div className="font-display text-xl text-brand-navy">{v}</div>
                <div className="text-sm text-brand-navy/70 mt-1 leading-relaxed">{d}</div>
              </div>
            ))}
          </div>
        </section>
      </main>
      <PmcFooter />
    </div>
  );
}
