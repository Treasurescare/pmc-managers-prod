import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { api, vendorInviteApi, kycApi, formatApiError, showApiError} from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import BulkInviteModal from "./BulkInviteModal";
import { InfoDot } from "@/components/InfoDot";

function KpiTile({ label, value }) {
  return (
    <div className="border border-brand-navy/10 bg-white p-4">
      <div className="pmc-label">{label}</div>
      <div className="pmc-stat-lg mt-1 text-brand-navy">{value ?? "—"}</div>
    </div>
  );
}

export default function VendorsPanel() {
  const { t } = useI18n();
  const [vendors, setVendors] = useState([]);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState(null);
  const [kpi, setKpi] = useState(null);
  const [loadingKpi, setLoadingKpi] = useState(false);
  const [showInvite, setShowInvite] = useState(false);
  const [showBulk, setShowBulk] = useState(false);
  const [sendingInvite, setSendingInvite] = useState(false);  // Bug #5 — prevent double-submit + dead-button feel
  const [statusFilter, setStatusFilter] = useState("all");  // V-02 fix
  const [inviteDraft, setInviteDraft] = useState({ email: "", company_name: "", country: "KZ", contact_name: "" });
  const [templateMeta, setTemplateMeta] = useState({ available: false });
  // v44 — highlight a specific vendor_ref after activation/creation so the
  // admin visually locates the row instead of feeling like it "disappeared".
  const [highlightRef, setHighlightRef] = useState(null);
  const [activatingRef, setActivatingRef] = useState(null);
  const [kycBusy, setKycBusy] = useState(false);
  const rowRefs = useRef({});

  const runKycAuto = async (v) => {
    if (kycBusy) return;
    setKycBusy(true);
    try {
      const r = await kycApi.start(v.vendor_ref, "basic");
      toast.success(`KYC ${r.status || "run"} · risk ${r.risk_score ?? "—"}/100`);
      load();
    } catch (e) { showApiError(e); } finally { setKycBusy(false); }
  };
  const setKycManual = async (v, decision) => {
    if (kycBusy) return;
    let notes = null;
    if (decision === "rejected") {
      notes = window.prompt("Reason for rejection (recorded in audit log):", "");
      if (notes === null) return;
    }
    setKycBusy(true);
    try {
      await kycApi.manual(v.vendor_ref, decision, notes);
      toast.success(`KYC marked ${decision}`);
      setSelected({ ...v, kyc_status: decision });
      load();
    } catch (e) { showApiError(e); } finally { setKycBusy(false); }
  };

  const load = useCallback((focusRef) => {
    api.get("/api/v1/vendors", { params: search ? { search } : {} })
      .then((r) => {
        setVendors(r.data || []);
        if (focusRef) {
          setHighlightRef(focusRef);
          // Wait one paint for the row to mount, then scroll to it.
          setTimeout(() => {
            const el = rowRefs.current[focusRef];
            if (el && typeof el.scrollIntoView === "function") {
              el.scrollIntoView({ behavior: "smooth", block: "center" });
            }
          }, 60);
          // Clear the highlight after 3.5s.
          setTimeout(() => setHighlightRef((cur) => (cur === focusRef ? null : cur)), 3500);
        }
      })
      .catch((e) => showApiError(e));
  }, [search]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    vendorInviteApi.templateMeta().then(setTemplateMeta).catch(() => {});
  }, []);

  useEffect(() => {
    if (!selected) { setKpi(null); return; }
    setLoadingKpi(true);
    api.get(`/api/v1/vendors/${selected.vendor_ref}/kpi`)
      .then((r) => setKpi(r.data))
      .catch((e) => showApiError(e))
      .finally(() => setLoadingKpi(false));
  }, [selected]);

  const sendInvite = async () => {
    // Bug #5 — email validation before request; give tester an actionable
    // message instead of a silent no-op that felt like a "dead button".
    if (!inviteDraft.email || !inviteDraft.email.trim()) {
      return toast.error("Vendor email is required");
    }
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(inviteDraft.email.trim())) {
      return toast.error("Enter a valid email address");
    }
    if (sendingInvite) return;   // prevent double-click while in-flight
    setSendingInvite(true);
    try {
      const r = await vendorInviteApi.invite({ ...inviteDraft, email: inviteDraft.email.trim() });
      toast.success(`Invited ${r.email} · ${r.vendor_ref}`, {
        description: "Verification email sent. Row is highlighted below.",
      });
      setShowInvite(false);
      setInviteDraft({ email: "", company_name: "", country: "KZ", contact_name: "" });
      setStatusFilter("all");  // ensure the just-invited pending vendor is visible
      load(r.vendor_ref);
    } catch (e) { showApiError(e); }
    finally { setSendingInvite(false); }
  };

  // v44 — inline one-click activation for an inactive vendor.
  // Default action: resend magic link. Uses window.confirm to give the admin
  // one chance to switch to "force activate with a password".
  const activateVendor = async (v) => {
    if (activatingRef) return;  // guard double-clicks
    const forcePwd = window.confirm(
      `Resend verify email to ${v.email}?\n\n` +
      `Press OK to RESEND the magic link.\n` +
      `Press Cancel to set a password yourself and activate immediately.`
    );
    let payload = { mode: "resend_link" };
    if (!forcePwd) {
      const pwd = window.prompt(
        `Set an initial password for ${v.email} (min 8 chars).\n` +
        `Vendor will be forced to change it on first sign-in.`
      );
      if (!pwd) return;  // admin bailed
      if (pwd.length < 8) {
        toast.error("Password must be at least 8 characters");
        return;
      }
      payload = { mode: "set_password", password: pwd };
    }
    setActivatingRef(v.vendor_ref);
    try {
      const r = await vendorInviteApi.activate(v.vendor_ref, payload);
      if (r.mode === "resend_link") {
        toast.success(`Verify link resent to ${r.email}`, {
          description: `Vendor ref ${r.vendor_ref} · row highlighted below`,
        });
      } else {
        toast.success(`Activated ${r.email}`, {
          description: `Vendor ref ${r.vendor_ref} can now sign in`,
        });
      }
      // The activated vendor no longer matches "pending"/"inactive" filters —
      // reset to "all" so the row stays visible instead of appearing to vanish.
      setStatusFilter("all");
      load(v.vendor_ref);
    } catch (e) { showApiError(e); }
    finally { setActivatingRef(null); }
  };

  const uploadTemplate = async (f) => {
    if (!f) return;
    try {
      const r = await vendorInviteApi.uploadTemplate(f);
      // Bug #74 — backend response was previously stringified straight into
      // the toast, which showed "Template uploaded · undefined" if the
      // response shape changed. Now we fall back to the file's own name.
      const fname = r?.file_name || f.name || "template";
      const size = r?.size_bytes ?? f.size ?? 0;
      toast.success(`Registration template uploaded · ${fname}`, {
        description: size ? `${(size / 1024).toFixed(1)} KB · vendors can now download this exact file` : undefined,
      });
      setTemplateMeta({ available: true, file_name: fname, size_bytes: size });
    } catch (e) {
      // Surface the real backend detail (413 too large, 400 wrong extension, etc.)
      showApiError(e);
    }
  };

  return (
    <div className="space-y-4" data-testid="admin-vendors-panel">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="text-sm text-brand-navy/70">
          {vendors.length} {t("panels.vendors.count_hint_suffix")}
        </div>
        <div className="flex gap-2 items-center">
          <label className="text-xs cursor-pointer border border-brand-navy/20 px-3 py-1.5 uppercase tracking-widest text-brand-navy hover:bg-brand-navy/5"
                 data-testid="vendor-template-upload-label">
            {templateMeta.available ? t("panels.vendors.replace_template") : t("panels.vendors.upload_template")}
            <input type="file" accept=".pdf,.docx,.doc" onChange={(e) => uploadTemplate(e.target.files?.[0])}
                   className="hidden" data-testid="vendor-template-upload" />
          </label>
          {templateMeta.available && (
            <a href={vendorInviteApi.templateDownloadUrl()} target="_blank" rel="noreferrer"
               className="text-xs underline text-brand-navy/70"
               data-testid="vendor-template-download">{t("panels.vendors.download_template_prefix")} ({templateMeta.file_name})</a>
          )}
          <button onClick={() => setShowBulk(true)} data-testid="vendor-bulk-invite-open"
                  className="px-4 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5">
            {t("panels.vendors.bulk_invite")}
          </button>
          <a href="/admin/vendors/new" data-testid="vendor-fullform-open"
             className="px-4 py-2 text-[11px] uppercase tracking-widest border border-brand-navy-soft text-brand-navy-soft hover:bg-brand-navy-soft hover:text-white">
            {t("panels.vendors.add_fullform")}
          </a>
          <button onClick={() => setShowInvite(!showInvite)}
                  data-testid="vendor-invite-toggle"
                  className="px-5 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
            {showInvite ? t("panels.vendors.invite_toggle_close") : t("panels.vendors.invite_toggle_open")}
          </button>
        </div>
      </div>

      <BulkInviteModal open={showBulk} onClose={() => setShowBulk(false)} onDone={load} />

      {showInvite && (
        <div className="border border-brand-navy-soft/40 bg-white p-6 grid gap-3 md:grid-cols-4"
             data-testid="vendor-invite-form">
          <label className="md:col-span-2 text-sm">
            <span className="pmc-label">{t("panels.vendors.invite_email")}<InfoDot tip="Verification email is sent to this address. The vendor sets their own password via the magic-link inside." /></span>
            <input value={inviteDraft.email} type="email" required
                   onChange={(e) => setInviteDraft({ ...inviteDraft, email: e.target.value })}
                   data-testid="vendor-invite-email"
                   className="mt-1 w-full px-3 py-2 border border-brand-navy/20" />
          </label>
          <label className="md:col-span-2 text-sm">
            <span className="pmc-label">{t("panels.vendors.invite_company")}<InfoDot tip="Legal entity name. Editable by the vendor during their own registration flow." /></span>
            <input value={inviteDraft.company_name}
                   onChange={(e) => setInviteDraft({ ...inviteDraft, company_name: e.target.value })}
                   data-testid="vendor-invite-company"
                   className="mt-1 w-full px-3 py-2 border border-brand-navy/20" />
          </label>
          <label className="text-sm">
            <span className="pmc-label">{t("panels.vendors.invite_contact")}<InfoDot tip="Primary point of contact at the vendor. Optional." /></span>
            <input value={inviteDraft.contact_name}
                   onChange={(e) => setInviteDraft({ ...inviteDraft, contact_name: e.target.value })}
                   className="mt-1 w-full px-3 py-2 border border-brand-navy/20" />
          </label>
          <label className="text-sm">
            <span className="pmc-label">{t("panels.vendors.invite_country")}<InfoDot tip="ISO-2 country code. Drives KYC provider selection and country-specific required documents." /></span>
            <input value={inviteDraft.country}
                   onChange={(e) => setInviteDraft({ ...inviteDraft, country: e.target.value })}
                   className="mt-1 w-full px-3 py-2 border border-brand-navy/20" />
          </label>
          <div className="md:col-span-4 text-[11px] text-brand-navy/50">
            {t("panels.vendors.invite_hint")}
          </div>
          <div className="md:col-span-4 flex justify-end">
            <button type="button" onClick={sendInvite}
                    disabled={sendingInvite}
                    data-testid="vendor-invite-submit"
                    className="px-8 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90 disabled:opacity-50 disabled:cursor-not-allowed">
              {sendingInvite ? t("panels.vendors.invite_sending") : t("panels.vendors.invite_submit")}
            </button>
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[5fr_7fr]">
        <div>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t("panels.vendors.search_placeholder")}
            data-testid="vendor-search"
            className="w-full px-4 py-2 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white text-sm mb-3"
          />
          {/* V-02 fix — filter dropdown: all / pending-verify / active / inactive */}
          <div className="flex gap-2 items-center mb-3 text-xs text-brand-navy/70" data-testid="vendor-status-filter-bar">
            <span className="pmc-label">{t("panels.vendors.filter_status")}</span>
            {[
              ["all", t("panels.vendors.filter_all")],
              ["pending", t("panels.vendors.filter_pending")],
              ["active", t("panels.vendors.filter_active")],
              ["inactive", t("panels.vendors.filter_inactive")],
            ].map(([k, l]) => (
              <button key={k} type="button" onClick={() => setStatusFilter(k)}
                data-testid={`vendor-status-filter-${k}`}
                className={`px-3 py-1 border text-[11px] uppercase tracking-widest ${statusFilter === k ? "bg-brand-navy text-white border-brand-navy" : "border-brand-navy/20 text-brand-navy/70 hover:border-brand-navy"}`}>
                {l}
              </button>
            ))}
          </div>
          <div className="border border-brand-navy/10 bg-white">
            {vendors.length === 0 && (
              <div className="p-6 text-brand-navy/50 text-sm">
                {t("panels.vendors.empty")}
              </div>
            )}
            {vendors
              .filter((v) => {
                if (statusFilter === "pending") return v.email_verified === false;
                if (statusFilter === "active") return v.email_verified !== false && v.is_active !== false;
                if (statusFilter === "inactive") return v.is_active === false;
                return true;
              })
              .map((v) => {
                const isInactive = v.is_active === false || v.email_verified === false;
                const isHighlighted = highlightRef === v.vendor_ref;
                return (
                  <div
                    key={v.id}
                    ref={(el) => { rowRefs.current[v.vendor_ref] = el; }}
                    data-testid={`vendor-row-${v.vendor_ref}`}
                    className={
                      "w-full p-4 border-b border-brand-navy/10 transition-colors duration-500 " +
                      (isHighlighted
                        ? "bg-emerald-100/80 ring-2 ring-emerald-400 "
                        : selected?.id === v.id
                          ? "bg-brand-navy/5 "
                          : "hover:bg-brand-navy/5 ")
                    }
                  >
                    <button
                      type="button"
                      onClick={() => setSelected(v)}
                      className="text-left w-full"
                      data-testid={`vendor-row-select-${v.vendor_ref}`}
                    >
                      <div className="text-sm font-semibold text-brand-navy">{v.company_name || "(no name)"}</div>
                      <div className="text-xs font-mono text-brand-navy-soft mt-1">{v.vendor_ref}</div>
                      <div className="text-xs text-brand-navy/50 mt-0.5">
                        {v.email} · {v.country}
                        {v.email_verified === false && <span className="ml-2 text-amber-600">· {t("panels.vendors.pending_verify")}</span>}
                        {v.is_active === false && v.email_verified !== false && <span className="ml-2 text-slate-500">· {t("panels.vendors.inactive_badge")}</span>}
                      </div>
                    </button>
                    {isInactive && (
                      <div className="mt-3">
                        <button
                          type="button"
                          onClick={() => activateVendor(v)}
                          disabled={activatingRef === v.vendor_ref}
                          data-testid={`vendor-activate-${v.vendor_ref}`}
                          className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-widest bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {activatingRef === v.vendor_ref
                            ? t("panels.vendors.activating")
                            : t("panels.vendors.activate_row")}
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
          </div>
        </div>

        <div>
          {!selected ? (
            <div className="border border-dashed border-brand-navy/20 bg-white p-14 text-center text-brand-navy/50">
              {t("panels.vendors.kpi_placeholder")}
            </div>
          ) : loadingKpi || !kpi ? (
            <div className="border border-brand-navy/10 bg-white p-14 text-center text-brand-navy/50">{t("panels.vendors.kpi_loading")}</div>
          ) : (
            <div className="border border-brand-navy/10 bg-white p-6" data-testid="vendor-kpi">
              <div className="pmc-label">{t("panels.vendors.kpi_kicker")}</div>
              <h3 className="font-display text-2xl text-brand-navy mt-1">{kpi.company_name || "(no name)"}</h3>
              <div className="text-sm font-mono text-brand-navy-soft mt-1">{kpi.vendor_ref}</div>
              <div className="text-xs text-brand-navy/50 mt-0.5">{kpi.email} · {kpi.country} · {kpi.primary_sector || "sector n/a"}</div>
              <div className="mt-6 grid gap-3 md:grid-cols-4">
                <KpiTile label={t("panels.vendors.kpi_days_approved")} value={kpi.approved_days_ago} />
                <KpiTile label={t("panels.vendors.kpi_review_hours")} value={kpi.time_to_decision_hours} />
                <KpiTile label={t("panels.vendors.kpi_kz_licenses")} value={kpi.kz_licenses_count} />
                <KpiTile label={t("panels.vendors.kpi_categories")} value={kpi.categories_count} />
              </div>
              {/* KYC controls — admin can trigger provider run OR override manually.
                  Vendor bids are blocked until kyc_status ∈ {verified, cleared, passed}. */}
              <div className="mt-6 border border-brand-navy/10 bg-brand-pale/40 p-4" data-testid="vendor-kyc-controls">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="pmc-label">KYC verification</div>
                    <div className="text-sm text-brand-navy mt-1">
                      Current status:{" "}
                      <strong data-testid="vendor-kyc-status" className={
                        (kpi.kyc_status === "verified" || kpi.kyc_status === "cleared" || kpi.kyc_status === "passed")
                          ? "text-emerald-700"
                          : kpi.kyc_status === "rejected" ? "text-red-600"
                          : "text-amber-700"
                      }>
                        {kpi.kyc_status || selected.kyc_status || "not run"}
                      </strong>
                      {kpi.kyc_score != null && <span className="ml-2 text-xs text-brand-navy/60">risk {kpi.kyc_score}/100</span>}
                    </div>
                  </div>
                  <InfoDot tip="Admin can trigger the automated KYC provider run OR override the decision manually. Vendors cannot submit bids until this reads verified / cleared / passed." />
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button type="button" onClick={() => runKycAuto(selected)} disabled={kycBusy}
                    data-testid="vendor-kyc-run"
                    className="px-3 py-1.5 text-[11px] uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-navy hover:text-white disabled:opacity-50">
                    {kycBusy ? "Working…" : "Run KYC provider"}
                  </button>
                  <button type="button" onClick={() => setKycManual(selected, "verified")} disabled={kycBusy}
                    data-testid="vendor-kyc-verify"
                    className="px-3 py-1.5 text-[11px] uppercase tracking-widest bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50">
                    Mark verified
                  </button>
                  <button type="button" onClick={() => setKycManual(selected, "pending")} disabled={kycBusy}
                    data-testid="vendor-kyc-pending"
                    className="px-3 py-1.5 text-[11px] uppercase tracking-widest border border-amber-500/60 text-amber-700 hover:bg-amber-50 disabled:opacity-50">
                    Mark pending
                  </button>
                  <button type="button" onClick={() => setKycManual(selected, "rejected")} disabled={kycBusy}
                    data-testid="vendor-kyc-reject"
                    className="px-3 py-1.5 text-[11px] uppercase tracking-widest border border-red-500/60 text-red-600 hover:bg-red-50 disabled:opacity-50">
                    Mark rejected
                  </button>
                </div>
              </div>
              <div className="mt-6 grid gap-4 md:grid-cols-2 text-sm">
                <div>
                  <div className="pmc-label">{t("panels.vendors.kpi_kz_held")}</div>
                  {(kpi.kz_licenses_held || []).length === 0
                    ? <div className="text-brand-navy/50 mt-1">{t("panels.vendors.kpi_none")}</div>
                    : (<ul className="mt-1 text-brand-navy">
                        {kpi.kz_licenses_held.map((l) => <li key={l}>· {l}</li>)}</ul>)}
                </div>
                <div>
                  <div className="pmc-label">{t("panels.vendors.kpi_regions")}</div>
                  {(kpi.operating_regions || []).length === 0
                    ? <div className="text-brand-navy/50 mt-1">{t("panels.vendors.kpi_regions_none")}</div>
                    : <div className="mt-1 text-brand-navy">{kpi.operating_regions.join(", ")}</div>}
                </div>
                <div className="md:col-span-2">
                  <div className="pmc-label">{t("panels.vendors.kpi_business_cats")}</div>
                  {(kpi.categories_declared || []).length === 0
                    ? <div className="text-brand-navy/50 mt-1">{t("panels.vendors.kpi_none")}</div>
                    : <div className="mt-1 text-brand-navy">{kpi.categories_declared.join(" · ")}</div>}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
