/**
 * mobileBridge.js — thin wrapper around Capacitor native plugins.
 * Works on both native (Capacitor.isNativePlatform() === true) and web/PWA.
 * On web it falls back to browser APIs where possible.
 *
 * Install (see docs/MOBILE_BUILD.md for full instructions):
 *   yarn add @capacitor/core @capacitor/cli @capacitor/ios @capacitor/android
 *   yarn add @capacitor/camera @capacitor/push-notifications @capacitor/preferences
 *   yarn add @aparajita/capacitor-biometric-auth
 */

// Guarded imports so the web bundle doesn't crash if plugins are missing
const cap = (typeof window !== "undefined" && window.Capacitor) || null;
const isNative = () => !!(cap && cap.isNativePlatform && cap.isNativePlatform());

// ---------- Camera (Certifier site inspection) ----------
export async function takePicture() {
  if (isNative()) {
    try {
      const { Camera, CameraResultType, CameraSource } = await import("@capacitor/camera");
      const img = await Camera.getPhoto({
        quality: 80, allowEditing: false,
        resultType: CameraResultType.Base64,
        source: CameraSource.Camera,
      });
      return { data_b64: img.base64String, mime: `image/${img.format}` };
    } catch (e) {
      if (process.env.NODE_ENV !== "production") console.error("Native camera failed", e);
    }
  }
  // Web fallback → prompt file picker
  return new Promise((resolve) => {
    const input = document.createElement("input");
    input.type = "file"; input.accept = "image/*"; input.capture = "environment";
    input.onchange = () => {
      const file = input.files?.[0];
      if (!file) return resolve(null);
      const reader = new FileReader();
      reader.onload = () => resolve({
        data_b64: (reader.result || "").toString().split(",")[1],
        mime: file.type,
      });
      reader.readAsDataURL(file);
    };
    input.click();
  });
}

// ---------- Biometric login (Face ID / fingerprint) ----------
export async function biometricAvailable() {
  if (!isNative()) return false;
  try {
    const { BiometricAuth } = await import("@aparajita/capacitor-biometric-auth");
    const info = await BiometricAuth.checkBiometry();
    return !!info.isAvailable;
  } catch { return false; }
}

export async function biometricAuthenticate(reason = "Sign in to PMC Managers") {
  if (!isNative()) return { ok: false, reason: "native-only" };
  try {
    const { BiometricAuth } = await import("@aparajita/capacitor-biometric-auth");
    await BiometricAuth.authenticate({ reason });
    return { ok: true };
  } catch (e) {
    return { ok: false, reason: e?.message || "cancelled" };
  }
}

// Persist a JWT/refresh token securely on native, sessionStorage on web
export async function saveSecure(key, value) {
  if (isNative()) {
    const { Preferences } = await import("@capacitor/preferences");
    await Preferences.set({ key, value });
    return;
  }
  try { sessionStorage.setItem(key, value); }
  catch (err) {
    if (process.env.NODE_ENV !== "production") console.warn("saveSecure sessionStorage failed", err);
  }
}
export async function loadSecure(key) {
  if (isNative()) {
    const { Preferences } = await import("@capacitor/preferences");
    const r = await Preferences.get({ key });
    return r.value || null;
  }
  try { return sessionStorage.getItem(key); } catch { return null; }
}
export async function clearSecure(key) {
  if (isNative()) {
    const { Preferences } = await import("@capacitor/preferences");
    await Preferences.remove({ key });
    return;
  }
  try { sessionStorage.removeItem(key); }
  catch (err) {
    if (process.env.NODE_ENV !== "production") console.warn("clearSecure sessionStorage failed", err);
  }
}

// ---------- Push notifications ----------
export async function registerPush(onToken, onNotification) {
  if (!isNative()) {
    // Web push via service worker (production needs VAPID keys server-side)
    if ("serviceWorker" in navigator && "PushManager" in window) {
      try {
        const reg = await navigator.serviceWorker.ready;
        return { platform: "web", registration: reg };
      } catch (e) {
        if (process.env.NODE_ENV !== "production") console.warn("Web push register failed", e);
      }
    }
    return { platform: "none" };
  }
  const { PushNotifications } = await import("@capacitor/push-notifications");
  const perm = await PushNotifications.requestPermissions();
  if (perm.receive !== "granted") return { platform: "denied" };
  await PushNotifications.register();
  PushNotifications.addListener("registration", (t) => onToken && onToken(t.value));
  PushNotifications.addListener("pushNotificationReceived", (n) => onNotification && onNotification(n));
  return { platform: cap?.getPlatform?.() || "native" };
}

// ---------- Platform detection helper ----------
export function platform() {
  if (isNative()) return cap?.getPlatform?.() || "native";
  return "web";
}

export function isMobile() {
  if (typeof navigator === "undefined") return false;
  return /Android|iPhone|iPad|iPod/i.test(navigator.userAgent) || isNative();
}
