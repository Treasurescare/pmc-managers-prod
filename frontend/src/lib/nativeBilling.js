// iPhone/Android app is purchase-free (App Store 3.1.3(f)): no buy buttons, no checkout calls.
export const isNativeApp = () => !!window.Capacitor?.isNativePlatform?.();
export const NATIVE_BILLING_MSG = "Billing for this feature is managed by your organisation's PMC account.";

export const isPaymentRequest = (method, url = "", data = null) =>
  !["get", "head", "options"].includes((method || "get").toLowerCase()) &&
  (/\/checkout(\/|\?|$)|fee-checkout|\/pay(\/|\?|$)|\/payments\/sandbox\//i.test(url) || !!(data && typeof data === "object" && data.pay_now));

const ID_RE = /(^|[-_])(pay|paynow|buy|purchase|checkout|subscribe|upgrade|feature)([-_]|$)/i;
const TEXT_RE = /\b(pay|buy|purchase|checkout|subscribe|upgrade|get featured|go premium)\b|(₹|\$|€|£)\s?\d/i;
const CUR_RE = /\b(INR|USD|EUR|GBP|AED|SGD|MYR|KZT|CNY|JPY|KRW|IDR)\s?\d/;
const SAFE_RE = /alert|newsletter|notif|status|history|receipt|refresh/i;

const isCta = (el) => {
  const id = el.getAttribute("data-testid") || "";
  const text = `${el.textContent || ""} ${el.getAttribute("aria-label") || ""}`.trim();
  if (ID_RE.test(id) && !SAFE_RE.test(id)) return true;
  return text.length < 60 && (TEXT_RE.test(text) || CUR_RE.test(text)) && !SAFE_RE.test(text);
};

export function installPurchaseFreeGuard() {
  if (!isNativeApp() || window.__pmcIapGuard) return;
  window.__pmcIapGuard = true;
  document.documentElement.classList.add("pmc-native");
  const style = document.createElement("style");
  style.textContent = "[data-pmc-iap-hidden]{display:none!important}";
  document.head.appendChild(style);
  let queued = false;
  const scan = () => {
    queued = false;
    document.querySelectorAll("button, a, [role=button], [data-sonner-toast] button").forEach((el) => {
      if (isCta(el)) el.setAttribute("data-pmc-iap-hidden", "");
      else el.removeAttribute("data-pmc-iap-hidden");
    });
  };
  new MutationObserver(() => { if (!queued) { queued = true; requestAnimationFrame(scan); } })
    .observe(document.body, { childList: true, subtree: true, characterData: true });
  scan();
}
