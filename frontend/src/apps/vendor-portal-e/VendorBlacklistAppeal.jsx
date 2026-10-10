import { useEffect, useState } from "react";
import { toast } from "sonner";
import { vendorIntelApi, showApiError } from "@/lib/api";
import EvidenceManager from "@/components/EvidenceManager";

/**
 * v51bd — When the signed-in vendor is on the blacklist, this panel
 * surfaces the admin's reason + lets the vendor file an appeal with
 * supporting evidence (upload document OR take a photo on mobile).
 *
 * Rendered inline at the top of VendorHomeE and VendorMyBidsE so a
 * blacklisted vendor cannot miss it.
 */
export default function VendorBlacklistAppeal({ compact = false }) {
  const [state, setState] = useState(null); // null = loading, {} = details
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => {
    vendorIntelApi.myBlacklist()
      .then(setState)
      .catch(() => setState({ blacklisted: false }));
  };
  useEffect(() => { load(); }, []);

  const submit = async () => {
    if (!message.trim()) return toast.error("Write a short explanation first");
    setBusy(true);
    try {
      await vendorIntelApi.submitAppeal({ message: message.trim() });
      toast.success("Appeal submitted. PMC admin will review it shortly.");
      setMessage("");
      load();
    } catch (e) { showApiError(e, { fallbackTitle: "Could not submit appeal" }); }
    finally { setBusy(false); }
  };

  const addEvidence = async (entry) => {
    try { await vendorIntelApi.addAppealEvidence(entry); load(); }
    catch (e) { showApiError(e, { fallbackTitle: "Could not attach evidence" }); throw e; }
  };
  const deleteEvidence = async (idx) => {
    if (!window.confirm("Delete this attachment from your appeal?")) return;
    try { await vendorIntelApi.deleteAppealEvidence(idx); load(); }
    catch (e) { showApiError(e, { fallbackTitle: "Could not delete evidence" }); }
  };

  if (!state || !state.blacklisted) return null;
  const latestAppeal = (state.appeals || []).slice(-1)[0];
  const evidence = latestAppeal?.evidence || [];

  return (
    <div className="pmc-callout pmc-callout--warn" data-testid="vendor-blacklist-appeal"
         style={{ margin: "0 0 20px", padding: 18, display: "block",
                  borderColor: "#B91C1C", background: "#FEF2F2", color: "#7F1D1D" }}>
      <div className="pmc-eyebrow" style={{ color: "#991B1B", marginBottom: 6 }}>
        Account suspended
      </div>
      <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>
        Your account is currently on the blacklist.
      </div>
      <div style={{ fontSize: 13, lineHeight: "20px", marginBottom: 10 }}>
        <strong>Reason:</strong> {state.reason || "—"}
        {state.at && <span style={{ marginLeft: 8, opacity: 0.75 }}>
          · {(state.at || "").slice(0, 19).replace("T", " ")}
        </span>}
      </div>
      {!compact && (
        <>
          <div style={{ marginTop: 8 }}>
            <label className="text-[11px] uppercase tracking-widest text-red-900 font-semibold block mb-1">
              Submit an appeal
            </label>
            <textarea rows={3} value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Explain the issue, cite remediation steps, mention attached evidence…"
              data-testid="vendor-appeal-message"
              style={{ width: "100%", padding: "8px 10px",
                       border: "1px solid #FCA5A5", background: "#FFFFFF",
                       color: "#0F172A", fontSize: 14 }} />
            <button type="button" onClick={submit} disabled={busy}
              data-testid="vendor-appeal-submit"
              className="pmc-btn pmc-btn--primary"
              style={{ marginTop: 8 }}>
              {busy ? "Sending…" : "Submit appeal"}
            </button>
          </div>
          <div style={{ marginTop: 14 }}>
            <EvidenceManager
              title="Appeal evidence (document or photo)"
              items={evidence}
              onAdd={addEvidence}
              onDelete={deleteEvidence}
              scope="blacklist-appeal"
              testIdPrefix="vendor-appeal-ev"
            />
          </div>
          {(state.appeals || []).length > 1 && (
            <div style={{ marginTop: 10, fontSize: 12, opacity: 0.75 }}>
              {(state.appeals || []).length} appeals on file.
            </div>
          )}
        </>
      )}
    </div>
  );
}
