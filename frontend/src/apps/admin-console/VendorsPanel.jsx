import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { api, vendorInviteApi, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import BulkInviteModal from "./BulkInviteModal";

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

  const load = useCallback(() => {
    api.get("/api/v1/vendors", { params: search ? { search } : {} })
      .then((r) => setVendors(r.data || []))
      .catch((e) => toast.error(formatApiError(e)));
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
      .catch((e) => toast.error(formatApiError(e)))
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
        description: "Verification email sent. Vendor can also open the link from the audit log.",
      });
      setShowInvite(false);
      setInviteDraft({ email: "", company_name: "", country: "KZ", contact_name: "" });
      load();
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setSendingInvite(false); }
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
      toast.error(formatApiError(e));
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
            <span className="pmc-label">{t("panels.vendors.invite_email")}</span>
            <input value={inviteDraft.email} type="email" required
                   onChange={(e) => setInviteDraft({ ...inviteDraft, email: e.target.value })}
                   data-testid="vendor-invite-email"
                   className="mt-1 w-full px-3 py-2 border border-brand-navy/20" />
          </label>
          <label className="md:col-span-2 text-sm">
            <span className="pmc-label">{t("panels.vendors.invite_company")}</span>
            <input value={inviteDraft.company_name}
                   onChange={(e) => setInviteDraft({ ...inviteDraft, company_name: e.target.value })}
                   data-testid="vendor-invite-company"
                   className="mt-1 w-full px-3 py-2 border border-brand-navy/20" />
          </label>
          <label className="text-sm">
            <span className="pmc-label">{t("panels.vendors.invite_contact")}</span>
            <input value={inviteDraft.contact_name}
                   onChange={(e) => setInviteDraft({ ...inviteDraft, contact_name: e.target.value })}
                   className="mt-1 w-full px-3 py-2 border border-brand-navy/20" />
          </label>
          <label className="text-sm">
            <span className="pmc-label">{t("panels.vendors.invite_country")}</span>
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
              .map((v) => (
              <button
                key={v.id}
                type="button"
                onClick={() => setSelected(v)}
                data-testid={`vendor-row-${v.vendor_ref}`}
                className={"w-full text-left p-4 border-b border-brand-navy/10 hover:bg-brand-navy/5 " + (selected?.id === v.id ? "bg-brand-navy/5" : "")}
              >
                <div className="text-sm font-semibold text-brand-navy">{v.company_name || "(no name)"}</div>
                <div className="text-xs font-mono text-brand-navy-soft mt-1">{v.vendor_ref}</div>
                <div className="text-xs text-brand-navy/50 mt-0.5">
                  {v.email} · {v.country}
                  {v.email_verified === false && <span className="ml-2 text-amber-600">· {t("panels.vendors.pending_verify")}</span>}
                  {v.is_active === false && v.email_verified !== false && <span className="ml-2 text-slate-500">· {t("panels.vendors.inactive_badge")}</span>}
                </div>
              </button>
            ))}
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
