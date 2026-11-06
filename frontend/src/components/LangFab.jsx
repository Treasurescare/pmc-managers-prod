import { useEffect, useState } from "react";
import LangSwitcher from "@/apps/shared/LangSwitcher";

// Shows a floating language button on any screen whose header has no visible language switcher (mobile, login, help, some admin pages).
export default function LangFab() {
  const [show, setShow] = useState(false);
  useEffect(() => {
    const check = () => {
      const vis = [...document.querySelectorAll('[data-testid="lang-toggle"]')]
        .some((el) => !el.closest("[data-lang-fab]") && el.offsetParent !== null && el.getBoundingClientRect().width > 0);
      setShow(!vis);
    };
    check();
    const id = setInterval(check, 1200);
    window.addEventListener("resize", check);
    return () => { clearInterval(id); window.removeEventListener("resize", check); };
  }, []);
  if (!show) return null;
  return (
    <div data-lang-fab="" data-testid="lang-fab" style={{ position: "fixed", left: 16, bottom: 16, zIndex: 70, background: "#fff", boxShadow: "0 8px 24px rgba(0,0,0,.18)" }}>
      <div style={{ position: "relative" }}><LangSwitcher up /></div>
    </div>);
}
