import { Link } from "react-router-dom";

export default function PmcLogo({ variant = "light" }) {
  const isDark = variant === "dark";
  return (
    <Link to="/" data-testid="pmc-logo-link" className="inline-flex items-center gap-3 group">
      <span
        className={`inline-flex h-9 w-9 items-center justify-center border ${
          isDark ? "border-white/30 bg-white/10 text-white" : "border-foreground bg-primary text-primary-foreground"
        }`}
      >
        <span className="font-serif text-xl leading-none">P</span>
      </span>
      <span className="flex flex-col leading-none">
        <span className={`font-serif text-lg tracking-tight ${isDark ? "text-white" : "text-foreground"}`}>PMC Managers</span>
        <span className={`pmc-label mt-1 ${isDark ? "text-white/60" : ""}`}>Global Tender Board</span>
      </span>
    </Link>
  );
}
