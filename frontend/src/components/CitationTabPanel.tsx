import { useState } from 'react';
import PdfViewer from './PdfViewer';

interface CitationEntry {
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

interface CitationTabPanelProps {
  citation: CitationEntry;
}

function ChunkContentExpander({ content }: { content: string }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="border-t border-gray-100 pt-4">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-xs font-medium text-gray-500 uppercase tracking-wide hover:text-gray-700 transition-colors w-full"
      >
        <svg
          className={`w-3.5 h-3.5 transition-transform ${expanded ? 'rotate-90' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        Document Text
      </button>
      {expanded && (
        <div className="mt-2 bg-indigo-50 border border-indigo-100 rounded-lg p-3">
          <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{content}</p>
        </div>
      )}
    </div>
  );
}


export default function CitationTabPanel({ citation }: CitationTabPanelProps) {
  const cit = citation;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-0 h-[calc(100vh-10rem)] min-h-[500px]">
      {/* Left: PDF Viewer (2/3) */}
      <div className="lg:col-span-2 overflow-hidden">
        {cit.view_url ? (
          <PdfViewer
            url={cit.view_url}
            pageNumber={cit.page_number}
            highlightText={cit.source_quote}
          />
        ) : (
          <div className="flex items-center justify-center h-full bg-gray-50 rounded-lg border border-gray-200">
            <div className="text-center text-gray-500">
              <svg className="w-12 h-12 mx-auto mb-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
              <p className="font-medium">PDF not available</p>
              <p className="text-sm mt-1">The source document cannot be displayed inline.</p>
            </div>
          </div>
        )}
      </div>

      {/* Right: Sidebar (1/3) */}
      <div className="overflow-y-auto border-l border-gray-200 bg-white p-5 space-y-5">
        {/* Section reference + verified badge */}
        <div>
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="text-lg font-semibold text-gray-900">{cit.section_reference}</span>
            {cit.verified ? (
              <span className="inline-flex items-center gap-1 text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                Verified
              </span>
            ) : (
              <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-medium">Unverified</span>
            )}
          </div>
        </div>

        {/* Page number */}
        {cit.page_number != null && (
          <div className="text-sm text-gray-500">
            Page {cit.page_number}
          </div>
        )}

        {/* Document name + download */}
        {cit.document_name && (
          <div className="bg-gray-50 rounded-lg p-3">
            <div className="flex items-center gap-2 text-sm text-gray-700">
              <svg className="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
              <span className="truncate font-medium">{cit.document_name}</span>
            </div>
            {cit.download_url && (
              <a
                href={cit.download_url}
                className="mt-2 inline-flex items-center gap-1.5 text-xs text-indigo-600 hover:text-indigo-800 font-medium"
                download
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Download PDF
              </a>
            )}
          </div>
        )}

        {/* Claim text */}
        <div>
          <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Claim</div>
          <p className="text-sm text-gray-800 leading-relaxed">{cit.claim_text}</p>
        </div>

        {/* Source quote */}
        {cit.source_quote && (
          <div>
            <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Source Quote</div>
            <blockquote className="border-l-3 border-indigo-200 pl-3 text-sm text-gray-600 italic bg-gray-50 rounded-r p-3">
              &ldquo;{cit.source_quote}&rdquo;
            </blockquote>
          </div>
        )}

        {/* Chunk content — collapsed by default */}
        {cit.chunk_content && <ChunkContentExpander content={cit.chunk_content} />}
      </div>
    </div>
  );
}
