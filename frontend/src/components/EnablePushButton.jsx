/**
 * Small navy-and-gold button to enable/disable Web Push. Shown wherever the
 * vendor/admin sits (dashboard header). Hidden when unsupported or when the
 * browser is Safari-in-tab (must be installed PWA on iOS).
 */
import { useWebPush, pushSupported, isStandalonePwa } from "@/lib/push";
import { toast } from "sonner";
import { useEffect, useRef } from "react";

export default function EnablePushButton({ role = "vendor", userRef = null, compact = false }) {
  const { supported, permission, subscribed, working, error, enable, disable } =
    useWebPush({ role, userRef });
  const lastErr = useRef(null);
  useEffect(() => {
    if (error && error !== lastErr.current) {
      lastErr.current = error;
      toast.error(`Push: ${error}`);
    }
    if (!error) lastErr.current = null;
  }, [error]);

  if (!supported) return null;

  const isIos = /iphone|ipad|ipod/i.test(navigator.userAgent);
  if (isIos && !isStandalonePwa()) {
    return (
      <span className="text-[11px] text-brand-navy/60 border border-brand-navy/20 px-2 py-1"
            data-testid="push-ios-hint">
        Install to home screen to enable alerts
      </span>
    );
  }

  const cls = "text-[11px] uppercase tracking-widest font-semibold px-3 py-2 border " +
              (subscribed
                ? "bg-brand-navy text-brand-gold border-brand-gold hover:bg-brand-navy/80"
                : "bg-white text-brand-navy border-brand-navy/40 hover:border-brand-gold hover:text-brand-navy");

  return (
    <button type="button"
            data-testid={subscribed ? "disable-push" : "enable-push"}
            className={cls}
            disabled={working || permission === "denied"}
            onClick={subscribed ? disable : enable}
            title={permission === "denied"
              ? "Notifications are blocked in your browser settings"
              : subscribed ? "Disable notifications" : "Enable award / corrigenda / deadline alerts"}>
      {compact ? (subscribed ? "🔔 On" : "🔕 Off")
               : (working ? "…" : subscribed ? "Notifications on" : "Enable alerts")}
    </button>
  );
}
