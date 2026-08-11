/**
 * Final activation step for the admin's new-vendor form.
 * Chooses between immediate activation (admin sets initial password) or
 * sending a verification email so the vendor sets their own password.
 * Split out from AdminVendorCreate.jsx for maintainability.
 */
export default function VendorActivationStep({
  t, mode, setMode, password, setPassword, saving, onSubmit,
}) {
  return (
    <div className="space-y-6" data-testid="admin-vendor-final">
      <div>
        <div className="pmc-label">{t("admin_vendor.activation_mode")}</div>
        <div className="mt-2 grid gap-3 md:grid-cols-2">
          <label
            className={
              "border p-4 cursor-pointer " +
              (mode === "activate"
                ? "border-brand-navy bg-brand-navy/5"
                : "border-brand-navy/20 bg-white")
            }
          >
            <input
              type="radio"
              checked={mode === "activate"}
              onChange={() => setMode("activate")}
              data-testid="admin-vendor-mode-activate"
              className="mr-2"
            />
            <strong>{t("admin_vendor.activate_now")}</strong>
            <div className="text-xs text-brand-navy/60 mt-1">
              {t("admin_vendor.activate_now_hint")}
            </div>
          </label>
          <label
            className={
              "border p-4 cursor-pointer " +
              (mode === "verify"
                ? "border-brand-navy bg-brand-navy/5"
                : "border-brand-navy/20 bg-white")
            }
          >
            <input
              type="radio"
              checked={mode === "verify"}
              onChange={() => setMode("verify")}
              data-testid="admin-vendor-mode-verify"
              className="mr-2"
            />
            <strong>{t("admin_vendor.verify_mail")}</strong>
            <div className="text-xs text-brand-navy/60 mt-1">
              {t("admin_vendor.verify_mail_hint")}
            </div>
          </label>
        </div>
      </div>

      {mode === "activate" && (
        <label className="block text-sm">
          <span className="pmc-label">{t("admin_vendor.initial_pwd")}</span>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            data-testid="admin-vendor-password"
            className="mt-1 w-full px-4 py-3 border border-brand-navy/20"
          />
        </label>
      )}

      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={onSubmit}
          disabled={saving}
          data-testid="admin-vendor-submit"
          className="px-8 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-50"
        >
          {saving
            ? t("admin_vendor.saving")
            : mode === "activate"
              ? t("admin_vendor.save_activate")
              : t("admin_vendor.save_verify")}
        </button>
      </div>
    </div>
  );
}
