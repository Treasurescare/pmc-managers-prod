/**
 * EngagementsPanel — Wave 38 admin surface for the quote pipeline.
 *
 * Lists every engagement (quote request), lets admin set the quoted amount +
 * currency, and one-click generates a Stripe checkout URL for the buyer.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { useI18n } from "@/context/I18nContext";
import { InfoDot } from "@/components/InfoDot";
import { engagementsApi, showApiError } from "@/lib/api";
import { useListPager } from "@/components/ListPager";

const STATUS_STYLE = {
  quote_requested: "bg-amber-100 text-amber-900 border-amber-400",
  quoted:          "bg-sky-100 text-sky-900 border-sky-400",
  invoiced:        "bg-indigo-100 text-indigo-900 border-indigo-400",
  paid:            "bg-emerald-100 text-emerald-900 border-emerald-400",
  cancelled:       "bg-slate-100 text-slate-700 border-slate-300",
};

const CURRENCIES = ["USD", "GBP", "EUR", "KZT", "INR", "AED", "SAR"];

function QuoteModal({ engagement, onClose, onSaved }) {
  const { t } = useI18n();
  const [amount, setAmount] = useState(engagement?.quoted_amount || "");
  const [currency, setCurrency] = useState(engagement?.quoted_currency || engagement?.product_currency || "USD");
  const [notes, setNotes] = useState(engagement?.admin_notes || "");
  const [validUntil, setValidUntil] = useState(engagement?.quote_valid_until || "");
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      await engagementsApi.saveQuote(engagement.id, {
        quoted_amount: Number(amount),
        quoted_currency: currency,
        admin_notes: notes || null,
        valid_until: validUntil || null,
      });
      toast.success("Quote saved — buyer can now be invoiced");
      onSaved();
    } catch (e) { showApiError(e, { fallbackTitle: "Save failed" }); }
    finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 bg-brand-navy/40 backdrop-blur-sm z-50 flex items-start justify-center p-6 overflow-y-auto"
         data-testid="engagement-quote-modal">
      <div className="bg-white border-2 border-brand-navy w-full max-w-lg p-8 my-8">
        <div className="flex items-center justify-between">
          <h3 className="font-display text-xl text-brand-navy">{t("panels.engagements.quote_modal_title")}</h3>
          <button onClick={onClose} className="text-brand-navy/60 hover:text-brand-navy"
                  data-testid="engagement-quote-close">✕</button>
        </div>
        <div className="mt-2 text-xs text-brand-navy/60">
          <b>{engagement.product_name}</b> · buyer <span className="font-mono">{engagement.buyer_email}</span> · qty {engagement.quantity}
        </div>
        {engagement.buyer_notes && (
          <div className="mt-3 border-l-4 border-brand-navy/20 pl-3 text-sm italic text-brand-navy/70">
            "{engagement.buyer_notes}"
          </div>
        )}
        <div className="mt-6 grid gap-4">
          <label><div className="pmc-label">{t("panels.engagements.quoted_amount")}<InfoDot tip="Total amount to invoice the buyer for this engagement. Enter the pre-tax subtotal only." /></div>
            <input type="number" value={amount} onChange={(e) => setAmount(e.target.value)}
                   data-testid="engagement-quote-amount"
                   className="mt-1 w-full border border-brand-navy/20 px-3 py-2 font-mono tabular-nums"/></label>
          <label><div className="pmc-label">{t("panels.engagements.currency")}<InfoDot tip="ISO-4217 currency code. Determines the Stripe checkout currency." /></div>
            <select value={currency} onChange={(e) => setCurrency(e.target.value)}
                    data-testid="engagement-quote-currency"
                    className="mt-1 w-full border border-brand-navy/20 px-3 py-2 bg-white font-mono">
              {CURRENCIES.map((c) => <option key={c}>{c}</option>)}
            </select></label>
          <label><div className="pmc-label">{t("panels.engagements.valid_until")}<InfoDot tip="Optional. Quote expiry date. After this date the Stripe checkout link is disabled server-side." /></div>
            <input type="date" value={validUntil?.slice(0, 10) || ""}
                   onChange={(e) => setValidUntil(e.target.value)}
                   className="mt-1 w-full border border-brand-navy/20 px-3 py-2"/></label>
          <label><div className="pmc-label">{t("panels.engagements.admin_notes")}</div>
            <textarea rows={3} value={notes} onChange={(e) => setNotes(e.target.value)}
                      data-testid="engagement-quote-notes"
                      className="mt-1 w-full border border-brand-navy/20 px-3 py-2"/></label>
        </div>
        <div className="mt-8 flex items-center justify-end gap-3">
          <button onClick={onClose} className="px-5 py-2 border border-brand-navy/20 text-sm">{t("panels.engagements.cancel")}</button>
          <button onClick={save} disabled={saving || !amount || Number(amount) <= 0}
                  data-testid="engagement-quote-save"
                  className="px-5 py-2 bg-brand-navy text-white text-xs uppercase tracking-widest disabled:opacity-50">
            {saving ? t("panels.engagements.saving") : t("panels.engagements.save_quote")}
          </button>
        </div>
      </div>
    </div>
  );
}

function CancelModal({ engagement, onClose, onDone }) {
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);
  const submit = async () => {
    if (reason.trim().length < 5) {
      toast.error("Please enter a cancellation reason (min 5 characters)");
      return;
    }
    setSaving(true);
    try {
      await engagementsApi.cancel(engagement.id, reason.trim());
      toast.success("Engagement cancelled");
      onDone();
    } catch (e) { showApiError(e, { fallbackTitle: "Cancel failed" }); }
    finally { setSaving(false); }
  };
  return (
    <div className="fixed inset-0 bg-brand-navy/40 backdrop-blur-sm z-50 flex items-start justify-center p-6 overflow-y-auto"
         data-testid="engagement-cancel-modal">
      <div className="bg-white border-2 border-red-500 w-full max-w-lg p-8 my-8">
        <div className="flex items-center justify-between">
          <h3 className="font-display text-xl text-red-700">Cancel engagement</h3>
          <button onClick={onClose} className="text-brand-navy/60 hover:text-brand-navy"
                  data-testid="engagement-cancel-close">✕</button>
        </div>
        <div className="mt-2 text-xs text-brand-navy/60">
          <b>{engagement.product_name}</b> · buyer <span className="font-mono">{engagement.buyer_email}</span>
        </div>
        <label className="mt-5 block">
          <div className="pmc-label">Cancellation reason <span className="text-red-600">*</span></div>
          <textarea rows={4} value={reason} onChange={(e) => setReason(e.target.value)}
                    data-testid="engagement-cancel-reason"
                    placeholder="Why is this engagement being cancelled? (visible to buyer + audit log)"
                    className="mt-1 w-full border border-brand-navy/20 px-3 py-2 text-sm" />
          <div className="mt-1 text-[11px] text-brand-navy/50">
            Minimum 5 characters. Logged to the ledger and emailed to the buyer.
          </div>
        </label>
        <div className="mt-8 flex items-center justify-end gap-3">
          <button onClick={onClose} className="px-5 py-2 border border-brand-navy/20 text-sm">Keep open</button>
          <button onClick={submit} disabled={saving || reason.trim().length < 5}
                  data-testid="engagement-cancel-confirm"
                  className="px-5 py-2 bg-red-600 text-white text-xs uppercase tracking-widest disabled:opacity-50">
            {saving ? "Cancelling…" : "Confirm cancel"}
          </button>
        </div>
      </div>
    </div>
  );
}

function MeetingModal({ engagement, onClose, onDone }) {
  const [when, setWhen] = useState("");
  const [duration, setDuration] = useState(60);
  const [agenda, setAgenda] = useState("");
  const [attendee, setAttendee] = useState("buyer");
  const [link, setLink] = useState("");
  const [saving, setSaving] = useState(false);
  const [meetings, setMeetings] = useState([]);
  useEffect(() => {
    engagementsApi.listMeetings(engagement.id)
      .then((r) => setMeetings(r.items || []))
      .catch(() => {});
  }, [engagement.id]);
  const submit = async () => {
    if (!when) { toast.error("Pick a date & time"); return; }
    if (agenda.trim().length < 3) { toast.error("Agenda is required"); return; }
    setSaving(true);
    try {
      await engagementsApi.scheduleMeeting(engagement.id, {
        scheduled_at: new Date(when).toISOString(),
        duration_minutes: Number(duration) || 60,
        agenda: agenda.trim(),
        attendee_role: attendee,
        location_or_link: link.trim() || null,
      });
      toast.success("Meeting scheduled — invitation sent");
      onDone();
    } catch (e) { showApiError(e, { fallbackTitle: "Schedule failed" }); }
    finally { setSaving(false); }
  };
  const print = () => {
    const win = window.open("", "_blank");
    if (!win) return;
    win.document.write(`<!doctype html><html><head><title>Agenda — ${engagement.product_name}</title>
      <style>body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:720px;margin:40px auto;color:#1a2b35}
        h1{font-size:22px;margin-bottom:4px} .meta{color:#64748b;font-size:13px} .agenda{white-space:pre-wrap;margin-top:24px;padding:16px;border:1px solid #ddd}</style>
      </head><body>
      <h1>Meeting agenda</h1>
      <div class="meta">${engagement.product_name} · ${engagement.buyer_email} · ${when || "TBD"}</div>
      <div class="agenda">${agenda || "(no agenda)"}</div>
      <p><b>Attendees:</b> ${attendee} · <b>Duration:</b> ${duration} min · <b>Location/Link:</b> ${link || "TBD"}</p>
      </body></html>`);
    win.document.close(); win.focus(); setTimeout(() => win.print(), 200);
  };
  return (
    <div className="fixed inset-0 bg-brand-navy/40 backdrop-blur-sm z-50 flex items-start justify-center p-6 overflow-y-auto"
         data-testid="engagement-meeting-modal">
      <div className="bg-white border-2 border-brand-navy w-full max-w-xl p-8 my-8">
        <div className="flex items-center justify-between">
          <h3 className="font-display text-xl text-brand-navy">Schedule meeting</h3>
          <button onClick={onClose} className="text-brand-navy/60 hover:text-brand-navy"
                  data-testid="engagement-meeting-close">✕</button>
        </div>
        <div className="mt-2 text-xs text-brand-navy/60">
          <b>{engagement.product_name}</b> · buyer <span className="font-mono">{engagement.buyer_email}</span>
        </div>
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <label className="md:col-span-1">
            <div className="pmc-label">Date &amp; time <span className="text-red-600">*</span></div>
            <input type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)}
                   data-testid="engagement-meeting-when"
                   className="mt-1 w-full border border-brand-navy/20 px-3 py-2" />
          </label>
          <label className="md:col-span-1">
            <div className="pmc-label">Duration (min)</div>
            <input type="number" min="5" max="480" step="5" value={duration}
                   onChange={(e) => setDuration(e.target.value)}
                   data-testid="engagement-meeting-duration"
                   className="mt-1 w-full border border-brand-navy/20 px-3 py-2" />
          </label>
          <label className="md:col-span-1">
            <div className="pmc-label">Attendees</div>
            <select value={attendee} onChange={(e) => setAttendee(e.target.value)}
                    data-testid="engagement-meeting-attendee"
                    className="mt-1 w-full border border-brand-navy/20 px-3 py-2 bg-white">
              <option value="buyer">Buyer</option>
              <option value="supplier">Supplier</option>
              <option value="both">Buyer + Supplier</option>
            </select>
          </label>
          <label className="md:col-span-1">
            <div className="pmc-label">Location / Link</div>
            <input value={link} onChange={(e) => setLink(e.target.value)}
                   placeholder="https://meet.pmc / Office 4B"
                   data-testid="engagement-meeting-link"
                   className="mt-1 w-full border border-brand-navy/20 px-3 py-2" />
          </label>
          <label className="md:col-span-2">
            <div className="pmc-label">Agenda <span className="text-red-600">*</span></div>
            <textarea rows={5} value={agenda} onChange={(e) => setAgenda(e.target.value)}
                      data-testid="engagement-meeting-agenda"
                      placeholder="1. Review scope …&#10;2. Confirm pricing …&#10;3. Next steps"
                      className="mt-1 w-full border border-brand-navy/20 px-3 py-2 text-sm" />
          </label>
        </div>
        {meetings.length > 0 && (
          <div className="mt-6 border-t pt-4" data-testid="engagement-meeting-list">
            <div className="pmc-label mb-2">Scheduled ({meetings.length})</div>
            <ul className="text-xs space-y-1 text-brand-navy/80">
              {meetings.map((m) => (
                <li key={m.id} className="flex gap-2">
                  <span className="font-mono">{(m.scheduled_at || "").replace("T", " ").slice(0, 16)}</span>
                  <span>·</span>
                  <span>{m.attendee_role}</span>
                  <span>·</span>
                  <span className="truncate">{m.agenda}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        <div className="mt-8 flex items-center justify-end gap-3">
          <button onClick={print} data-testid="engagement-meeting-print"
                  className="px-4 py-2 border border-brand-navy/20 text-xs uppercase tracking-widest">Print agenda</button>
          <button onClick={onClose} className="px-5 py-2 border border-brand-navy/20 text-sm">Close</button>
          <button onClick={submit} disabled={saving || !when || agenda.trim().length < 3}
                  data-testid="engagement-meeting-save"
                  className="px-5 py-2 bg-brand-navy text-white text-xs uppercase tracking-widest disabled:opacity-50">
            {saving ? "Scheduling…" : "Schedule"}
          </button>
        </div>
      </div>
    </div>
  );
}

function StatusPill({ s }) {
  const cls = STATUS_STYLE[s] || "bg-brand-navy/5 border-brand-navy/20";
  return (
    <span className={`inline-block px-2 py-0.5 border text-[10px] uppercase tracking-widest ${cls}`}>
      {s?.replace(/_/g, " ")}
    </span>
  );
}

function EngagementRow({ e, onQuote, onInvoice, onCancel, onMeeting }) {
  const { t } = useI18n();
  return (
    <tr className="border-b border-brand-navy/10" data-testid={`engagement-row-${e.id}`}>
      <td className="px-3 py-3">
        <div className="text-sm font-semibold text-brand-navy">{e.product_name}</div>
        <div className="text-xs text-brand-navy/60 font-mono">{e.product_code}</div>
      </td>
      <td className="px-3 py-3 text-xs">
        {/* EN-03 fix — buyer email is a jump link back to the Vendors master */}
        <a href={`/admin?tab=vendors&search=${encodeURIComponent(e.buyer_email)}`}
           data-testid={`engagement-buyer-link-${e.id}`}
           className="underline decoration-dotted text-brand-navy hover:text-brand-navy-soft">
          {e.buyer_email}
        </a>
        {e.buyer_company && <div className="text-brand-navy/60">{e.buyer_company}</div>}
      </td>
      <td className="px-3 py-3 text-center text-sm">{e.quantity}</td>
      <td className="px-3 py-3 text-right font-mono tabular-nums text-sm">
        {e.quoted_amount
          ? `${e.quoted_currency || "USD"} ${Number(e.quoted_amount).toLocaleString()}`
          : <span className="text-brand-navy/40">—</span>}
      </td>
      <td className="px-3 py-3"><StatusPill s={e.status}/></td>
      <td className="px-3 py-3 text-right space-x-2">
        {e.status === "quote_requested" && (
          <button onClick={() => onQuote(e)} data-testid={`engagement-set-quote-${e.id}`}
                  className="text-xs uppercase tracking-widest text-sky-800 hover:underline">{t("panels.engagements.set_quote")}</button>
        )}
        {e.status === "quoted" && (
          <>
            <button onClick={() => onQuote(e)} className="text-xs uppercase tracking-widest text-brand-navy hover:underline">{t("panels.engagements.requote")}</button>
            <button onClick={() => onInvoice(e)} data-testid={`engagement-invoice-${e.id}`}
                    className="text-xs uppercase tracking-widest text-indigo-800 hover:underline font-semibold">{t("panels.engagements.invoice")}</button>
          </>
        )}
        {e.status === "invoiced" && e.checkout_url && (
          <a href={e.checkout_url} target="_blank" rel="noreferrer"
             className="text-xs uppercase tracking-widest text-indigo-800 hover:underline">{t("panels.engagements.pay_link")}</a>
        )}
        {!["paid", "cancelled"].includes(e.status) && (
          <>
            <button onClick={() => onMeeting(e)} data-testid={`engagement-meeting-${e.id}`}
                    className="text-xs uppercase tracking-widest text-emerald-800 hover:underline">Schedule meeting</button>
            <button onClick={() => onCancel(e)} data-testid={`engagement-cancel-${e.id}`}
                    className="text-xs uppercase tracking-widest text-red-700 hover:underline">{t("panels.engagements.cancel")}</button>
          </>
        )}
      </td>
    </tr>
  );
}

