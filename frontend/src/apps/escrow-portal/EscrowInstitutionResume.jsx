import { useParams, useSearchParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { api, showApiError } from "@/lib/api";

/**
 * EscrowInstitutionResume — magic-link resume page for escrow institutions
 * (banks/trustees) returning to finish a draft registration. v51al.
 */
export default function EscrowInstitutionResume() {
  const { token } = useParams();
  const [params] = useSearchParams();
  const iid = params.get("iid");
  const [doc, setDoc] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!token) return;
    api.get(`/api/v1/escrow-institutions/resume/${token}`)
      .then((r) => setDoc(r.data))
      .catch((e) => {
        setErr(e?.response?.data?.detail || "Could not resume this registration");
        showApiError(e);
      });
  }, [token]);

  if (err) {
    return (
      <div className="max-w-xl mx-auto p-10 text-center" data-testid="escrow-resume-error">
        <h1 className="text-xl font-semibold text-red-800">Link invalid</h1>
        <p className="text-sm text-slate-600 mt-2">{err}</p>
      </div>
    );
  }
  if (!doc) return <div className="p-8 text-brand-navy/50">Loading…</div>;

  return (
    <div className="max-w-3xl mx-auto p-6" data-testid="escrow-resume-page">
      <h1 className="text-2xl font-semibold text-brand-navy">
        {doc.legal_name || "Escrow Institution"}
      </h1>
      <div className="mt-2 text-xs uppercase tracking-widest text-brand-navy/60">
        Status · {doc.status}
      </div>
      <div className="mt-6 bg-white border border-brand-navy/15 p-6 text-sm">
        <p>
          Your registration is <strong>{doc.status}</strong>. {doc.reviewer_notes && (
            <>Reviewer notes: <em>{doc.reviewer_notes}</em></>
          )}
        </p>
        {doc.status === "approved" && (
          <a href={`/escrow/dashboard/${iid || doc.id}?token=${token}`}
             data-testid="escrow-resume-dashboard-cta"
             className="inline-block mt-4 px-5 py-2 text-xs uppercase tracking-widest bg-brand-navy text-white">
            Open your dashboard
          </a>
        )}
      </div>
    </div>
  );
}
