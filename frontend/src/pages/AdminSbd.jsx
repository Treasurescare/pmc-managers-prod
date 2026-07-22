import { useEffect, useState } from "react";
import { toast } from "sonner";
import { BookOpen, Upload, Trash2, Download } from "lucide-react";
import DashboardLayout from "@/components/app/DashboardLayout";
import api, { formatApiError } from "@/lib/api";

const DOC_TYPES = [
  { value: "tender", label: "Tender" },
  { value: "rfp", label: "RFP" },
  { value: "rfq", label: "RFQ" },
];

function readAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(r.result);
    r.onerror = reject;
    r.readAsDataURL(file);
  });
}

export default function AdminSbd() {
  const [templates, setTemplates] = useState([]);
  const [form, setForm] = useState({ name: "", document_type: "rfp", category: "", description: "" });
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try { const { data } = await api.get("/sbd/templates"); setTemplates(data); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const upload = async (e) => {
    e.preventDefault();
    if (!file) { toast.error("Attach a template file (.docx / .pdf)"); return; }
    setBusy(true);
    try {
      const data = await readAsDataUrl(file);
      await api.post("/sbd/templates", {
        ...form,
        file: { name: file.name, mime: file.type, size: file.size, data },
      });
      toast.success("Template published to library");
      setForm({ name: "", document_type: "rfp", category: "", description: "" });
      setFile(null);
      load();
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  const archive = async (tid) => {
    if (!window.confirm("Archive this template? It will hide from buyers going forward.")) return;
    try { await api.delete(`/sbd/templates/${tid}`); toast.success("Archived"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <DashboardLayout title="SBD Template Library" subtitle="Standard Bidding Documents that buyers can attach to any tender in one click">
      <div className="grid lg:grid-cols-[400px_1fr] gap-8">
        <form onSubmit={upload} className="border p-5 space-y-4 bg-white" data-testid="sbd-form">
          <div className="pmc-label flex items-center gap-2"><Upload className="h-3 w-3" /> Publish new template</div>
          <div>
            <label className="pmc-label block mb-1 text-xs">Template name</label>
            <input required data-testid="sbd-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="e.g. KZ Construction RFP v3.2"
              className="w-full h-10 px-3 border border-input focus:border-primary focus:outline-none" />
          </div>
          <div>
            <label className="pmc-label block mb-1 text-xs">Document type</label>
            <select data-testid="sbd-doctype" value={form.document_type} onChange={(e) => setForm({ ...form, document_type: e.target.value })}
              className="w-full h-10 px-3 border border-input bg-white">
              {DOC_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
          <div>
            <label className="pmc-label block mb-1 text-xs">Category (optional)</label>
            <input data-testid="sbd-category" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}
              placeholder="e.g. Construction & Civil Works"
              className="w-full h-10 px-3 border border-input focus:border-primary focus:outline-none" />
          </div>
          <div>
            <label className="pmc-label block mb-1 text-xs">Description</label>
            <textarea data-testid="sbd-description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
              rows={3} placeholder="Short description of what this template covers"
              className="w-full px-3 py-2 border border-input focus:border-primary focus:outline-none" />
          </div>
          <div>
            <label className="pmc-label block mb-1 text-xs">File (.docx, .pdf)</label>
            <input required data-testid="sbd-file" type="file" accept=".docx,.pdf,.doc"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="w-full text-sm" />
            {file && <div className="text-xs text-muted-foreground mt-1">{file.name} · {(file.size / 1024).toFixed(1)} KB</div>}
          </div>
          <button data-testid="sbd-publish-btn" disabled={busy} className="text-sm bg-primary text-white px-4 py-2 hover:-translate-y-0.5 transition-transform disabled:opacity-60">
            {busy ? "Uploading..." : "Publish template"}
          </button>
        </form>

        <div>
          <div className="pmc-label mb-3 flex items-center gap-2"><BookOpen className="h-3 w-3" /> Library · {templates.length} template{templates.length !== 1 ? "s" : ""}</div>
          <div className="border" data-testid="sbd-list">
            {templates.length === 0 ? (
              <div className="p-8 text-center text-sm text-muted-foreground">No templates yet. Publish your first Standard Bidding Document above.</div>
            ) : (
              <ul>
                {templates.map((t) => (
                  <li key={t.id} className="border-b p-4 flex items-start gap-4" data-testid={`sbd-item-${t.id}`}>
                    <div className="flex-1 min-w-0">
                      <div className="font-serif text-lg">{t.name}</div>
                      <div className="pmc-label text-primary text-xs mt-1">
                        {t.document_type?.toUpperCase()}{t.category ? ` · ${t.category}` : ""}
                      </div>
                      {t.description && <div className="text-sm text-muted-foreground mt-1 line-clamp-2">{t.description}</div>}
                      <div className="text-xs text-muted-foreground mt-2 font-mono">
                        {t.file?.name} · {t.file?.size ? `${(t.file.size / 1024).toFixed(1)} KB` : ""} · by {t.created_by_name} · {new Date(t.created_at).toLocaleDateString()}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      {t.file?.data && (
                        <a href={t.file.data} download={t.file.name} title="Download"
                          className="text-muted-foreground hover:text-foreground p-2"><Download className="h-4 w-4" /></a>
                      )}
                      <button onClick={() => archive(t.id)} data-testid={`sbd-archive-${t.id}`}
                        className="text-destructive p-2 hover:bg-destructive/10"><Trash2 className="h-4 w-4" /></button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
