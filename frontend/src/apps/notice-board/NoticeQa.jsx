import { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";
import { noticeQaApi, formatApiError } from "@/lib/api";

/**
 * NoticeQa — public bidder-clarification thread on the Notice detail page.
 * Asks are throttled by the browser (client-side de-dup) and only the answered
 * pairs are visible to everyone, so nobody gets an information advantage.
 */
export default function NoticeQa({ noticeRef }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ asker_name: "", asker_email: "", question: "" });
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(() => {
    noticeQaApi.listPublic(noticeRef)
      .then((d) => setItems(d.items || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [noticeRef]);
  useEffect(() => { load(); }, [load]);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.asker_name || !form.asker_email || form.question.trim().length < 8) {
      toast.error("Name, email and a question of 8+ characters are required.");
      return;
    }
    setSubmitting(true);
    try {
      await noticeQaApi.ask(noticeRef, form);
      toast.success("Question sent — you'll see the reply here once the tender team responds.");
      setForm({ asker_name: "", asker_email: "", question: "" });
      load();
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setSubmitting(false); }
  };

  return (
    <section className="mt-10 bg-white border border-brand-navy/10 p-8" data-testid="notice-qa">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <div>
          <div className="pmc-label">Clarifications</div>
          <h2 className="font-display text-xl text-brand-navy mt-1">Ask a clarification</h2>
          <p className="text-xs text-brand-navy/60 mt-1 max-w-lg">
            Once answered, the reply is visible to every prospective bidder so nobody
            gets an information advantage. Only your first name and a masked email are shown publicly.
          </p>
        </div>
        <span className="text-xs text-brand-navy/50 tabular-nums">{items.length} answered</span>
      </div>

      <form onSubmit={submit} className="mt-4 grid gap-3 md:grid-cols-3">
        <input value={form.asker_name}
               onChange={(e) => setForm({ ...form, asker_name: e.target.value })}
               placeholder="Your name" data-testid="qa-name"
               className="px-3 py-2 border border-brand-navy/20 text-sm" />
        <input value={form.asker_email} type="email"
               onChange={(e) => setForm({ ...form, asker_email: e.target.value })}
               placeholder="you@company.com" data-testid="qa-email"
               className="px-3 py-2 border border-brand-navy/20 text-sm" />
        <button type="submit" disabled={submitting}
                data-testid="qa-submit"
                className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40">
          {submitting ? "Sending…" : "Send question"}
        </button>
        <textarea value={form.question}
                  onChange={(e) => setForm({ ...form, question: e.target.value })}
                  placeholder="Type your clarification here…"
                  rows={3} data-testid="qa-question"
                  className="md:col-span-3 px-3 py-2 border border-brand-navy/20 text-sm" />
      </form>

      <div className="mt-8 space-y-4" data-testid="qa-thread">
        {loading && <div className="text-brand-navy/50 text-sm">Loading…</div>}
        {!loading && items.length === 0 && (
          <div className="text-brand-navy/50 text-sm italic">
            No clarifications have been published yet.
          </div>
        )}
        {items.map((q) => (
          <article key={q.id} className="border-l-4 border-brand-navy-soft/40 pl-4" data-testid={`qa-item-${q.id}`}>
            <div className="text-xs text-brand-navy/60">
              <span className="font-semibold text-brand-navy">{q.asker_name}</span>
              <span className="mx-2">·</span>
              <span className="font-mono">{q.asker_email_masked}</span>
              <span className="mx-2">·</span>
              <span>{q.asked_at?.slice(0, 10)}</span>
            </div>
            <p className="mt-1 text-sm text-brand-navy/85 whitespace-pre-wrap">{q.question}</p>
            {q.answer && (
              <div className="mt-3 bg-brand-pale/60 p-3">
                <div className="text-[10px] uppercase tracking-widest text-brand-navy/50">
                  Tender team reply · {q.answered_at?.slice(0, 10)}
                </div>
                <p className="mt-1 text-sm text-brand-navy whitespace-pre-wrap">{q.answer}</p>
              </div>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
