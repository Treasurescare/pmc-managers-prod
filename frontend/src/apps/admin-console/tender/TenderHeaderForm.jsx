/**
 * TenderHeaderForm — CPPP-style structured "front matter" for a tender.
 * Mirrors the Indian government e-Procurement portal layout the client shared:
 *   Basic Details · Cover Details · Fee & EMD · Work/Item · Critical Dates
 *   · Tender Documents · Inviting Authority.
 * All fields stream into `header` on the parent tender doc — no backend change.
 */

// tiny local primitives to keep the parent lean and match the CPPP density
function Group({ title, children, testid }) {
  return (
    <section className="border border-brand-navy/20 bg-white mb-5" data-testid={testid}>
      <header className="bg-brand-pale/70 border-b border-brand-navy/20 px-4 py-2">
        <strong className="text-brand-navy text-sm">{title}</strong>
      </header>
      <div className="p-4">{children}</div>
    </section>
  );
}

function Row({ label, children, testid }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] border-t border-brand-navy/10 first:border-t-0"
         data-testid={testid}>
      <div className="bg-brand-pale/40 px-3 py-2 text-xs uppercase tracking-wider text-brand-navy/70 border-r border-brand-navy/10">
        {label}
      </div>
      <div className="px-3 py-2 text-sm text-brand-navy">{children}</div>
    </div>
  );
}

function Text({ value, onChange, type = "text", testid, placeholder }) {
  return (
    <input type={type} value={value ?? ""} placeholder={placeholder}
      onChange={(e) => onChange(type === "number" ? Number(e.target.value) : e.target.value)}
      data-testid={testid}
      className="w-full px-2 py-1.5 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft bg-white text-sm" />
  );
}

function YesNo({ value, onChange, testid }) {
  return (
    <select value={value ? "yes" : "no"} onChange={(e) => onChange(e.target.value === "yes")}
      data-testid={testid}
      className="w-32 px-2 py-1.5 border border-brand-navy/20 bg-white text-sm">
      <option value="yes">Yes</option><option value="no">No</option>
    </select>
  );
}

