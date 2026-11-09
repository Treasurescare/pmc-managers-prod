import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { installPurchaseFreeGuard } from "@/lib/nativeBilling";

// iPhone/Android app only: push alerts, Face ID lock, native share, app settings.
const native = () => !!window.Capacitor?.isNativePlatform?.();
const SITE = "https://www.pmcmanagers.com";
// Plugin proxies must never be returned from a promise (they are treated as thenables).
const prefGet = async (key) => (await import("@capacitor/preferences")).Preferences.get({ key });
const prefSet = async (key, value) => (await import("@capacitor/preferences")).Preferences.set({ key, value });

async function enablePush(navigate, ask) {
  const { PushNotifications } = await import("@capacitor/push-notifications");
  const st = await (ask ? PushNotifications.requestPermissions() : PushNotifications.checkPermissions());
  if (st.receive !== "granted") return false;
  PushNotifications.removeAllListeners();
  PushNotifications.addListener("registration", (t) => { api.post("/api/v1/push/ios/register", { token: t.value }).catch(() => {}); });
  PushNotifications.addListener("pushNotificationReceived", (n) => toast(n.title || "PMC Managers", { description: n.body }));
  PushNotifications.addListener("pushNotificationActionPerformed", (a) => { const u = a.notification?.data?.url; if (u) navigate(u); });
  await PushNotifications.register();
  return true;
}

async function faceId() {
  const { BiometricAuth } = await import("@aparajita/capacitor-biometric-auth");
  try { await BiometricAuth.authenticate({ reason: "Unlock PMC Managers", allowDeviceCredential: true }); return true; } catch { return false; }
}

const LockScreen = ({ onOpen }) => (
  <div className="fixed inset-0 z-[100] flex flex-col items-center justify-center gap-6 bg-[#162921] text-white" data-testid="app-lock-screen">
    <img src="/pmc-logo-mark.png" alt="PMC Managers" className="w-20 h-20" />
    <div className="text-lg">PMC Managers is locked</div>
    <button className="pmc-btn pmc-btn--brass" onClick={onOpen} data-testid="app-unlock-btn">Unlock with Face ID</button>
  </div>);

const Settings = ({ lock, setLock, onPush, onClose }) => (
  <div className="fixed inset-0 z-[90] bg-black/50 flex items-end" onClick={onClose} data-testid="app-settings-sheet">
    <div className="w-full bg-white p-5 rounded-t-2xl space-y-4 text-[#162921]" onClick={(e) => e.stopPropagation()}>
      <div className="text-lg font-semibold">App settings</div>
      <label className="flex items-center justify-between"><span>Lock the app with Face ID</span>
        <input type="checkbox" checked={lock} onChange={(e) => setLock(e.target.checked)} data-testid="app-faceid-toggle" /></label>
      <button className="pmc-btn w-full" onClick={onPush} data-testid="app-push-enable-btn">Turn on new-tender alerts</button>
      <a href="/vendor/account#delete" className="block text-sm underline text-red-700" data-testid="app-delete-account-link">Delete my account</a>
      <button className="pmc-btn pmc-btn--ghost w-full" onClick={onClose} data-testid="app-settings-close">Close</button>
    </div>
  </div>);

export default function NativeFeatures() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [locked, setLocked] = useState(false);
  const [lock, setLockState] = useState(false);
  const [open, setOpen] = useState(false);
  const on = native();

  useEffect(() => {
    if (!on) return;
    installPurchaseFreeGuard();
    const signedOut = /^\/(login|signin)/.test(window.location.pathname);
    prefGet("pmc.faceid").then((r) => { if (r.value === "1") { setLockState(true); if (!signedOut) setLocked(true); } }).catch(() => {});
    let hiddenAt = 0;
    const vis = () => { if (document.hidden) hiddenAt = Date.now(); else if (hiddenAt && Date.now() - hiddenAt > 60000) prefGet("pmc.faceid").then((r) => { if (r.value === "1") setLocked(true); }).catch(() => {}); };
    document.addEventListener("visibilitychange", vis);
    return () => document.removeEventListener("visibilitychange", vis);
  }, [on]);

  useEffect(() => {
    if (on && pathname.startsWith("/vendor")) { enablePush(navigate, false).catch(() => {}); }
  }, [on, pathname, navigate]);

  if (!on) return null;
  const unlock = async () => { if (await faceId()) setLocked(false); };
  const setLock = async (v) => {
    if (v && !(await faceId())) return;
    setLockState(v); await prefSet("pmc.faceid", v ? "1" : "0");
    toast.success(v ? "Face ID lock is on" : "Face ID lock is off");
  };
  const onPush = async () => {
    if (!pathname.startsWith("/vendor")) { toast("Sign in as a supplier first, then turn on alerts"); return; }
    const ok = await enablePush(navigate, true);
    if (ok) toast.success("New-tender alerts are on"); else toast.error("Allow notifications for PMC Managers in iPhone Settings");
  };
  const share = async () => { const { Share } = await import("@capacitor/share"); Share.share({ title: document.title, url: SITE + pathname }).catch(() => {}); };
  return (
    <>
      {locked && <LockScreen onOpen={unlock} />}
      {open && <Settings lock={lock} setLock={setLock} onPush={onPush} onClose={() => setOpen(false)} />}
      <div className="fixed z-[60] flex flex-col gap-2" style={{ left: 12, bottom: 70 }}>
        <button aria-label="Share this page" onClick={share} className="w-11 h-11 rounded-full bg-[#162921] text-[#d9bd72] shadow" data-testid="app-share-btn">⇪</button>
        <button aria-label="App settings" onClick={() => setOpen(true)} className="w-11 h-11 rounded-full bg-[#162921] text-[#d9bd72] shadow" data-testid="app-settings-btn">⚙</button>
      </div>
    </>);
}
