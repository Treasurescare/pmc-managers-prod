import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { publicApi, vendorApi, bidApi, paymentApi, uploadsApi, corrigendaApi, sandboxPayApi, formatApiError, showApiError, BACKEND_URL } from "@/lib/api";

const GATEWAYS = [
  { id: "stripe", label: "Stripe", note: "Card · Live sandbox" },
  { id: "paypal", label: "PayPal", note: "Sandbox demo" },
  { id: "kaspi",  label: "Kaspi Pay", note: "KZ · Sandbox demo" },
];

export default function BidSubmit() {
  const { noticeRef } = useParams();
  const nav = useNavigate();
  const [vendor, setVendor] = useState(null);
  const [notice, setNotice] = useState(null);
  const [price, setPrice] = useState("");
  const [technical, setTechnical] = useState("");
  const [commercial, setCommercial] = useState("");
  const [docs, setDocs] = useState([]);
  const [gateway, setGateway] = useState("stripe");
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState(null);
  // v52bh — corrigenda acknowledgement: backend blocks submission (412)
  // until every active corrigendum is acknowledged by this vendor.
  const [corrigenda, setCorrigenda] = useState([]);
  const [ackingId, setAckingId] = useState(null);
  // v52bj — captured from a 409 so we can offer a direct "open / withdraw"
  // path without the vendor having to hunt through My Bids.
  const [existingDup, setExistingDup] = useState(null);
  // v52cz rev2 — bundle picker selection. Default: every doc is checked so
  // the natural click flow matches "Download all". Keyed by upload key so
  // the set survives Remove / Re-upload.
  const [selectedKeys, setSelectedKeys] = useState(() => new Set());

  // v51bd — local draft so vendors can save work and come back later.
  // (persisted BOTH to localStorage AND to the backend via bidApi.saveDraft
  // so the vendor can resume on another device.)
  const draftKey = `pmc-bid-draft:${noticeRef}`;

  useEffect(() => {
    (async () => {
      try {
        const [v, n] = await Promise.all([vendorApi.me(), publicApi.getNotice(noticeRef)]);
        if (v.must_change_password) return nav("/vendor/change-password");
        setVendor(v); setNotice(n);
        // Load any published corrigenda so the vendor can acknowledge them
        // inline before submitting (412 gate on the backend).
        try {
          const cs = await corrigendaApi.listPublic(noticeRef);
          setCorrigenda(Array.isArray(cs) ? cs : (cs?.items || []));
        } catch { /* corrigenda are optional */ }
        // Prefer the server-side draft (cross-device) and fall back to local.
        let restored = null;
        try {
          const srv = await bidApi.getDraft(noticeRef);
          if (srv?.found) restored = srv;
        } catch { /* draft is optional */ }
        if (!restored) {
          try {
            const raw = localStorage.getItem(draftKey);
            if (raw) restored = JSON.parse(raw);
          } catch { /* ignore corrupt draft */ }
        }
        if (restored) {
          if (restored.price_amount != null) setPrice(String(restored.price_amount));
          else if (restored.price != null) setPrice(String(restored.price));
          if (restored.technical_notes != null) setTechnical(restored.technical_notes);
          else if (restored.technical) setTechnical(restored.technical);
          if (restored.commercial_notes != null) setCommercial(restored.commercial_notes);
          else if (restored.commercial) setCommercial(restored.commercial);
          if (Array.isArray(restored.documents)) setDocs(restored.documents);
          else if (Array.isArray(restored.docs)) setDocs(restored.docs);
        }
      } catch {
        nav("/vendor/login");
      }
    })();
  }, [noticeRef, nav, draftKey]);

  const uploadFile = async (kind, file, inputEl) => {
    try {
      // v52cy — enforce allowed file-type list on client. Backend already
      // caps size + sniffs magic bytes; this prevents a misleading UX where
      // the user picks an unsupported file and only sees failure after
      // upload. Allowed: pdf, doc(x), xls(x), ppt(x), jpg/jpeg, png, dwg.
      const ALLOWED_EXT = /\.(pdf|docx?|xlsx?|pptx?|jpe?g|png|dwg)$/i;
      if (!ALLOWED_EXT.test(file.name)) {
        if (inputEl) inputEl.value = "";
        toast.error(`"${file.name}" is not allowed — pick a PDF, DOC/DOCX, XLS/XLSX, PPT/PPTX, JPG/PNG or DWG file.`);
        return;
      }
      const p = await uploadsApi.presign(file.name, file.type || "application/pdf", "bid-docs", file.size);
      const r = await uploadsApi.direct(p.key, file);
      // Guard: never push a partial BidDocument — backend requires all 5 fields.
      const key = r?.key || p?.key;
      const size_bytes = r?.size_bytes ?? file.size;
      if (!key) {
        toast.error(`Upload failed for ${file.name} — missing storage key`);
        return;
      }
      setDocs((d) => [...d, {
        kind, key, filename: file.name,
        size_bytes, uploaded_at: new Date().toISOString(),
      }]);
      // v52cz rev2 — auto-tick the new doc so the Download picker always
      // reflects "everything so far" by default.
      setSelectedKeys((s) => { const n = new Set(s); n.add(key); return n; });
      toast.success(`Uploaded ${file.name}`);
    } catch (err) { showApiError(err); }
    finally {
      // v50s — always clear the <input type="file"> value so the SAME file
      // can be re-selected after a Remove. Browsers suppress onChange when
      // the picked path hasn't changed, which previously left the slot dead
      // after one upload-then-remove cycle.
      if (inputEl) inputEl.value = "";
    }
  };

  const removeDoc = (idx) => {
    const gone = docs[idx]?.key;
    setDocs((d) => d.filter((_, i) => i !== idx));
    if (gone) setSelectedKeys((s) => { const n = new Set(s); n.delete(gone); return n; });
    // Also clear every file input so re-selecting the same filename works.
    document.querySelectorAll('[data-testid^="bid-upload-"] input[type="file"]').forEach((el) => { el.value = ""; });
  };

  const submit = async (e) => {
    e.preventDefault();
    setFormError(null);
    if (!price || Number(price) <= 0) return toast.error("Enter a valid bid price");
    // Strip any partially-uploaded documents so the payload always matches
    // BidCreateIn / BidDocument on the backend (avoids the six "Field required"
    // 422 errors seen when an upload silently returned an incomplete object).
    const cleanDocs = docs.filter(
      (d) => d && d.kind && d.key && d.filename && typeof d.size_bytes === "number" && d.uploaded_at
    );
    // v51bc — both envelope documents are mandatory on submit.
    const kinds = new Set(cleanDocs.map((d) => d.kind));
    if (!kinds.has("technical") || !kinds.has("commercial")) {
      setFormError("Both the Technical and Commercial envelope documents are required before you can submit (PDF, DOC/DOCX, XLS/XLSX, PPT/PPTX, JPG/PNG or DWG). You can keep working on this bid with Save draft.");
      return toast.error("Upload Technical and Commercial documents before submitting");
    }
    setBusy(true);
    try {
      const bid = await bidApi.create({
        notice_ref: noticeRef,
        price_amount: Number(price),
        price_currency: notice.budget_currency || "USD",
        technical_notes: technical, commercial_notes: commercial,
        documents: cleanDocs,
      });
      toast.success(`Bid ${bid.bid_ref} submitted`);
      // Clear local + server draft now that the server has the real bid.
      try { localStorage.removeItem(draftKey); } catch { /* ignore */ }
      try { await bidApi.deleteDraft(noticeRef); } catch { /* ignore */ }
      // If EMD due, immediately go to selected gateway
      if ((bid.emd_due_amount || 0) > 0) {
        let checkout_url;
        if (gateway === "stripe") {
          const chk = await paymentApi.checkout(bid.id, window.location.origin);
          checkout_url = chk.checkout_url;
        } else {
          const chk = await sandboxPayApi.checkout(bid.id, gateway, window.location.origin);
          checkout_url = chk.checkout_url;
        }
        // Open payment gateway in a new tab — Stripe's CSP blocks iframe
        // embedding, so navigating the current window hangs inside preview iframes.
        const w = window.open(checkout_url, "_blank", "noopener,noreferrer");
        if (!w) {
          try { window.top.location.href = checkout_url; }
          catch { window.location.href = checkout_url; }
        }
        toast.info(`${gateway === "stripe" ? "Stripe" : gateway} checkout opened in a new tab`);
        nav("/vendor");
      } else {
        nav("/vendor");
      }
    } catch (err) {
      const msg = formatApiError(err);
      const status = err?.response?.status;
      // v52bj — surface the existing bid id on a 409 so the vendor can
      // open or withdraw it in one click instead of being stuck.
      const dup = err?.response?.data?.detail;
      if (status === 409 && typeof dup === "object" && dup?.existing_bid_id) {
        setFormError(
          `${dup.message} (${dup.existing_bid_ref} · ${dup.existing_status}). ` +
          `Open the existing bid to continue or withdraw it below.`
        );
        setExistingDup(dup);
        showApiError(err, { fallbackTitle: "You already bid on this notice" });
        setBusy(false);
        return;
      }
      const title =
        status === 412 ? "Submission blocked — pre-condition failed" :
        status === 409 ? "Submission blocked — duplicate bid" :
        status === 422 ? "Submission blocked — missing information" :
        status === 400 ? "Submission blocked — deadline or rule violation" :
        "Could not submit bid";
      showApiError(err, { fallbackTitle: title });
      setFormError(msg);
      setBusy(false);
    }
  };

  if (!vendor || !notice) return <div className="p-10 text-slate-500">Loading…</div>;

  const emdConfig = notice.emd_config || { fixed_amount: 0, percentage: 0, currency: notice.budget_currency };
  const emdDue = (emdConfig.fixed_amount || 0) + ((emdConfig.percentage || 0) / 100) * (notice.budget_amount || 0);
  const deadlinePassed = !!notice.submission_deadline && new Date(notice.submission_deadline) < new Date();
  // v52bc — gate submit on both envelope kinds being uploaded.
  const uploadedKinds = new Set(docs.map((d) => d.kind));
  const hasTech = uploadedKinds.has("technical");
  const hasComm = uploadedKinds.has("commercial");
  const docsOk = hasTech && hasComm;

  // Corrigenda acknowledgement state (v52bh)
  const myVendorId = vendor?.id;
  const activeCorr = (corrigenda || []).filter((c) => c.is_active !== false);
  const ackedByMe = (c) => (c.acknowledgements || []).some((a) => a.vendor_id === myVendorId);
  const pendingCorr = activeCorr.filter((c) => !ackedByMe(c));
  const allAcked = pendingCorr.length === 0;

  const acknowledge = async (c) => {
    setAckingId(c.id);
    try {
      await corrigendaApi.acknowledge(c.id);
      setCorrigenda((prev) => prev.map((x) => x.id === c.id
        ? { ...x, acknowledgements: [...(x.acknowledgements || []),
            { vendor_id: myVendorId, vendor_email: vendor?.email,
              vendor_ref: vendor?.vendor_ref, acknowledged_at: new Date().toISOString() }] }
        : x));
      toast.success(`Corrigendum ${c.corrigendum_no || ""} acknowledged`.trim());
    } catch (e) {
      // Already acknowledged is fine — treat as done.
      if (e?.response?.status === 400 || e?.response?.status === 409) {
        setCorrigenda((prev) => prev.map((x) => x.id === c.id
          ? { ...x, acknowledgements: [...(x.acknowledgements || []), { vendor_id: myVendorId }] }
          : x));
      } else {
        showApiError(e, { fallbackTitle: "Could not acknowledge corrigendum" });
      }
    } finally { setAckingId(null); }
  };

  const saveDraft = async () => {
    try {
      const payload = {
        price_amount: price ? Number(price) : null,
        price_currency: notice?.budget_currency || "USD",
        technical_notes: technical, commercial_notes: commercial,
        documents: docs,
      };
      // Always persist locally for offline resilience.
      try {
        localStorage.setItem(draftKey, JSON.stringify({
          ...payload, saved_at: new Date().toISOString(),
        }));
      } catch { /* storage may be full */ }
      // And push to the server so other devices can resume.
      try {
        await bidApi.saveDraft(noticeRef, payload);
        toast.success("Draft saved — you can resume this bid on any device.");
      } catch (e) {
        showApiError(e, { fallbackTitle: "Draft saved locally only — server sync failed" });
      }
    } catch { toast.error("Could not save draft"); }
  };

  return (
    <div className="min-h-screen bg-slate-50 pt-6 pb-40 md:py-10" data-testid="bid-submit-page">
      <div className="max-w-3xl mx-auto px-4 sm:px-6">
        <button onClick={() => nav("/vendor")} className="text-xs text-slate-500 hover:underline">← Back</button>
        <h1 className="text-3xl font-serif mt-2 text-slate-900">Submit a bid</h1>
        <div className="text-sm text-slate-600">{notice.notice_ref}</div>

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
          {deadlinePassed && (
            <div className="border border-red-300 bg-red-50 text-red-800 text-sm rounded-md px-4 py-3"
              data-testid="bid-deadline-passed">
              <strong>Submission deadline has passed</strong> ({(notice.submission_deadline || "").slice(0, 10)}).
              This notice is no longer accepting bids.
            </div>
          )}
          {formError && (
            <div className="border border-red-300 bg-red-50 text-red-800 text-sm rounded-md px-4 py-3 whitespace-pre-line"
              data-testid="bid-submit-error">
              {formError}
              {existingDup?.existing_bid_id && (
                <div className="mt-2 flex gap-2 flex-wrap">
                  <Link to={`/vendor/mybids`}
                        data-testid="bid-dup-open-mybids"
                        className="px-3 py-1.5 text-[11px] uppercase tracking-widest bg-slate-900 text-white hover:bg-black">
                    Open my bids
                  </Link>
                  <button type="button"
                    data-testid="bid-dup-withdraw"
                    onClick={async () => {
                      if (!window.confirm(`Withdraw bid ${existingDup.existing_bid_ref}? You can create a new bid on this notice afterwards.`)) return;
                      try {
                        await bidApi.withdraw(existingDup.existing_bid_id);
                        toast.success("Previous bid withdrawn — you can submit again now.");
                        setExistingDup(null); setFormError(null);
                      } catch (e) {
                        showApiError(e, { fallbackTitle: "Could not withdraw the stuck bid" });
                      }
                    }}
                    className="px-3 py-1.5 text-[11px] uppercase tracking-widest border border-red-700 text-red-700 hover:bg-red-700 hover:text-white">
                    Withdraw stuck bid
                  </button>
                </div>
              )}
            </div>
          )}

          {activeCorr.length > 0 && (
            <div className={`border rounded-md p-4 space-y-3 ${
              allAcked ? "border-emerald-300 bg-emerald-50" : "border-amber-400 bg-amber-50"}`}
              data-testid="bid-corrigenda-panel">
              <div className="text-sm font-semibold text-slate-900">
                Tender corrigenda ({activeCorr.length})
                {!allAcked && <span className="text-amber-800 font-normal"> — acknowledge all before submitting</span>}
              </div>
              {activeCorr.map((c) => (
                <div key={c.id} className="bg-white border border-slate-200 rounded p-3 text-sm"
                     data-testid={`bid-corrigendum-${c.id}`}>
                  <div className="font-medium text-slate-800">
                    {c.corrigendum_no ? `Corrigendum ${c.corrigendum_no} · ` : ""}{c.title}
                  </div>
                  {c.summary && <div className="text-slate-600 text-xs mt-1 whitespace-pre-wrap">{c.summary}</div>}
                  {c.new_submission_deadline && (
                    <div className="text-xs text-slate-600 mt-1">
                      New deadline: <strong>{String(c.new_submission_deadline).slice(0, 10)}</strong>
                    </div>
                  )}
                  <div className="mt-2">
                    {ackedByMe(c) ? (
                      <span className="text-[11px] uppercase tracking-widest text-emerald-700 font-semibold"
                            data-testid={`bid-corr-acked-${c.id}`}>Acknowledged ✓</span>
                    ) : (
                      <button type="button" onClick={() => acknowledge(c)} disabled={ackingId === c.id}
                        className="px-3 py-1.5 text-[11px] uppercase tracking-widest border border-amber-700 text-amber-800 hover:bg-amber-700 hover:text-white disabled:opacity-50"
                        data-testid={`bid-corr-ack-${c.id}`}>
                        {ackingId === c.id ? "Acknowledging…" : "I acknowledge this corrigendum"}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
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
            <div className="text-sm font-semibold text-slate-900">Supporting documents <span className="text-red-600">*</span></div>
            <div className="text-xs text-slate-600">
              Both <strong>Technical</strong> and <strong>Commercial</strong> documents are required to submit
              (PDF, DOC/DOCX, XLS/XLSX, PPT/PPTX, JPG/PNG or DWG).
              {!docsOk && (
                <span className="ml-2 text-amber-700" data-testid="bid-docs-status">
                  Missing: {!hasTech && "Technical"}{!hasTech && !hasComm && " + "}{!hasComm && "Commercial"}
                </span>
              )}
              {docsOk && <span className="ml-2 text-emerald-700" data-testid="bid-docs-status">Both envelopes ready ✓</span>}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
              {[["technical", "Technical document"], ["commercial", "Commercial document"], ["supporting", "Other doc"]].map(([k, label]) => (
                <label key={k}
                  className="group border-2 border-dashed border-amber-400 bg-amber-50 hover:bg-amber-100 hover:border-amber-500 rounded-md p-3 text-center cursor-pointer transition-colors"
                  data-testid={`bid-upload-${k}`}>
                  <input type="file"
                    accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.jpg,.jpeg,.png,.dwg,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-powerpoint,application/vnd.openxmlformats-officedocument.presentationml.presentation,image/jpeg,image/png,image/vnd.dwg,application/acad,application/dwg"
                    hidden
                    onChange={(e) => e.target.files?.[0] && uploadFile(k, e.target.files[0], e.target)} />
                  <span className="block text-amber-900 font-semibold">{label}</span>
                  <span className="block text-amber-700 mt-1 font-medium">+ Click to upload</span>
                  <span className="block text-[10px] text-amber-700/80 mt-1 leading-snug">
                    PDF, DOC/DOCX, XLS/XLSX, PPT/PPTX, JPG/PNG, DWG only · max 10 MB
                  </span>
                </label>
              ))}
            </div>
            {docs.length > 0 && (
              <div className="mt-2 space-y-2" data-testid="bid-docs-list">
                {/* v52cz — single clearly-visible "Download all" so the vendor
                    can pull every uploaded envelope + supporting document in
                    one ZIP, regardless of count (works for 1 doc or 20). */}
                <div className="flex justify-end">
                  <button type="button"
                    data-testid="bid-docs-download-all"
                    onClick={async () => {
                      const keys = docs.map((x) => x.key).filter(Boolean);
                      if (!keys.length) return toast.error("Nothing to download yet");
                      try {
                        await uploadsApi.downloadBundle(keys, {
                          filename: `bid-${noticeRef || "documents"}-documents`,
                        });
                        toast.success(`Downloading ${keys.length} document${keys.length === 1 ? "" : "s"} as a ZIP`);
                      } catch (err) {
                        showApiError(err, { fallbackTitle: "Could not bundle the documents" });
                      }
                    }}
                    className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-widest border border-slate-900 text-slate-900 bg-white hover:bg-slate-900 hover:text-white transition-colors rounded-md">
                    ↓ Download all ({docs.length})
                  </button>
                </div>
                {docs.map((d, i) => {
                  const checked = d.key ? selectedKeys.has(d.key) : false;
                  return (
                  <div key={`bid-att-${d.filename || d.kind || i}`}
                    className="flex items-center justify-between gap-2 bg-white border border-slate-300 px-3 py-2 rounded-md"
                    data-testid={`bid-doc-${d.kind}-${i}`}>
                    <label className="flex items-center gap-2 min-w-0 flex-1 cursor-pointer">
                      <input type="checkbox" checked={checked}
                        disabled={!d.key}
                        onChange={(e) => {
                          if (!d.key) return;
                          setSelectedKeys((s) => {
                            const n = new Set(s);
                            if (e.target.checked) n.add(d.key); else n.delete(d.key);
                            return n;
                          });
                        }}
                        data-testid={`bid-doc-pick-${d.kind}-${i}`}
                        className="w-4 h-4 accent-slate-900 shrink-0" />
                      <span className="text-xs text-slate-900 font-medium break-all min-w-0">
                        <span className="uppercase text-slate-500 font-semibold">{d.kind}</span>
                        {" · "}{d.filename}
                        <span className="text-slate-500"> ({Math.round((d.size_bytes || 0) / 1024)} KB)</span>
                      </span>
                    </label>
                    <span className="flex gap-3 shrink-0 text-xs font-semibold">
                      <button type="button"
                        onClick={() => uploadsApi.openInNewTab(d.key, { filename: d.filename })
                                                 .catch((err) => showApiError(err, { fallbackTitle: "Could not open file" }))}
                        className="text-slate-900 underline hover:text-slate-600"
                        data-testid={`bid-doc-view-${d.kind}-${i}`}>View</button>
                      <button type="button" onClick={() => removeDoc(i)}
                        className="text-red-600 hover:underline"
                        data-testid={`bid-doc-remove-${d.kind}-${i}`}>Remove</button>
                    </span>
                  </div>
                  );
                })}
              </div>
            )}
          </div>

          {emdDue > 0 && (
            <div>
              <div className="text-sm font-semibold mb-2">EMD payment gateway</div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2" data-testid="gateway-selector">
                {GATEWAYS.map((g) => (
                  <label key={g.id}
                    className={`border rounded-md p-3 cursor-pointer text-center text-xs ${gateway === g.id ? "border-slate-900 bg-slate-50 ring-1 ring-slate-900" : "hover:border-slate-400"}`}
                    data-testid={`gateway-${g.id}`}>
                    <input type="radio" name="gateway" value={g.id} checked={gateway === g.id}
                      onChange={(e) => setGateway(e.target.value)} className="sr-only" />
                    <div className="font-semibold text-slate-900">{g.label}</div>
                    <div className="text-slate-500 mt-1">{g.note}</div>
                  </label>
                ))}
              </div>
            </div>
          )}

          <div className="flex gap-3 flex-wrap">
            <button type="button" onClick={saveDraft} disabled={busy}
              className="flex-1 min-w-[160px] border border-slate-300 bg-white text-slate-800 rounded-md py-4 text-sm font-semibold hover:bg-slate-50 disabled:opacity-60"
              data-testid="bid-save-draft-btn">
              Save draft
            </button>
            <button type="submit" disabled={busy || deadlinePassed || !docsOk || !allAcked}
              className="flex-[2] bg-slate-900 text-white rounded-md py-4 text-sm font-semibold hover:bg-slate-800 disabled:opacity-60 disabled:cursor-not-allowed"
              data-testid="bid-submit-btn"
              title={!allAcked ? "Acknowledge every corrigendum above first" : !docsOk ? "Upload Technical AND Commercial documents first" : ""}>
              {busy ? "Submitting…" : deadlinePassed ? "Deadline passed" : !allAcked ? `Acknowledge ${pendingCorr.length} corrigend${pendingCorr.length === 1 ? "um" : "a"} to submit` : !docsOk ? "Upload both envelopes to submit" : (emdDue > 0 ? `Submit & pay EMD (${emdConfig.currency} ${emdDue.toLocaleString()})` : "Submit bid")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
