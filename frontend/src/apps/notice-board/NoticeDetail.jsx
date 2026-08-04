import { useEffect, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { publicApi, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import TopBar from "@/apps/shared/TopBar";
import Footer from "@/apps/shared/Footer";
import NoticeQa from "./NoticeQa";
import { toast } from "sonner";

function DetailField({ label, value, mono = false }) {
  if (value == null || value === "") return null;
  return (
    <div className="border-t border-brand-navy/10 py-4">
      <div className="pmc-label">{label}</div>
      <div className={`mt-1 text-brand-navy ${mono ? "font-mono tabular-nums text-sm" : ""}`}>{value}</div>
    </div>
  );
}

export default function NoticeDetail() {
  const { t } = useI18n();
  const { noticeRef } = useParams();
  const navigate = useNavigate();
  const [notice, setNotice] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    publicApi.getNotice(noticeRef)
      .then((n) => !cancelled && setNotice(n))
      .catch((e) => {
        if (cancelled) return;
        toast.error(formatApiError(e));
        setTimeout(() => navigate("/notices"), 1200);
      })
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [noticeRef, navigate]);

  useEffect(() => {
    if (notice) document.title = `${notice.title} — PMC Managers`;
    return () => { document.title = "PMC Managers · Global Tender Board"; };
  }, [notice]);

  const budget = notice?.budget_amount
    ? new Intl.NumberFormat("en-US", { style: "currency", currency: notice.budget_currency || "USD", maximumFractionDigits: 0 }).format(notice.budget_amount)
    : null;
  const deadline = notice?.submission_deadline ? new Date(notice.submission_deadline) : null;
  const preBid = notice?.pre_bid_meeting_date ? new Date(notice.pre_bid_meeting_date) : null;
  const publishedAt = notice?.published_at ? new Date(notice.published_at) : null;

  return (
    <div className="min-h-screen bg-brand-pale flex flex-col">
      <TopBar />
      <main className="flex-1 max-w-7xl mx-auto w-full px-6 lg:px-10 py-10">
        <div className="flex items-center justify-between gap-4">
          <Link to="/notices" className="text-xs uppercase tracking-widest text-brand-navy/60 hover:text-brand-navy inline-flex items-center gap-2" data-testid="back-to-list">
            ← {t("notice.back_to_list")}
          </Link>
          {notice && (
            <button
              type="button"
              onClick={() => window.print()}
              data-testid="print-notice"
              className="px-4 py-2 text-[11px] font-semibold uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5"
            >
              Print / Save as PDF
            </button>
          )}
        </div>

        {loading && <div className="text-brand-navy/60 py-16 text-center">{t("common.loading")}</div>}

        {notice && (
          <div className="mt-6 grid gap-10 lg:grid-cols-[8fr_4fr] lg:gap-14 items-start">
            <article className="bg-white border border-brand-navy/10 p-8 lg:p-12" data-testid={`notice-detail-${notice.notice_ref}`}>
              <div className="flex flex-wrap items-baseline gap-3">
                <span className="pmc-pill-navy uppercase">{notice.document_type}</span>
                <span className="pmc-label text-brand-navy-soft">{notice.notice_ref}</span>
              </div>
              <h1 className="font-display text-3xl lg:text-4xl mt-4 leading-tight text-brand-navy">{notice.title}</h1>

              <div className="mt-8 prose max-w-none">
                <div className="pmc-label">Scope of work</div>
                <p className="whitespace-pre-wrap text-brand-navy/85 text-[15px] leading-7 mt-2">{notice.description}</p>
              </div>

              {notice.primary_document && (
                <div className="mt-8" data-testid="notice-primary-document">
                  <div className="pmc-label">Tender / RFP / RFQ document</div>
                  <a href={`${process.env.REACT_APP_BACKEND_URL}${notice.primary_document.url}`}
                     target="_blank" rel="noreferrer"
                     data-testid="notice-primary-download"
                     className="mt-2 inline-flex items-center gap-2 px-4 py-3 border border-brand-navy text-brand-navy hover:bg-brand-navy hover:text-white transition-colors text-sm">
                    📄 <span>{notice.primary_document.file_name}</span>
                    <span className="text-xs text-brand-navy/50">
                      ({Math.round((notice.primary_document.size_bytes || 0) / 1024)} KB)
                    </span>
                  </a>
                </div>
              )}

              {notice.tender_template_id && (
                <div className="mt-8" data-testid="notice-composed-pdf">
                  <div className="pmc-label">Composed tender document</div>
                  <div className="mt-2 flex flex-wrap items-center gap-3">
                    <span className="text-[10px] uppercase tracking-widest text-brand-navy/60">Language:</span>
                    {["en", "ru", "kk"].map((lg) => (
                      <a key={lg}
                         href={`${process.env.REACT_APP_BACKEND_URL}/api/v1/tender-templates/${notice.tender_template_id}/public/pdf?notice_ref=${encodeURIComponent(notice.notice_ref)}&lang=${lg}`}
                         data-testid={`notice-composed-download-${lg}`}
                         className={`inline-flex items-center gap-2 px-3 py-2 border text-[11px] uppercase tracking-widest ${lg === 'en' ? 'bg-brand-navy text-white border-brand-navy hover:bg-brand-navy-deep' : 'border-brand-navy/40 text-brand-navy hover:bg-brand-navy hover:text-white'}`}>
                        ⬇ PDF · {lg.toUpperCase()}
                      </a>
                    ))}
                    <a href={`${process.env.REACT_APP_BACKEND_URL}/api/v1/tender-templates/${notice.tender_template_id}/public/zip?notice_ref=${encodeURIComponent(notice.notice_ref)}`}
                       data-testid="notice-composed-zip"
                       className="inline-flex items-center gap-2 px-3 py-2 text-[11px] uppercase tracking-widest border border-brand-navy text-brand-navy hover:bg-brand-navy hover:text-white">
                      🗂 all docs (.zip)
                    </a>
                  </div>
                  <div className="mt-1 text-[11px] text-brand-navy/50">
                    Rendered live from the Tender Builder — includes every annexure and template attachment.
                    Static labels are translated; bodies remain in the language the admin wrote them.
                  </div>
                </div>
              )}

              {notice.attachments?.length > 0 && (
                <div className="mt-8">
                  <div className="pmc-label">{t("notice.attachments")} ({notice.attachments.length})</div>
                  <ul className="mt-2 text-sm text-brand-navy-soft space-y-1">
                    {notice.attachments.map((a, i) => {
                      const href = a.url ? `${process.env.REACT_APP_BACKEND_URL}${a.url}` : "#";
                      const label = a.file_name || a.name || a.key || "attachment";
                      const sizeKb = a.size_bytes ? ` (${Math.round(a.size_bytes / 1024)} KB)` : "";
                      return (
                        <li key={a.key || a.url || i} data-testid={`attachment-${i}`}>
                          <a href={href} target="_blank" rel="noreferrer" className="hover:underline">
                            → {label}<span className="text-brand-navy/40">{sizeKb}</span>
                          </a>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}
            </article>

            <aside className="bg-white border border-brand-navy/10 p-6 lg:p-8 lg:sticky lg:top-6">
              <div className="pmc-label">Key details</div>
              <DetailField label={t("notice.category")} value={notice.category} />
              <DetailField label={t("notice.country")} value={notice.delivery_country} />
              <DetailField label={t("notice.budget")} value={budget} mono />
              <DetailField label={t("notice.submission_deadline")} value={deadline?.toISOString().replace("T", " ").slice(0, 16)} mono />
              <DetailField label={t("notice.pre_bid")} value={preBid?.toISOString().replace("T", " ").slice(0, 16)} mono />
              <DetailField label={t("notice.required_licenses")} value={notice.required_licenses?.join(", ")} />
              <DetailField label={t("notice.contact")} value={notice.contact_name} />
              <DetailField label="Contact email" value={notice.contact_email} mono />
              <DetailField label={t("notice.published_at")} value={publishedAt?.toISOString().slice(0, 10)} mono />

              <Link
                to="/register"
                data-testid="detail-cta-register"
                className="mt-8 block w-full text-center bg-brand-navy-soft text-white px-6 py-4 uppercase tracking-widest text-[0.8125rem] font-semibold hover:bg-brand-navy-soft/90 transition-colors"
              >
                {t("notice.register_to_bid")}
              </Link>
            </aside>
          </div>
        )}
        {notice && <NoticeQa noticeRef={notice.notice_ref} />}
      </main>
      <Footer />
    </div>
  );
}
