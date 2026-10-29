import { useEffect, useState, useCallback } from "react";
import { useUiTheme } from "@/context/UiThemeContext";
import { toast } from "sonner";
import { tenderTemplateApi, showApiError } from "@/lib/api";
import AdminShellE from "./AdminShellE";
import AdminAvatarMenu from "./AdminAvatarMenu";

const TABS = [["submitted", "Awaiting review"], ["changes_requested", "Changes requested"], ["approved", "Published"], ["rejected", "Rejected"]];

const tt = (t) => (t.header || {});

export default function AdminTenderReviewE() {
  const { isE } = useUiTheme();
  const [tab, setTab] = useState("submitted");
  const [rows, setRows] = useState([]);
  const load = useCallback(() => tenderTemplateApi.reviewQueue(tab).then((r) => setRows(r.items || [])).catch(() => {}), [tab]);
  useEffect(() => { load(); }, [load]);

  if (!isE) return null;

  const act = async (fn, label) => { try { await fn(); toast.success(label); load(); } catch (e) { showApiError(e); } };
  const approve = (id) => act(() => tenderTemplateApi.reviewApprove(id, ""), "Approved & published");
  const changes = (id) => { const n = window.prompt("What changes are needed?"); if (n) act(() => tenderTemplateApi.reviewRequestChanges(id, n), "Sent back for changes"); };
  const reject = (id) => { const n = window.prompt("Reason for rejection:"); if (n) act(() => tenderTemplateApi.reviewReject(id, n), "Rejected"); };

  return (
    <div data-testid="admin-tender-review" data-pmc-e-page="admin-tender-review">
      <AdminShellE active="Tender review" header={<>
        <div className="crumb">Procurement / <b>Vendor tender review</b></div>
        <label className="pmc-search"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Search tenders, bids, vendors, ledger events…" /><span className="pmc-kbd">Ctrl K</span></label>
        <div className="pmc-atop__r">
          <button className="pmc-btn pmc-btn--secondary" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> Help</button>
          <AdminAvatarMenu />
        </div>
      </>}>
        <h1 className="pmc-display" style={{ fontSize: "28px", margin: "0 0 4px" }}>Vendor tender review</h1>
        <p className="pmc-muted" style={{ fontSize: "14px", marginBottom: "16px" }}>Full tenders prepared by vendors in the PMC builder. Only an active Reviewer can approve, send back, or reject. Approving publishes the tender for bidding and keeps the originating vendor as author.</p>
        <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginBottom: "18px", borderBottom: "1px solid var(--line)", paddingBottom: "8px" }}>
          {TABS.map(([k, label]) => <button key={k} className={"pmc-btn pmc-btn--sm " + (tab === k ? "pmc-btn--primary" : "pmc-btn--ghost")} data-testid={`tr-tab-${k}`} onClick={() => setTab(k)}>{label}</button>)}
        </div>
        {rows.length === 0 ? <div className="pmc-muted" data-testid="tr-empty">Nothing here.</div> : (
          <div style={{ display: "grid", gap: "10px" }} data-testid="tr-list">
            {rows.map((t) => (
              <div key={t.id} className="pmc-panel" style={{ padding: "14px 16px" }} data-testid={`tr-row-${t.id}`}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: "12px" }}>
                  <div>
                    <div style={{ fontWeight: 600 }}>{tt(t).work_title || t.name} {t.published_notice_ref && <span className="pmc-muted" style={{ fontWeight: 400, fontSize: "12px" }}>· {t.published_notice_ref}</span>}</div>
                    <div className="pmc-muted" style={{ fontSize: "12px", marginTop: "2px" }}>Author: {t.owner_company_name || "Vendor"} · {tt(t).product_category || "—"} · {t.country || tt(t).location || "—"} · {tt(t).budget_currency || ""} {tt(t).budget_amount ?? tt(t).tender_value ?? "—"} · closes {String(tt(t).sub_end || "").slice(0, 16).replace("T", " ") || "—"}</div>
                    <div style={{ fontSize: "13px", marginTop: "6px", maxWidth: "640px" }}>{tt(t).work_description || ""}</div>
                    {t.review_note && <div style={{ fontSize: "12px", color: "var(--ink-muted)", marginTop: "4px" }}>Last note: {t.review_note}</div>}
                  </div>
                  {tab === "submitted" && (
                    <div style={{ display: "flex", flexDirection: "column", gap: "6px", flex: "none" }}>
                      <button className="pmc-btn pmc-btn--sm pmc-btn--primary" data-testid={`tr-approve-${t.id}`} onClick={() => approve(t.id)}>Approve &amp; publish</button>
                      <button className="pmc-btn pmc-btn--sm pmc-btn--secondary" data-testid={`tr-changes-${t.id}`} onClick={() => changes(t.id)}>Request changes</button>
                      <button className="pmc-btn pmc-btn--sm pmc-btn--ghost" style={{ color: "var(--danger)" }} data-testid={`tr-reject-${t.id}`} onClick={() => reject(t.id)}>Reject</button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </AdminShellE>
    </div>
  );
}
