/**
 * AssignCertifierModal — extracted from BiddingOpsPanel. Renders the modal
 * used by admins to assign a certifier + schedule the inspection.
 */
export default function AssignCertifierModal({ assignFor, certifiers, inspDraft, setInspDraft, onCancel, onSubmit }) {
  if (!assignFor) return null;
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      data-testid="assign-certifier-modal">
      <div className="bg-white rounded-lg p-6 max-w-md w-full space-y-4">
        <h3 className="text-lg font-serif">Assign certifier — {assignFor.bid_ref}</h3>
        <label className="block text-sm">
          <span>Certifier</span>
          <select value={inspDraft.certifier_id}
            onChange={(e) => setInspDraft({ ...inspDraft, certifier_id: e.target.value })}
            className="mt-1 w-full border rounded px-3 py-2 text-sm" data-testid="assign-cert-select">
            <option value="">Select…</option>
            {certifiers.map((c) => <option key={c.id} value={c.id}>{c.email}</option>)}
          </select>
        </label>
        <label className="block text-sm">
          <span>Scheduled site visit</span>
          <input type="datetime-local" value={inspDraft.scheduled_at}
            onChange={(e) => setInspDraft({ ...inspDraft, scheduled_at: e.target.value })}
            className="mt-1 w-full border rounded px-3 py-2 text-sm" data-testid="assign-cert-date" />
        </label>
        <label className="block text-sm">
          <span>Location</span>
          <input value={inspDraft.location}
            onChange={(e) => setInspDraft({ ...inspDraft, location: e.target.value })}
            className="mt-1 w-full border rounded px-3 py-2 text-sm" placeholder="Site address" />
        </label>
        <div className="flex justify-end gap-2">
          <button onClick={onCancel}
            className="px-4 py-2 text-sm border rounded">Cancel</button>
          <button onClick={onSubmit} data-testid="assign-cert-submit"
            className="px-4 py-2 text-sm bg-slate-900 text-white rounded">Assign</button>
        </div>
      </div>
    </div>
  );
}
