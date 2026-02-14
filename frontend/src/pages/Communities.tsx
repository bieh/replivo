import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { getCommunities } from '../api/client';
import type { Community } from '../types';

export default function Communities() {
  const { data: communities, isLoading } = useQuery<Community[]>({
    queryKey: ['communities'],
    queryFn: () => getCommunities().then((r) => r.data),
  });

  if (isLoading) return <div className="text-gray-500">Loading...</div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Communities</h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {communities?.map((c) => (
          <Link
            key={c.id}
            to={`/communities/${c.id}`}
            className="bg-white rounded-lg shadow p-6 hover:shadow-md transition-shadow"
          >
            <h3 className="text-lg font-semibold text-gray-900">{c.name}</h3>
            <p className="text-sm text-gray-500 mt-1">{c.description || c.slug}</p>
            <div className="mt-4 flex gap-4 text-sm text-gray-600">
              <span>{c.tenant_count} tenants</span>
              <span>{c.document_count} documents</span>
            </div>
            {c.settings?.auto_reply_enabled && (
              <span className="mt-2 inline-block text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded">
                Auto-reply ON
              </span>
            )}
          </Link>
        ))}
      </div>

      {(!communities || communities.length === 0) && (
        <div className="text-center py-12 text-gray-500">
          No communities yet. Run <code>cli seed</code> to create sample data.
        </div>
      )}
    </div>
  );
}
