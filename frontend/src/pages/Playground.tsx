import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getCommunities, playgroundAsk } from '../api/client';
import type { Community, Citation } from '../types';
import Markdown from '../components/Markdown';

interface HistoryEntry {
  role: string;
  text: string;
}

export default function Playground() {
  const [communityId, setCommunityId] = useState('');
  const [question, setQuestion] = useState('');
  const [showReasoning, setShowReasoning] = useState(false);
  const [conversationHistory, setConversationHistory] = useState<HistoryEntry[]>([]);

  const { data: communities } = useQuery<Community[]>({
    queryKey: ['communities'],
    queryFn: () => getCommunities().then((r) => r.data),
  });

  const hasHistory = conversationHistory.length > 0;

  const askMutation = useMutation({
    mutationFn: () => playgroundAsk(
      communityId,
      question,
      hasHistory ? conversationHistory : undefined,
    ),
    onSuccess: (res) => {
      const answer = res.data?.answer_text || '';
      setConversationHistory((prev) => [
        ...prev,
        { role: 'tenant', text: question },
        { role: 'replivo', text: answer },
      ]);
      setQuestion('');
    },
  });

  const result = askMutation.data?.data;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (communityId && question.trim()) {
      askMutation.mutate();
    }
  };

  const handleNewConversation = () => {
    setConversationHistory([]);
    setQuestion('');
    askMutation.reset();
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Playground</h1>
      <p className="text-sm text-gray-500 mb-6">
        Test the AI pipeline against any community's documents. No emails are sent.
      </p>

      {/* Conversation Thread */}
      {hasHistory && (
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="flex items-center justify-between px-6 py-3 border-b border-gray-100">
            <h2 className="text-sm font-medium text-gray-900">Conversation Thread</h2>
            <button
              onClick={handleNewConversation}
              className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
            >
              New Conversation
            </button>
          </div>
          <div className="p-6 space-y-3">
            {conversationHistory.map((entry, i) => (
              <div
                key={i}
                className={`text-sm p-3 rounded-lg ${
                  entry.role === 'tenant'
                    ? 'bg-gray-50 border-l-4 border-gray-300'
                    : 'bg-indigo-50 border-l-4 border-indigo-400'
                }`}
              >
                <span className="font-medium text-gray-700 text-xs uppercase tracking-wide">
                  {entry.role === 'tenant' ? 'Tenant' : 'Replivo AI'}
                </span>
                <Markdown className="mt-1">{entry.text}</Markdown>
              </div>
            ))}
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6 mb-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Community</label>
          <select
            value={communityId}
            onChange={(e) => setCommunityId(e.target.value)}
            disabled={hasHistory}
            className="w-full border border-gray-300 rounded-md p-2 text-sm disabled:bg-gray-100 disabled:text-gray-500"
          >
            <option value="">Select a community...</option>
            {communities?.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {hasHistory ? 'Follow-up Question' : 'Question'}
          </label>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            rows={3}
            placeholder={hasHistory ? 'e.g. What colors are approved?' : 'e.g. Can I paint my house?'}
            className="w-full border border-gray-300 rounded-md p-3 text-sm"
          />
        </div>
        <button
          type="submit"
          disabled={!communityId || !question.trim() || askMutation.isPending}
          className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700 disabled:opacity-50"
        >
          {askMutation.isPending ? 'Running pipeline...' : hasHistory ? 'Follow up' : 'Ask'}
        </button>
      </form>

      {askMutation.isPending && (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-r-transparent mb-3" />
          <p className="text-sm text-gray-500">Running AI pipeline... this can take 5-15 seconds.</p>
        </div>
      )}

      {askMutation.isError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-sm text-red-700">Error: {(askMutation.error as any)?.response?.data?.error || 'Something went wrong'}</p>
        </div>
      )}

      {result && !askMutation.isPending && (
        <div className="grid grid-cols-3 gap-6">
          {/* Main Result */}
          <div className="col-span-2 space-y-4">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center gap-3 mb-4">
                <h2 className="text-lg font-semibold text-gray-900">AI Response</h2>
                {result.status === 'draft_ready' ? (
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full font-medium">Draft Ready</span>
                ) : (
                  <span className="text-xs bg-amber-100 text-amber-700 px-2 py-1 rounded-full font-medium">Needs Human</span>
                )}
              </div>
              <Markdown>{result.answer_text}</Markdown>
            </div>

            {/* Citations */}
            {result.citations && result.citations.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-sm font-medium text-gray-900 mb-3">Citations</h3>
                <ul className="space-y-3">
                  {result.citations.map((cit: Citation, i: number) => (
                    <li key={i} className="text-sm border-l-2 border-indigo-200 pl-3">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-indigo-700">{cit.section_reference}</span>
                        {cit.verified ? (
                          <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">Verified</span>
                        ) : (
                          <span className="text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded">Unverified</span>
                        )}
                        {cit.confidence && (
                          <span className="text-xs text-gray-400">{cit.confidence}</span>
                        )}
                      </div>
                      <p className="text-gray-600 mt-1">{cit.claim_text}</p>
                      {cit.source_quote && (
                        <p className="text-gray-400 mt-1 text-xs italic">"{cit.source_quote.substring(0, 200)}..."</p>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Reasoning (expandable) */}
            {result.raw_response?.reasoning && (
              <div className="bg-white rounded-lg shadow p-6">
                <button
                  onClick={() => setShowReasoning(!showReasoning)}
                  className="flex items-center gap-2 text-sm font-medium text-gray-900"
                >
                  <span>{showReasoning ? '▼' : '▶'}</span>
                  Reasoning (Chain of Thought)
                </button>
                {showReasoning && (
                  <pre className="mt-3 text-xs text-gray-600 whitespace-pre-wrap bg-gray-50 rounded p-3">
                    {result.raw_response.reasoning}
                  </pre>
                )}
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            <div className="bg-white rounded-lg shadow p-4">
              <h3 className="text-sm font-medium text-gray-900 mb-3">AI Analysis</h3>
              <dl className="space-y-2 text-sm">
                <div>
                  <dt className="text-gray-500">Answer Type</dt>
                  <dd className="text-gray-900">{result.raw_response?.answer_type || '—'}</dd>
                </div>
                <div>
                  <dt className="text-gray-500">Confidence</dt>
                  <dd className="text-gray-900">{result.raw_response?.overall_confidence || '—'}</dd>
                </div>
                {result.escalation_reason && (
                  <div>
                    <dt className="text-gray-500">Escalation Reason</dt>
                    <dd className="text-red-700">{result.escalation_reason}</dd>
                  </div>
                )}
                {result.raw_response?.sections_reviewed?.length > 0 && (
                  <div>
                    <dt className="text-gray-500">Sections Reviewed</dt>
                    <dd className="text-gray-900">{result.raw_response.sections_reviewed.join(', ')}</dd>
                  </div>
                )}
              </dl>
            </div>

            <div className="bg-white rounded-lg shadow p-4">
              <h3 className="text-sm font-medium text-gray-900 mb-3">Pipeline Status</h3>
              <dl className="space-y-2 text-sm">
                <div>
                  <dt className="text-gray-500">Status</dt>
                  <dd className="text-gray-900">{result.status}</dd>
                </div>
                <div>
                  <dt className="text-gray-500">Citations</dt>
                  <dd className="text-gray-900">{result.citations?.length || 0} total</dd>
                </div>
                <div>
                  <dt className="text-gray-500">Verified</dt>
                  <dd className="text-gray-900">
                    {result.citations?.filter((c: Citation) => c.verified).length || 0} / {result.citations?.length || 0}
                  </dd>
                </div>
              </dl>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
