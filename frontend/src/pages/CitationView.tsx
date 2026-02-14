import { useState, useEffect, useMemo } from 'react';
import { useParams, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getCitation } from '../api/client';
import CitationTabPanel from '../components/CitationTabPanel';

interface Citation {
  index: number;
  claim_text: string;
  section_reference: string;
  source_quote: string;
  confidence: string;
  verified: boolean;
  document_name: string;
  document_id?: string;
  chunk_content: string;
  page_number: number | null;
  download_url: string | null;
  view_url?: string | null;
}

interface CitationData {
  subject: string;
  answer_text: string;
  citations: Citation[];
  community_name: string;
}

function parseHashIndex(hash: string): number | null {
  const match = hash.match(/^#cite-(\d+)$/);
  return match ? parseInt(match[1], 10) : null;
}

export default function CitationView() {
  const { token } = useParams<{ token: string }>();
  const location = useLocation();

  const { data, isLoading, isError } = useQuery<CitationData>({
    queryKey: ['citation', token],
    queryFn: () => getCitation(token!).then((r) => r.data),
  });

  // Determine initial active index from URL hash
  const initialIndex = parseHashIndex(location.hash);
  const [activeIndex, setActiveIndex] = useState<number>(initialIndex ?? 1);

  // Update active index when data loads if hash points to valid citation
  useEffect(() => {
    if (data && data.citations.length > 0) {
      const hashIdx = parseHashIndex(location.hash);
      if (hashIdx && data.citations.some((c) => c.index === hashIdx)) {
        setActiveIndex(hashIdx);
      } else if (!data.citations.some((c) => c.index === activeIndex)) {
        setActiveIndex(data.citations[0].index);
      }
    }
  }, [data]);

  const handleTabClick = (index: number) => {
    setActiveIndex(index);
    history.replaceState(null, '', `#cite-${index}`);
  };

  const activeCitation = useMemo(
    () => data?.citations.find((c) => c.index === activeIndex),
    [data, activeIndex],
  );

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

  if (!data.citations || data.citations.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">No Citations</h1>
          <p className="text-gray-500">This response has no source citations.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 flex-shrink-0">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-3">
          <span className="text-xl font-bold text-indigo-600">Replivo</span>
          {data.community_name && (
            <span className="text-sm text-gray-400">{data.community_name}</span>
          )}
          <span className="text-sm text-gray-400 mx-1">/</span>
          <span className="text-sm text-gray-700 truncate">Re: {data.subject}</span>
        </div>
      </header>

      {/* Tab bar */}
      <div className="bg-white border-b border-gray-200 flex-shrink-0">
        <div className="max-w-7xl mx-auto px-4">
          <nav className="flex gap-1 overflow-x-auto py-1 -mb-px scrollbar-thin" aria-label="Citation tabs">
            {data.citations.map((cit) => {
              const isActive = cit.index === activeIndex;
              const label = `#${cit.index}`;
              const docLabel = cit.document_name ? ` - ${cit.document_name}` : '';
              const sectionLabel = cit.section_reference ? ` - ${cit.section_reference}` : '';

              return (
                <button
                  key={cit.index}
                  onClick={() => handleTabClick(cit.index)}
                  className={`flex-shrink-0 px-3 py-2 text-sm font-medium rounded-t-lg border-b-2 transition-colors whitespace-nowrap ${
                    isActive
                      ? 'border-indigo-500 text-indigo-700 bg-indigo-50'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  {label}{docLabel}{sectionLabel}
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Tab content */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-4 overflow-hidden">
        {activeCitation && (
          <CitationTabPanel
            key={`${activeCitation.document_id ?? activeCitation.index}-${activeCitation.index}`}
            citation={activeCitation}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-white flex-shrink-0">
        <div className="max-w-7xl mx-auto px-4 py-3 text-center text-xs text-gray-400">
          Powered by Replivo
        </div>
      </footer>
    </div>
  );
}
