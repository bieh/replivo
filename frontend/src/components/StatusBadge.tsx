const statusStyles: Record<string, string> = {
  draft_ready: 'bg-blue-100 text-blue-800',
  needs_human: 'bg-yellow-100 text-yellow-800',
  pending_review: 'bg-gray-100 text-gray-800',
  replied: 'bg-green-100 text-green-800',
  auto_replied: 'bg-emerald-100 text-emerald-800',
  closed: 'bg-gray-100 text-gray-500',
};

const statusLabels: Record<string, string> = {
  draft_ready: 'Draft Ready',
  needs_human: 'Needs Human',
  pending_review: 'Pending',
  replied: 'Replied',
  auto_replied: 'Auto-Replied',
  closed: 'Closed',
};

export default function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
        statusStyles[status] || 'bg-gray-100 text-gray-800'
      }`}
    >
      {statusLabels[status] || status}
    </span>
  );
}
