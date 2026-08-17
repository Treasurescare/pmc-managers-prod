import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { adminApi, tenantApi, formatApiError } from "@/lib/api";

/**
 * BrandingPanel — admin can pick a tenant and upload / remove its portal logo.
 * The logo replaces the default PMC "P" mark in the top-left of the portal
 * for every user whose active tenant matches.
 */
export default function BrandingPanel() {
  const [tenants, setTenants] = useState([]);
  const [selected, setSelected] = useState("");
  const [selectedLogo, setSelectedLogo] = useState("");
  const [busy, setBusy] = useState(false);
  const fileRef = useRef(null);

  const load = async () => {
    try {
      const rows = await tenantApi.list();
      setTenants(rows || []);
      if (rows?.length && !selected) {
        setSelected(rows[0].id);
        setSelectedLogo(rows[0].logo_data_url || "");
      }
    } catch (err) { toast.error(formatApiError(err)); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);

  useEffect(() => {
    const t = tenants.find((x) => x.id === selected);
    setSelectedLogo(t?.logo_data_url || "");
  }, [selected, tenants]);

  const pick = () => fileRef.current?.click();

  const onFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!/^image\/(png|jpe?g|webp)$/.test(file.type))
      return toast.error("Please pick a PNG, JPG or WEBP image.");
    const dataUrl = await resizeSquare(file, 256);
    if (!dataUrl) return toast.error("Could not read image.");
    if (dataUrl.length > 340 * 1024) return toast.error("Image still too large.");
    setSelectedLogo(dataUrl);
  };

  const save = async () => {
    if (!selected) return toast.error("Pick a tenant first.");
    if (!selectedLogo) return toast.error("Pick a logo first.");
    setBusy(true);
    try {
      await adminApi.uploadTenantLogo(selected, selectedLogo);
      toast.success("Portal logo updated.");
      await load();
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  const remove = async () => {
    if (!selected) return;
    setBusy(true);
    try {
      await adminApi.removeTenantLogo(selected);
      setSelectedLogo("");
      toast.success("Portal logo removed.");
      await load();
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  return (
    <div data-testid="branding-panel" className="max-w-2xl space-y-6">
      <div>
        <div className="pmc-label">Portal branding</div>
        <h2 className="font-display text-2xl text-brand-navy">Tenant logo</h2>
        <p className="text-sm text-brand-navy/60 mt-1">
          The logo replaces the default PMC “P” mark in the top-left corner
          for every user whose active tenant matches. Square PNG or JPG works
          best. Under 350 KB after encoding.
        </p>
      </div>

      <label className="block text-sm">
        <span className="pmc-label">Tenant</span>
        <select value={selected} onChange={(e) => setSelected(e.target.value)}
                data-testid="branding-tenant-select"
                className="mt-1 w-full px-4 py-3 border border-brand-navy/20 text-brand-navy bg-white">
          {tenants.map((t) => (
            <option key={t.id} value={t.id}>{t.name} · {t.code}</option>
          ))}
        </select>
      </label>

      <div className="flex items-center gap-5">
        <div className="w-24 h-24 border border-brand-navy/10 bg-brand-pale flex items-center justify-center overflow-hidden">
          {selectedLogo
            ? <img src={selectedLogo} alt="Logo" className="w-full h-full object-contain"
                   data-testid="branding-preview" />
            : <span className="text-brand-navy/40 text-xs">no logo</span>}
        </div>
        <div className="flex-1 space-y-2">
          <input type="file" hidden ref={fileRef}
                 accept="image/png,image/jpeg,image/webp"
                 data-testid="branding-file"
                 onChange={onFile} />
          <button onClick={pick} data-testid="branding-pick"
                  className="px-4 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
            Pick logo
          </button>
          {selectedLogo && (
            <button onClick={remove} disabled={busy}
                    data-testid="branding-remove"
                    className="ml-2 px-4 py-2 text-[11px] font-semibold uppercase tracking-widest border border-red-500 text-red-600 hover:bg-red-50 disabled:opacity-50">
              Remove
            </button>
          )}
        </div>
      </div>

      <div className="pt-4 border-t border-brand-navy/10 flex justify-end">
        <button onClick={save} disabled={busy || !selectedLogo}
                data-testid="branding-save"
                className="px-6 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-50">
          {busy ? "Saving…" : "Save logo"}
        </button>
      </div>
    </div>
  );
}

async function resizeSquare(file, size) {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement("canvas");
        canvas.width = size; canvas.height = size;
        const ctx = canvas.getContext("2d");
        const s = Math.min(img.width, img.height);
        const sx = (img.width - s) / 2;
        const sy = (img.height - s) / 2;
        ctx.drawImage(img, sx, sy, s, s, 0, 0, size, size);
        resolve(canvas.toDataURL("image/png"));
      };
      img.onerror = () => resolve(null);
      img.src = reader.result;
    };
    reader.onerror = () => resolve(null);
    reader.readAsDataURL(file);
  });
}
