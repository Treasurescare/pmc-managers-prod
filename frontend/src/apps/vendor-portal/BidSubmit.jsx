import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { publicApi, vendorApi, bidApi, paymentApi, uploadsApi, formatApiError } from "@/lib/api";

export default function BidSubmit() {
  const { noticeRef } = useParams();
  const nav = useNavigate();
  const [vendor, setVendor] = useState(null);
  const [notice, setNotice] = useState(null);
  const [price, setPrice] = useState("");
  const [technical, setTechnical] = useState("");
  const [commercial, setCommercial] = useState("");
  const [docs, setDocs] = useState([]); // {kind, key, filename, size_bytes, uploaded_at}
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [v, n] = await Promise.all([vendorApi.me(), publicApi.getNotice(noticeRef)]);
        if (v.must_change_password) return nav("/vendor/change-password");
        setVendor(v); setNotice(n);
      } catch {
        nav("/vendor/login");
      }
    })();
  }, [noticeRef, nav]);

  const uploadFile = async (kind, file) => {
    try {
      const p = await uploadsApi.presign(file.name, file.type || "application/pdf", "bid-docs", file.size);
      const r = await uploadsApi.direct(p.key, file);
      setDocs((d) => [...d, {
        kind, key: r.key, filename: file.name,
        size_bytes: r.size_bytes, uploaded_at: new Date().toISOString(),
      }]);
      toast.success(`Uploaded ${file.name}`);
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const removeDoc = (idx) => setDocs((d) => d.filter((_, i) => i !== idx));

  const submit = async (e) => {
    e.preventDefault();
    if (!price || Number(price) <= 0) return toast.error("Enter a valid bid price");
    setBusy(true);
    try {
      const bid = await bidApi.create({
        notice_ref: noticeRef,
        price_amount: Number(price),
        price_currency: notice.budget_currency || "USD",
        technical_notes: technical, commercial_notes: commercial,
        documents: docs,
      });
      toast.success(`Bid ${bid.bid_ref} submitted`);
      // If EMD due, immediately go to Stripe
      if ((bid.emd_due_amount || 0) > 0) {
        const chk = await paymentApi.checkout(bid.id, window.location.origin);
        window.location.href = chk.checkout_url;
      } else {
        nav("/vendor");
      }
    } catch (err) {
      toast.error(formatApiError(err));
      setBusy(false);
    }
  };

  if (!vendor || !notice) return <div className="p-10 text-slate-500">Loading…</div>;

  const emdConfig = notice.emd_config || { fixed_amount: 0, percentage: 0, currency: notice.budget_currency };
  const emdDue = (emdConfig.fixed_amount || 0) + ((emdConfig.percentage || 0) / 100) * (notice.budget_amount || 0);

  return (
    <div className="min-h-screen bg-slate-50 py-10" data-testid="bid-submit-page">
      <div className="max-w-3xl mx-auto px-6">
        <button onClick={() => nav("/vendor")} className="text-xs text-slate-500 hover:underline">← Back</button>
        <h1 className="text-3xl font-serif mt-2">Submit a bid</h1>
        <div className="text-sm text-slate-500">{notice.notice_ref}</div>

        <div className="bg-white border rounded-lg p-5 mt-5">
          <div className="text-xs text-slate-500 uppercase tracking-wider">Tender</div>
          <div className="font-serif text-lg mt-1">{notice.title}</div>
          <div className="text-sm text-slate-600 mt-2">{notice.description}</div>
          <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
            <div>Category: <strong>{notice.category}</strong></div>
            <div>Budget: <strong>{notice.budget_currency} {(notice.budget_amount || 0).toLocaleString()}</strong></div>
            <div>Deadline: <strong>{(notice.submission_deadline || "").slice(0, 10)}</strong></div>
            <div className="text-amber-700 font-semibold">
              EMD due on submit: {emdConfig.currency} {emdDue.toLocaleString()}
            </div>
          </div>
        </div>

        <form onSubmit={submit} className="bg-white border rounded-lg p-5 mt-5 space-y-5" data-testid="bid-form">
          <label className="block text-sm">
            <span>Your bid price ({notice.budget_currency})</span>
            <input type="number" required min="1" step="0.01" value={price}
              onChange={(e) => setPrice(e.target.value)}
              className="mt-1 w-full border rounded-md px-3 py-2 text-sm" data-testid="bid-price" />
          </label>

          <label className="block text-sm">
            <span>Technical proposal notes</span>
            <textarea value={technical} onChange={(e) => setTechnical(e.target.value)}
              rows={3} className="mt-1 w-full border rounded-md px-3 py-2 text-sm"
              placeholder="Approach, methodology, key personnel…"
              data-testid="bid-technical" />
          </label>

          <label className="block text-sm">
            <span>Commercial proposal notes</span>
            <textarea value={commercial} onChange={(e) => setCommercial(e.target.value)}
              rows={3} className="mt-1 w-full border rounded-md px-3 py-2 text-sm"
              placeholder="Break-up, milestones, payment terms…"
              data-testid="bid-commercial" />
          </label>

          <div className="space-y-2">
            <div className="text-sm font-semibold">Supporting documents</div>
            <div className="grid grid-cols-3 gap-2 text-xs">
              {[["technical", "Technical PDF"], ["commercial", "Commercial PDF"], ["supporting", "Other doc"]].map(([k, label]) => (
                <label key={k} className="border rounded-md p-3 text-center cursor-pointer hover:bg-slate-50"
                  data-testid={`bid-upload-${k}`}>
                  <input type="file" accept="application/pdf,image/*" hidden
                    onChange={(e) => e.target.files?.[0] && uploadFile(k, e.target.files[0])} />
                  <span className="block text-slate-700 font-medium">{label}</span>
                  <span className="block text-slate-400 mt-1">Click to upload</span>
                </label>
              ))}
            </div>
            {docs.length > 0 && (
              <div className="mt-2 text-xs space-y-1">
                {docs.map((d, i) => (
                  <div key={i} className="flex justify-between bg-slate-50 px-2 py-1 rounded">
                    <span>{d.kind}: {d.filename} ({Math.round((d.size_bytes || 0) / 1024)} KB)</span>
                    <button type="button" onClick={() => removeDoc(i)}
                      className="text-red-600 hover:underline">Remove</button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <button type="submit" disabled={busy}
            className="w-full bg-slate-900 text-white rounded-md py-3 text-sm hover:bg-slate-800 disabled:opacity-60"
            data-testid="bid-submit-btn">
            {busy ? "Submitting…" : (emdDue > 0 ? `Submit & pay EMD (${emdConfig.currency} ${emdDue.toLocaleString()})` : "Submit bid")}
          </button>
        </form>
      </div>
    </div>
  );
}