export default function EngagementsPanel() {
  const { t } = useI18n();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [quoting, setQuoting] = useState(null);
  const [cancelling, setCancelling] = useState(null);
  const [meeting, setMeeting] = useState(null);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const d = await engagementsApi.listAdmin();
      setItems(d.items || []);
    } catch (e) { showApiError(e, { fallbackTitle: "Load failed" }); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { reload(); }, [reload]);

  const invoice = async (e) => {
    try {
      const d = await engagementsApi.checkout(e.id, window.location.origin);
      toast.success(`Invoice generated — pay-link ready`);
      if (window.confirm("Open the Stripe pay-link now?")) window.open(d.checkout_url, "_blank");
      reload();
    } catch (err) { showApiError(err, { fallbackTitle: "Invoice failed" }); }
  };

  const cancel = (e) => setCancelling(e);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return items.filter((i) =>
      (statusFilter === "all" || i.status === statusFilter)
      && (!q || (i.product_name || "").toLowerCase().includes(q)
             || (i.product_code || "").toLowerCase().includes(q)
             || (i.buyer_email || "").toLowerCase().includes(q)
             || (i.buyer_company || "").toLowerCase().includes(q))
    );
  }, [items, statusFilter, search]);

  const { paged, controls } = useListPager(filtered, { testid: "engagement-pager" });

  const counts = useMemo(() => {
    const c = { all: items.length };
    for (const i of items) c[i.status] = (c[i.status] || 0) + 1;
    return c;
  }, [items]);

  return (
    <div className="space-y-6" data-testid="engagements-panel">
      <section>
        <div className="pmc-label">{t("panels.engagements.kicker")}</div>
        <h2 className="font-display text-2xl text-brand-navy mt-1">{t("panels.engagements.heading")}</h2>
        <p className="text-sm text-brand-navy/60 mt-2 max-w-xl">
          {t("panels.engagements.subhead")}
        </p>
      </section>

      <div className="flex flex-wrap gap-2 items-center">
        {["all", "quote_requested", "quoted", "invoiced", "paid", "cancelled"].map((s) => (
          <button key={s} onClick={() => setStatusFilter(s)}
                  data-testid={`engagement-filter-${s}`}
                  className={`px-3 py-1.5 text-[11px] uppercase tracking-widest border ${
                    statusFilter === s ? "bg-brand-navy text-white border-brand-navy"
                      : "text-brand-navy/70 border-brand-navy/20 hover:border-brand-navy"}`}>
            {s === "all" ? t("panels.engagements.filter_all") : s.replace(/_/g, " ")} ({counts[s] || 0})
          </button>
        ))}
        <input value={search} onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by product, buyer email or company…"
          data-testid="engagement-search"
          className="flex-1 min-w-[220px] px-3 py-1.5 border border-brand-navy/20 text-sm bg-white" />
      </div>

      {loading ? (
        <div className="text-brand-navy/60 py-10 text-center">{t("panels.engagements.loading")}</div>
      ) : (
        <div className="border border-brand-navy/10 bg-white overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-brand-navy text-white uppercase text-xs tracking-widest">
              <tr>
                <th className="px-3 py-3 text-left">{t("panels.engagements.col_product")}</th>
                <th className="px-3 py-3 text-left">{t("panels.engagements.col_buyer")}</th>
                <th className="px-3 py-3 text-center">{t("panels.engagements.col_qty")}</th>
                <th className="px-3 py-3 text-right">{t("panels.engagements.col_quoted")}</th>
                <th className="px-3 py-3 text-left">{t("panels.engagements.col_status")}</th>
                <th className="px-3 py-3 text-right">{t("panels.engagements.col_actions")}</th>
              </tr>
            </thead>
            <tbody>
              {paged.map((e) => (
                <EngagementRow key={e.id} e={e} onQuote={setQuoting} onInvoice={invoice}
                               onCancel={cancel} onMeeting={setMeeting}/>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={6} className="text-center py-10 text-brand-navy/60">
                  {t("panels.engagements.empty")}
                </td></tr>
              )}
            </tbody>
          </table>
          {controls}
        </div>
      )}

      {quoting && (
        <QuoteModal engagement={quoting}
                     onClose={() => setQuoting(null)}
                     onSaved={() => { setQuoting(null); reload(); }}/>
      )}
      {cancelling && (
        <CancelModal engagement={cancelling}
                     onClose={() => setCancelling(null)}
                     onDone={() => { setCancelling(null); reload(); }}/>
      )}
      {meeting && (
        <MeetingModal engagement={meeting}
                      onClose={() => setMeeting(null)}
                      onDone={() => { setMeeting(null); reload(); }}/>
      )}
    </div>
  );
}
