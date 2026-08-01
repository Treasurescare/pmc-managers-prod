import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { registrationApi, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import TopBar from "@/apps/shared/TopBar";
import Footer from "@/apps/shared/Footer";
import { toast } from "sonner";

export default function RegistrationStatus() {
  const { t } = useI18n();
  const [params] = useSearchParams();
  const [token, setToken] = useState(params.get("token") || "");
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);

  const check = async (tk) => {
    if (!tk) return;
    setBusy(true);
    try {
      const s = await registrationApi.status(tk);
      setStatus(s);
    } catch (err) {
      toast.error(formatApiError(err));
      setStatus(null);
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => { if (params.get("token")) check(params.get("token")); }, [params]);

  return (
    <div className="min-h-screen bg-brand-pale flex flex-col">
      <TopBar />
      <main className="flex-1 max-w-3xl mx-auto w-full px-6 py-16">
        <div className="pmc-label">Registration</div>
        <h1 className="font-display text-3xl mt-2 text-brand-navy">Check status</h1>
        <p className="text-brand-navy/70 mt-3">Paste the token from your registration email to see the current status.</p>
        <div className="mt-8 flex gap-3">
          <input
            type="text"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="Paste your resume/status token"
            data-testid="status-token"
            className="flex-1 px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white font-mono text-sm"
          />
          <button
            type="button"
            onClick={() => check(token)}
            disabled={busy || !token}
            data-testid="status-check"
            className="px-6 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40"
          >
            {busy ? t("common.loading") : "Check"}
          </button>
        </div>
        {status && (
          <div className="mt-8 border border-brand-navy/10 bg-white p-8" data-testid="status-result">
            <div className="pmc-label">Status</div>
            <div className="font-display text-2xl text-brand-navy mt-1">{status.status}</div>
            {status.vendor_ref && <div className="mt-3 font-mono text-brand-navy-soft">Supplier ref: {status.vendor_ref}</div>}
            {status.reviewer_notes && <div className="mt-3 text-brand-navy/70 text-sm">Notes: {status.reviewer_notes}</div>}
            {status.submitted_at && <div className="mt-3 text-xs text-brand-navy/50">Submitted: {status.submitted_at}</div>}
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}
