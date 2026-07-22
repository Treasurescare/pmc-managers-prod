import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";
import { toast } from "sonner";
import PmcLogo from "@/components/app/PmcLogo";
import { ArrowRight } from "lucide-react";

export default function ChooseRole() {
  const navigate = useNavigate();
  const [role, setRole] = useState("vendor");
  const [pending, setPending] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const raw = sessionStorage.getItem("pmc_google_pending");
    if (!raw) { navigate("/login"); return; }
    setPending(JSON.parse(raw));
  }, [navigate]);

  const submit = async () => {
    if (!pending) return;
    setBusy(true);
    try {
      const { data } = await api.post("/auth/google-callback", { session_id: pending.session_id, role });
      sessionStorage.removeItem("pmc_google_pending");
      toast.success(`Welcome, ${data.name}`);
      window.location.href = role === "vendor" ? "/vendor/profile" : role === "buyer" ? "/buyer" : "/admin";
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-6">
      <div className="max-w-lg w-full border bg-white p-10">
        <PmcLogo />
        <div className="pmc-label mt-8 mb-2">Complete sign-up</div>
        <h1 className="font-serif text-3xl">Choose how you'll use PMC</h1>
        <p className="text-sm text-muted-foreground mt-2">
          Signing in as <span className="font-mono">{pending?.email}</span>. Select your account type — this cannot be changed later.
        </p>

        <div className="grid grid-cols-2 gap-0 border mt-8">
          {[
            { id: "vendor", label: "Vendor", body: "I want to bid on tenders" },
            { id: "buyer", label: "Buyer", body: "I want to publish tenders" },
          ].map((r) => (
            <button
              key={r.id} type="button" data-testid={`role-${r.id}`} onClick={() => setRole(r.id)}
              className={`p-6 text-left border-r last:border-r-0 transition-colors ${
                role === r.id ? "bg-primary text-white" : "hover:bg-muted/40"
              }`}
            >
              <div className="font-serif text-xl">{r.label}</div>
              <div className={`text-sm mt-1 ${role === r.id ? "text-white/80" : "text-muted-foreground"}`}>{r.body}</div>
            </button>
          ))}
        </div>

        <button data-testid="role-continue" onClick={submit} disabled={busy}
          className="mt-8 w-full h-12 bg-foreground text-white text-sm inline-flex items-center justify-center gap-2 hover:-translate-y-0.5 transition-transform disabled:opacity-60">
          {busy ? "Continuing..." : "Continue"} {!busy && <ArrowRight className="h-4 w-4" />}
        </button>
      </div>
    </div>
  );
}
