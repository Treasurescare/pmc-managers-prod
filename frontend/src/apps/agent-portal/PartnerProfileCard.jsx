import { useEffect, useState } from "react";
import { toast } from "sonner";
import { agentApi, showApiError } from "@/lib/api";

const BASE = process.env.REACT_APP_BACKEND_URL;

export default function PartnerProfileCard() {
  const [p, setP] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = () => agentApi.publicProfile().then((x) => setP({ bio: "", show: false, ...x })).catch(showApiError);
  useEffect(() => { load(); }, []);
  if (!p) return null;
  const save = () => { setBusy(true); agentApi.savePublicProfile({ bio: p.bio || "", show: !!p.show }).then(() => toast.success("Profile card saved")).catch(showApiError).finally(() => setBusy(false)); };
  const upload = (f) => { if (!f) return; setBusy(true); agentApi.uploadPublicPhoto(f).then(() => { toast.success("Photo uploaded"); load(); }).catch(showApiError).finally(() => setBusy(false)); };
  return (
    <div className="bg-white border border-brand-navy/15 p-4 space-y-3" data-testid="partner-profile-card">
      <div className="font-semibold">Homepage profile card</div>
      <p className="text-xs text-brand-navy/60">If you win a badge, PMC's homepage can show your photo, name and a short bio in "Partners of the month". It's off until you switch it on.</p>
      <div className="flex gap-4 items-start flex-wrap">
        <div className="w-24 h-24 border border-brand-navy/15 bg-brand-pale flex items-center justify-center overflow-hidden" data-testid="partner-photo-preview">
          {p.photo_url ? <img src={`${BASE}${p.photo_url}`} alt="Your profile" className="w-full h-full object-cover" /> : <span className="text-xs text-brand-navy/50">No photo</span>}
        </div>
        <div className="flex-1 min-w-[240px] space-y-2">
          <label className="text-sm block">Photo (JPG, PNG or WebP, under 2 MB)<input type="file" accept="image/jpeg,image/png,image/webp" className="block mt-1 text-sm" disabled={busy} onChange={(e) => upload(e.target.files?.[0])} data-testid="partner-photo-input" /></label>
          <label className="text-sm block">Short bio ({280 - (p.bio || "").length} characters left)
            <textarea rows={3} maxLength={280} className="mt-1 block w-full px-3 py-2 border border-brand-navy/20 text-sm" value={p.bio || ""} onChange={(e) => setP({ ...p, bio: e.target.value })} data-testid="partner-bio-input" /></label>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={!!p.show} onChange={(e) => setP({ ...p, show: e.target.checked })} data-testid="partner-show-public" />Show my photo, name and bio on the PMC homepage when I win a badge</label>
          {p.hidden && <div className="text-xs text-red-700" data-testid="partner-profile-hidden">PMC has hidden your card from the homepage. Contact PMC for details.</div>}
          <button type="button" className="pmc-btn pmc-btn--primary" disabled={busy} onClick={save} data-testid="partner-profile-save">Save profile card</button>
        </div>
      </div>
    </div>
  );
}
