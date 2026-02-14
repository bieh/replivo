import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { getDashboardStats } from '../api/client';
import type { DashboardStats } from '../types';
import StatusBadge from '../components/StatusBadge';

export default function Dashboard() {
  const { data: stats, isLoading } = useQuery<DashboardStats>({
    queryKey: ['dashboard'],
    queryFn: () => getDashboardStats().then((r) => r.data),
    refetchInterval: 10000,
  });

  if (isLoading) return <div className="text-gray-500">Loading...</div>;

  const counts = stats?.status_counts || {};

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Needs Attention" value={stats?.needs_attention || 0} color="yellow" />
        <StatCard label="Draft Ready" value={counts.draft_ready || 0} color="blue" />
        <StatCard label="Needs Human" value={counts.needs_human || 0} color="red" />
        <StatCard label="Replied" value={(counts.replied || 0) + (counts.auto_replied || 0)} color="green" />
      </div>

      {stats?.inboxes && stats.inboxes.length > 0 && (
        <div className="bg-white rounded-lg shadow mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Inbox Addresses</h2>
            <p className="text-sm text-gray-500 mt-1">Tenants send emails to these addresses to start a conversation.</p>
          </div>
          <ul className="divide-y divide-gray-200">
            {stats.inboxes.map((inbox) => (
              <li key={inbox.inbox_email} className="px-6 py-3 flex items-center justify-between">
                <span className="text-sm text-gray-700">{inbox.community_name}</span>
                <code className="text-sm bg-gray-100 text-gray-900 px-3 py-1 rounded font-mono">{inbox.inbox_email}</code>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">Recent Conversations Needing Attention</h2>
        </div>
        {stats?.recent && stats.recent.length > 0 ? (
          <ul className="divide-y divide-gray-200">
            {stats.recent.map((conv) => (
              <li key={conv.id}>
                <Link
                  to={`/conversations/${conv.id}`}
                  className="block px-6 py-4 hover:bg-gray-50"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{conv.subject || '(no subject)'}</p>
                      <p className="text-sm text-gray-500">{conv.sender_email}</p>
                    </div>
                    <StatusBadge status={conv.status} />
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <div className="px-6 py-8 text-center text-gray-500">
            No conversations needing attention. All caught up!
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  const colors: Record<string, string> = {
    yellow: 'bg-yellow-50 text-yellow-800 border-yellow-200',
    blue: 'bg-blue-50 text-blue-800 border-blue-200',
    red: 'bg-red-50 text-red-800 border-red-200',
    green: 'bg-green-50 text-green-800 border-green-200',
  };
  return (
    <div className={`rounded-lg border p-4 ${colors[color]}`}>
      <p className="text-sm font-medium">{label}</p>
      <p className="text-3xl font-bold mt-1">{value}</p>
    </div>
  );
}