export default function TenderHeaderForm({ header, patchHeader }) {
  const h = header || {};

  const covers = h.covers || [
    { cover_no: 1, name: "Fee/PreQual/Technical", doc_type: ".pdf", description: "Bid declaration for EMD" },
    { cover_no: 1, name: "",                       doc_type: ".pdf", description: "Technical bid documents" },
    { cover_no: 2, name: "Finance",                doc_type: ".xls", description: "Financial bid" },
  ];
  const nitDocs = h.nit_documents || [];
  const workItemDocs = h.work_item_documents || [];

  const patchCover = (idx, next) => {
    const arr = [...covers];
    arr[idx] = { ...arr[idx], ...next };
    patchHeader({ covers: arr });
  };
  const addCover = () => patchHeader({ covers: [...covers, { cover_no: covers.length + 1, name: "", doc_type: ".pdf", description: "" }] });
  const rmCover = (idx) => {
    const arr = [...covers]; arr.splice(idx, 1); patchHeader({ covers: arr });
  };

  const patchNit = (idx, next) => {
    const arr = [...nitDocs]; arr[idx] = { ...arr[idx], ...next }; patchHeader({ nit_documents: arr });
  };
  const addNit = () => patchHeader({ nit_documents: [...nitDocs, { document_name: "", description: "", size_kb: 0 }] });
  const rmNit = (idx) => { const arr = [...nitDocs]; arr.splice(idx, 1); patchHeader({ nit_documents: arr }); };

  const patchWid = (idx, next) => {
    const arr = [...workItemDocs]; arr[idx] = { ...arr[idx], ...next }; patchHeader({ work_item_documents: arr });
  };
  const addWid = () => patchHeader({ work_item_documents: [...workItemDocs, { document_type: "", document_name: "", description: "", size_kb: 0 }] });
  const rmWid = (idx) => { const arr = [...workItemDocs]; arr.splice(idx, 1); patchHeader({ work_item_documents: arr }); };

  return (
    <div data-testid="tender-header-form">
      <Group title="Basic Details" testid="th-basic-details">
        <Row label="Organisation Chain">
          <Text value={h.organisation_chain} onChange={(v) => patchHeader({ organisation_chain: v })}
            placeholder="e.g. Employees State Insurance Corporation||ESIC Hqrs. Office - New Delhi"
            testid="th-org-chain" />
        </Row>
        <Row label="Tender Reference Number">
          <Text value={h.tender_reference_number} onChange={(v) => patchHeader({ tender_reference_number: v })}
            testid="th-ref-number" />
        </Row>
        <div className="grid md:grid-cols-2 gap-0">
          <Row label="Tender ID">
            <Text value={h.tender_id} onChange={(v) => patchHeader({ tender_id: v })} testid="th-tender-id" />
          </Row>
          <Row label="Withdrawal Allowed">
            <YesNo value={h.withdrawal_allowed ?? true} onChange={(v) => patchHeader({ withdrawal_allowed: v })} testid="th-withdrawal" />
          </Row>
          <Row label="Tender Type">
            <select value={h.tender_type || "Open Tender"}
              onChange={(e) => patchHeader({ tender_type: e.target.value })}
              data-testid="th-tender-type"
              className="w-full px-2 py-1.5 border border-brand-navy/20 bg-white text-sm">
              {["Open Tender", "Limited", "EOI", "Global", "Single Source", "RFQ", "RFP"].map((x) => <option key={x}>{x}</option>)}
            </select>
          </Row>
          <Row label="Form of contract">
            <select value={h.form_of_contract || "EOI"}
              onChange={(e) => patchHeader({ form_of_contract: e.target.value })}
              data-testid="th-form-of-contract"
              className="w-full px-2 py-1.5 border border-brand-navy/20 bg-white text-sm">
              {["EOI", "Item Rate", "Percentage", "Lump-Sum", "Fixed Rate", "Piecework"].map((x) => <option key={x}>{x}</option>)}
            </select>
          </Row>
          <Row label="Tender Category">
            <select value={h.tender_category || "Works"}
              onChange={(e) => patchHeader({ tender_category: e.target.value })}
              data-testid="th-tender-category"
              className="w-full px-2 py-1.5 border border-brand-navy/20 bg-white text-sm">
              {["Works", "Goods", "Services"].map((x) => <option key={x}>{x}</option>)}
            </select>
          </Row>
          <Row label="No. of Covers">
            <Text type="number" value={h.no_of_covers ?? 2} onChange={(v) => patchHeader({ no_of_covers: v })} testid="th-covers" />
          </Row>
          <Row label="General Technical Evaluation Allowed">
            <YesNo value={h.general_technical_eval ?? false} onChange={(v) => patchHeader({ general_technical_eval: v })} testid="th-gen-tech" />
          </Row>
          <Row label="ItemWise Technical Evaluation Allowed">
            <YesNo value={h.itemwise_technical_eval ?? false} onChange={(v) => patchHeader({ itemwise_technical_eval: v })} testid="th-item-tech" />
          </Row>
          <Row label="Payment Mode">
            <Text value={h.payment_mode || "Not Applicable"} onChange={(v) => patchHeader({ payment_mode: v })} testid="th-payment-mode" />
          </Row>
          <Row label="Is Multi Currency Allowed For BOQ">
            <YesNo value={h.multi_currency_boq ?? false} onChange={(v) => patchHeader({ multi_currency_boq: v })} testid="th-multicur-boq" />
          </Row>
          <Row label="Is Multi Currency Allowed For Fee">
            <YesNo value={h.multi_currency_fee ?? false} onChange={(v) => patchHeader({ multi_currency_fee: v })} testid="th-multicur-fee" />
          </Row>
          <Row label="Allow Two Stage Bidding">
            <YesNo value={h.two_stage_bidding ?? false} onChange={(v) => patchHeader({ two_stage_bidding: v })} testid="th-two-stage" />
          </Row>
        </div>
      </Group>

      <Group title={`Cover Details, No. Of Covers - ${h.no_of_covers ?? covers.length}`} testid="th-cover-details">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs uppercase tracking-wider text-brand-navy/70 border-b border-brand-navy/10">
              <th className="text-left px-2 py-1 w-24">Cover No</th>
              <th className="text-left px-2 py-1">Cover</th>
              <th className="text-left px-2 py-1 w-32">Document Type</th>
              <th className="text-left px-2 py-1">Description</th>
              <th className="w-10" />
            </tr>
          </thead>
          <tbody>
            {covers.map((c, i) => (
              <tr key={`cover-${i}`} className="border-b border-brand-navy/10" data-testid={`th-cover-row-${i}`}>
                <td className="px-2 py-1"><Text type="number" value={c.cover_no} onChange={(v) => patchCover(i, { cover_no: v })} testid={`th-cover-no-${i}`} /></td>
                <td className="px-2 py-1"><Text value={c.name} onChange={(v) => patchCover(i, { name: v })} testid={`th-cover-name-${i}`} /></td>
                <td className="px-2 py-1"><Text value={c.doc_type} onChange={(v) => patchCover(i, { doc_type: v })} testid={`th-cover-doctype-${i}`} /></td>
                <td className="px-2 py-1"><Text value={c.description} onChange={(v) => patchCover(i, { description: v })} testid={`th-cover-desc-${i}`} /></td>
                <td className="px-2 py-1 text-center">
                  <button type="button" onClick={() => rmCover(i)} data-testid={`th-cover-del-${i}`}
                    className="text-xs text-red-600">×</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <button type="button" onClick={addCover} data-testid="th-cover-add"
          className="mt-2 px-3 py-1.5 text-[11px] uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-navy/5">
          + Add cover row
        </button>
      </Group>

      <div className="grid gap-5 md:grid-cols-2">
        <Group title={`Tender Fee Details [Total Fee in ₹ - ${(h.tender_fee_amount || 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}]`} testid="th-fee">
          <Row label="Tender Fee in ₹">
            <Text type="number" value={h.tender_fee_amount} onChange={(v) => patchHeader({ tender_fee_amount: v })} testid="th-fee-amount" />
          </Row>
          <Row label="Fee Payable To">
            <Text value={h.fee_payable_to} onChange={(v) => patchHeader({ fee_payable_to: v })} testid="th-fee-payable-to" />
          </Row>
          <Row label="Fee Payable At">
            <Text value={h.fee_payable_at} onChange={(v) => patchHeader({ fee_payable_at: v })} testid="th-fee-payable-at" />
          </Row>
          <Row label="Tender Fee Exemption Allowed">
            <YesNo value={h.fee_exemption ?? false} onChange={(v) => patchHeader({ fee_exemption: v })} testid="th-fee-exemption" />
          </Row>
        </Group>
        <Group title="EMD Fee Details" testid="th-emd">
          <Row label="EMD Amount in ₹">
            <Text type="number" value={h.emd_amount} onChange={(v) => patchHeader({ emd_amount: v })} testid="th-emd-amount" />
          </Row>
          <Row label="EMD Exemption Allowed">
            <YesNo value={h.emd_exemption ?? false} onChange={(v) => patchHeader({ emd_exemption: v })} testid="th-emd-exemption" />
          </Row>
          <Row label="EMD Fee Type">
            <select value={h.emd_type || "fixed"} onChange={(e) => patchHeader({ emd_type: e.target.value })}
              data-testid="th-emd-type"
              className="w-full px-2 py-1.5 border border-brand-navy/20 bg-white text-sm">
              {["fixed", "percentage"].map((x) => <option key={x}>{x}</option>)}
            </select>
          </Row>
          <Row label="EMD Percentage">
            <Text value={h.emd_percentage || "NA"} onChange={(v) => patchHeader({ emd_percentage: v })} testid="th-emd-pct" />
          </Row>
          <Row label="EMD Payable To">
            <Text value={h.emd_payable_to} onChange={(v) => patchHeader({ emd_payable_to: v })} testid="th-emd-to" />
          </Row>
          <Row label="EMD Payable At">
            <Text value={h.emd_payable_at} onChange={(v) => patchHeader({ emd_payable_at: v })} testid="th-emd-at" />
          </Row>
        </Group>
      </div>

      <Group title="Work / Item(s)" testid="th-work">
        <Row label="Title">
          <Text value={h.work_title} onChange={(v) => patchHeader({ work_title: v })} testid="th-work-title" />
        </Row>
        <Row label="Work Description">
          <textarea value={h.work_description || ""} onChange={(e) => patchHeader({ work_description: e.target.value })}
            rows={3} data-testid="th-work-desc"
            className="w-full px-2 py-1.5 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft bg-white text-sm" />
        </Row>
        <Row label="Pre Qualification Details">
          <Text value={h.pre_qual_details} onChange={(v) => patchHeader({ pre_qual_details: v })} testid="th-preq" />
        </Row>
        <Row label="Independent External Monitor / Remarks">
          <Text value={h.independent_monitor} onChange={(v) => patchHeader({ independent_monitor: v })} testid="th-monitor" />
        </Row>
        <div className="grid md:grid-cols-2">
          <Row label="Tender Value in ₹">
            <Text type="number" value={h.tender_value} onChange={(v) => patchHeader({ tender_value: v })} testid="th-value" />
          </Row>
          <Row label="Product Category">
            <Text value={h.product_category} onChange={(v) => patchHeader({ product_category: v })} testid="th-prod-cat" />
          </Row>
          <Row label="Sub category">
            <Text value={h.sub_category} onChange={(v) => patchHeader({ sub_category: v })} testid="th-sub-cat" />
          </Row>
          <Row label="Contract Type">
            <Text value={h.contract_type} onChange={(v) => patchHeader({ contract_type: v })} testid="th-contract-type" />
          </Row>
          <Row label="Bid Validity (Days)">
            <Text type="number" value={h.bid_validity_days} onChange={(v) => patchHeader({ bid_validity_days: v })} testid="th-validity" />
          </Row>
          <Row label="Period Of Work (Days)">
            <Text type="number" value={h.period_days} onChange={(v) => patchHeader({ period_days: v })} testid="th-period" />
          </Row>
          <Row label="Location">
            <Text value={h.location} onChange={(v) => patchHeader({ location: v })} testid="th-location" />
          </Row>
          <Row label="Pincode">
            <Text value={h.pincode} onChange={(v) => patchHeader({ pincode: v })} testid="th-pincode" />
          </Row>
          <Row label="Pre Bid Meeting Place">
            <Text value={h.pre_bid_place} onChange={(v) => patchHeader({ pre_bid_place: v })} testid="th-prebid-place" />
          </Row>
          <Row label="Pre Bid Meeting Date">
            <Text type="datetime-local" value={h.pre_bid_date} onChange={(v) => patchHeader({ pre_bid_date: v })} testid="th-prebid-date" />
          </Row>
          <Row label="Pre Bid Meeting Address">
            <Text value={h.pre_bid_address} onChange={(v) => patchHeader({ pre_bid_address: v })} testid="th-prebid-addr" />
          </Row>
          <Row label="Bid Opening Place">
            <Text value={h.bid_opening_place} onChange={(v) => patchHeader({ bid_opening_place: v })} testid="th-open-place" />
          </Row>
          <Row label="Should Allow NDA Tender">
            <YesNo value={h.allow_nda ?? false} onChange={(v) => patchHeader({ allow_nda: v })} testid="th-nda" />
          </Row>
          <Row label="Allow Preferential Bidder">
            <YesNo value={h.allow_preferential ?? false} onChange={(v) => patchHeader({ allow_preferential: v })} testid="th-preferential" />
          </Row>
        </div>
      </Group>

      <Group title="Critical Dates" testid="th-dates">
        <div className="grid md:grid-cols-2">
          <Row label="Publish Date">
            <Text type="datetime-local" value={h.publish_date} onChange={(v) => patchHeader({ publish_date: v })} testid="th-publish" />
          </Row>
          <Row label="Bid Opening Date">
            <Text type="datetime-local" value={h.bid_opening_date} onChange={(v) => patchHeader({ bid_opening_date: v })} testid="th-opening" />
          </Row>
          <Row label="Document Download / Sale Start Date">
            <Text type="datetime-local" value={h.doc_dl_start} onChange={(v) => patchHeader({ doc_dl_start: v })} testid="th-dl-start" />
          </Row>
          <Row label="Document Download / Sale End Date">
            <Text type="datetime-local" value={h.doc_dl_end} onChange={(v) => patchHeader({ doc_dl_end: v })} testid="th-dl-end" />
          </Row>
          <Row label="Clarification Start Date">
            <Text type="datetime-local" value={h.clarif_start} onChange={(v) => patchHeader({ clarif_start: v })} testid="th-clarif-start" />
          </Row>
          <Row label="Clarification End Date">
            <Text type="datetime-local" value={h.clarif_end} onChange={(v) => patchHeader({ clarif_end: v })} testid="th-clarif-end" />
          </Row>
          <Row label="Bid Submission Start Date">
            <Text type="datetime-local" value={h.sub_start} onChange={(v) => patchHeader({ sub_start: v })} testid="th-sub-start" />
          </Row>
          <Row label="Bid Submission End Date">
            <Text type="datetime-local" value={h.sub_end} onChange={(v) => patchHeader({ sub_end: v })} testid="th-sub-end" />
          </Row>
        </div>
      </Group>

      <Group title="Tender Documents" testid="th-docs">
        <div className="mb-4">
          <div className="text-xs uppercase tracking-wider text-brand-navy/70 mb-2">NIT Document</div>
          <table className="w-full text-sm">
            <thead><tr className="text-xs text-brand-navy/60">
              <th className="text-left px-2 w-12">S.No</th>
              <th className="text-left px-2">Document Name</th>
              <th className="text-left px-2">Description</th>
              <th className="text-right px-2 w-28">Size (KB)</th>
              <th className="w-10" />
            </tr></thead>
            <tbody>
              {nitDocs.map((d, i) => (
                <tr key={`nit-${i}`} className="border-t border-brand-navy/10" data-testid={`th-nit-row-${i}`}>
                  <td className="px-2 py-1">{i + 1}</td>
                  <td className="px-2 py-1"><Text value={d.document_name} onChange={(v) => patchNit(i, { document_name: v })} testid={`th-nit-name-${i}`} /></td>
                  <td className="px-2 py-1"><Text value={d.description} onChange={(v) => patchNit(i, { description: v })} testid={`th-nit-desc-${i}`} /></td>
                  <td className="px-2 py-1"><Text type="number" value={d.size_kb} onChange={(v) => patchNit(i, { size_kb: v })} testid={`th-nit-size-${i}`} /></td>
                  <td className="px-2 py-1 text-center">
                    <button type="button" onClick={() => rmNit(i)} className="text-xs text-red-600">×</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <button type="button" onClick={addNit} data-testid="th-nit-add"
            className="mt-2 px-3 py-1.5 text-[11px] uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-navy/5">
            + Add NIT document
          </button>
        </div>
        <div>
          <div className="text-xs uppercase tracking-wider text-brand-navy/70 mb-2">Work Item Documents</div>
          <table className="w-full text-sm">
            <thead><tr className="text-xs text-brand-navy/60">
              <th className="text-left px-2 w-12">S.No</th>
              <th className="text-left px-2">Document Type</th>
              <th className="text-left px-2">Document Name</th>
              <th className="text-left px-2">Description</th>
              <th className="text-right px-2 w-28">Size (KB)</th>
              <th className="w-10" />
            </tr></thead>
            <tbody>
              {workItemDocs.map((d, i) => (
                <tr key={`wid-${i}`} className="border-t border-brand-navy/10" data-testid={`th-wid-row-${i}`}>
                  <td className="px-2 py-1">{i + 1}</td>
                  <td className="px-2 py-1"><Text value={d.document_type} onChange={(v) => patchWid(i, { document_type: v })} testid={`th-wid-type-${i}`} /></td>
                  <td className="px-2 py-1"><Text value={d.document_name} onChange={(v) => patchWid(i, { document_name: v })} testid={`th-wid-name-${i}`} /></td>
                  <td className="px-2 py-1"><Text value={d.description} onChange={(v) => patchWid(i, { description: v })} testid={`th-wid-desc-${i}`} /></td>
                  <td className="px-2 py-1"><Text type="number" value={d.size_kb} onChange={(v) => patchWid(i, { size_kb: v })} testid={`th-wid-size-${i}`} /></td>
                  <td className="px-2 py-1 text-center">
                    <button type="button" onClick={() => rmWid(i)} className="text-xs text-red-600">×</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <button type="button" onClick={addWid} data-testid="th-wid-add"
            className="mt-2 px-3 py-1.5 text-[11px] uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-navy/5">
            + Add Work Item document
          </button>
        </div>
      </Group>

      <Group title="Tender Inviting Authority" testid="th-authority">
        <Row label="Name">
          <Text value={h.authority_name} onChange={(v) => patchHeader({ authority_name: v })} testid="th-auth-name" />
        </Row>
        <Row label="Address">
          <textarea value={h.authority_address || ""} onChange={(e) => patchHeader({ authority_address: e.target.value })}
            rows={2} data-testid="th-auth-address"
            className="w-full px-2 py-1.5 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft bg-white text-sm" />
        </Row>
      </Group>
    </div>
  );
}
