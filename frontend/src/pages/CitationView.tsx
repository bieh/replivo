import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getCitation } from '../api/client';
import Markdown from '../components/Markdown';

interface CitationData {
  question: string;
  subject: string;
  answer_text: string;
  citations: {
    claim_text: string;
    section_reference: string;
    source_quote: string;
    confidence: string;
    verified: boolean;
  }[];
  community_name: string;
}

export default function CitationView() {
  const { token } = useParams<{ token: string }>();

  const { data, isLoading, isError } = useQuery<CitationData>({
    queryKey: ['citation', token],
    queryFn: () => getCitation(token!).then((r) => r.data),
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Citation Not Found</h1>
          <p className="text-gray-500">This citation link may be invalid or expired.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-3xl mx-auto px-4 py-4">
          <span className="text-xl font-bold text-indigo-600">Replivo</span>
          {data.community_name && (
            <span className="ml-3 text-sm text-gray-400">{data.community_name}</span>
          )}
        </div>
      </header>

      {/* Content */}
      <main className="max-w-3xl mx-auto px-4 py-8">
        <h1 className="text-xl font-semibold text-gray-900 mb-6">
          Re: {data.subject}
        </h1>

        {/* Original Question */}
        {data.question && (
          <div className="mb-6">
            <h2 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Question</h2>
            <div className="bg-white rounded-lg border border-gray-200 p-4 text-sm text-gray-700 whitespace-pre-wrap">
              {data.question}
            </div>
          </div>
        )}

        {/* AI Answer */}
        <div className="mb-8">
          <h2 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Response</h2>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <Markdown>{data.answer_text}</Markdown>
          </div>
        </div>

        {/* Citations / Sources */}
        {data.citations && data.citations.length > 0 && (
          <div className="mb-8">
            <h2 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">Sources</h2>
            <div className="space-y-4">
              {data.citations.map((cit, i) => (
                <div key={i} className="bg-white rounded-lg border border-gray-200 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm font-medium text-indigo-700">{cit.section_reference}</span>
                    {cit.verified ? (
                      <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">Verified</span>
                    ) : (
                      <span className="text-xs bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded">Unverified</span>
                    )}
                  </div>
                  <p className="text-sm text-gray-700 mb-2">{cit.claim_text}</p>
                  {cit.source_quote && (
                    <blockquote className="border-l-3 border-indigo-200 pl-3 text-sm text-gray-500 italic bg-gray-50 rounded-r p-3">
                      "{cit.source_quote}"
                    </blockquote>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-white">
        <div className="max-w-3xl mx-auto px-4 py-4 text-center text-xs text-gray-400">
          Powered by Replivo
        </div>
      </footer>
    </div>
  );
}
