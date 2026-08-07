import { useEffect, useState } from "react";
import { toast } from "sonner";
import { mfaApi, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";

export default function MFASetupModal({ open, onClose }) {
  const { t } = useI18n();
  const [status, setStatus] = useState(null);
  const [enrolment, setEnrolment] = useState(null);
  const [otp, setOtp] = useState("");
  const [recovery, setRecovery] = useState(null);

  useEffect(() => {
    if (!open) return;
    mfaApi.status().then(setStatus).catch(() => {});
  }, [open]);

  const start = async () => {
    try { setEnrolment(await mfaApi.enroll()); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const verify = async () => {
    try {
      const r = await mfaApi.verify(otp);
      setRecovery(r.recovery_codes);
      toast.success(t("panels.mfa.enabled_toast"));
      setStatus({ enabled: true, pending_enrolment: false });
    } catch (e) { toast.error(formatApiError(e)); }
  };
  const disable = async () => {
    try {
      await mfaApi.disable(otp);
      toast.success(t("panels.mfa.disabled_toast"));
      setStatus({ enabled: false, pending_enrolment: false });
      setEnrolment(null); setOtp(""); setRecovery(null);
    } catch (e) { toast.error(formatApiError(e)); }
  };

  if (!open) return null;
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50" data-testid="mfa-modal">
      <div className="bg-white rounded-lg p-6 max-w-md w-full space-y-4">
        <div className="flex justify-between items-start">
          <div>
            <h2 className="text-lg font-serif">{t("panels.mfa.title")}</h2>
            <div className="text-xs text-slate-500">{t("panels.mfa.subtitle")}</div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700" data-testid="mfa-close">×</button>
        </div>

        {status?.enabled && !recovery && (
          <>
            <div className="text-sm bg-emerald-50 border border-emerald-200 p-3">
              {t("panels.mfa.enabled_msg_prefix")} <strong>{t("panels.mfa.enabled_word")}</strong> {t("panels.mfa.enabled_msg_suffix")}
            </div>
            <div className="text-sm">
              {t("panels.mfa.disable_prompt")}
              <input value={otp} onChange={(e) => setOtp(e.target.value)}
                className="mt-1 w-full border px-3 py-2 text-center font-mono tracking-widest"
                data-testid="mfa-disable-otp" />
              <button onClick={disable} data-testid="mfa-disable-btn"
                className="mt-2 w-full bg-red-600 text-white py-2 text-sm">{t("panels.mfa.disable_btn")}</button>
            </div>
          </>
        )}

        {!status?.enabled && !enrolment && (
          <>
            <p className="text-sm text-slate-600">
              {t("panels.mfa.start_hint")}
            </p>
            <button onClick={start} data-testid="mfa-start"
              className="w-full bg-slate-900 text-white py-2 text-sm">{t("panels.mfa.start_btn")}</button>
          </>
        )}

        {enrolment && !recovery && (
          <>
            <div className="text-sm text-slate-600">{t("panels.mfa.scan_qr")}</div>
            <img src={`data:image/png;base64,${enrolment.qr_png_base64}`}
                 alt="TOTP QR" className="mx-auto w-56 h-56 border" data-testid="mfa-qr" />
            <div className="text-xs text-slate-500 font-mono break-all bg-slate-50 p-2 border">
              {t("panels.mfa.manual_entry")} {enrolment.secret}
            </div>
            <label className="block text-sm">
              <span>{t("panels.mfa.enter_code")}</span>
              <input value={otp} onChange={(e) => setOtp(e.target.value)}
                autoFocus inputMode="numeric" maxLength={8}
                className="mt-1 w-full border px-3 py-2 text-center font-mono tracking-widest"
                data-testid="mfa-verify-otp" />
            </label>
            <button onClick={verify} data-testid="mfa-verify-btn"
              className="w-full bg-slate-900 text-white py-2 text-sm">{t("panels.mfa.enable_btn")}</button>
          </>
        )}

        {recovery && (
          <>
            <div className="text-sm bg-amber-50 border border-amber-200 p-3">
              {t("panels.mfa.recovery_warning")}
            </div>
            <pre className="bg-slate-50 border p-3 text-xs font-mono grid grid-cols-2 gap-1"
                 data-testid="mfa-recovery-codes">
              {recovery.map((c) => <div key={c}>{c}</div>)}
            </pre>
            <button onClick={onClose} className="w-full bg-slate-900 text-white py-2 text-sm">
              {t("panels.mfa.done")}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
