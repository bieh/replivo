import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { getConversations, getCommunities } from '../api/client';
import type { Conversation, Community } from '../types';
import StatusBadge from '../components/StatusBadge';

export default function Conversations() {
  const [statusFilter, setStatusFilter] = useState('');
  const [communityFilter, setCommunityFilter] = useState('');

  const { data: conversations, isLoading } = useQuery<Conversation[]>({
    queryKey: ['conversations', statusFilter, communityFilter],
    queryFn: () =>
      getConversations({
        status: statusFilter || undefined,
        community_id: communityFilter || undefined,
      }).then((r) => r.data),
    refetchInterval: 5000,
  });

  const { data: communities } = useQuery<Community[]>({
    queryKey: ['communities'],
    queryFn: () => getCommunities().then((r) => r.data),
  });

  const statuses = [
    { value: '', label: 'All' },
    { value: 'draft_ready', label: 'Draft Ready' },
    { value: 'needs_human', label: 'Needs Human' },
    { value: 'replied', label: 'Replied' },
    { value: 'auto_replied', label: 'Auto-Replied' },
    { value: 'closed', label: 'Closed' },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Conversations</h1>

      <div className="flex gap-3 mb-4">
        <div className="flex gap-1">
          {statuses.map((s) => (
            <button
              key={s.value}
              onClick={() => setStatusFilter(s.value)}
              className={`px-3 py-1.5 text-sm rounded-md ${
                statusFilter === s.value
                  ? 'bg-indigo-100 text-indigo-700 font-medium'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
        <select
          value={communityFilter}
          onChange={(e) => setCommunityFilter(e.target.value)}
          className="text-sm border border-gray-300 rounded-md px-2 py-1.5"
        >
          <option value="">All Communities</option>
          {communities?.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <div className="text-gray-500">Loading...</div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          {conversations && conversations.length > 0 ? (
            <ul className="divide-y divide-gray-200">
              {conversations.map((conv) => (
                <li key={conv.id}>
                  <Link
                    to={`/conversations/${conv.id}`}
                    className="block px-6 py-4 hover:bg-gray-50"
                  >
                    <div className="flex items-center justify-between">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-3">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {conv.subject || '(no subject)'}
                          </p>
                          <StatusBadge status={conv.status} />
                        </div>
                        <div className="mt-1 flex items-center gap-3 text-sm text-gray-500">
                          <span>{conv.sender_email}</span>
                          {conv.community_name && (
                            <span className="text-gray-400">in {conv.community_name}</span>
                          )}
                        </div>
                        {conv.last_message_preview && (
                          <p className="mt-1 text-sm text-gray-400 truncate">
                            {conv.last_message_preview}
                          </p>
                        )}
                      </div>
                      <div className="ml-4 text-xs text-gray-400">
                        {new Date(conv.updated_at).toLocaleDateString()}
                      </div>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <div className="px-6 py-12 text-center text-gray-500">
              No conversations found.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
