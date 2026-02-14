import { useState, useRef, useCallback, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/TextLayer.css';
import 'react-pdf/dist/Page/AnnotationLayer.css';

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

interface PdfViewerProps {
  url: string;
  pageNumber?: number | null;
  highlightText?: string;
}

const PAGE_WIDTH = 700;

function normalizeText(text: string): string {
  return text.replace(/\s+/g, ' ').trim().toLowerCase();
}

export default function PdfViewer({ url, pageNumber, highlightText }: PdfViewerProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const targetPageRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const scrolledRef = useRef(false);

  const targetPage = pageNumber ?? 1;

  const onDocumentLoadSuccess = useCallback(({ numPages: n }: { numPages: number }) => {
    setNumPages(n);
    setLoading(false);
    scrolledRef.current = false;
  }, []);

  const onDocumentLoadError = useCallback(() => {
    setError(true);
    setLoading(false);
  }, []);

  // Scroll to target page after render
  useEffect(() => {
    if (numPages > 0 && !scrolledRef.current && targetPageRef.current) {
      scrolledRef.current = true;
      setTimeout(() => {
        targetPageRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 300);
    }
  }, [numPages]);

  // Build text renderer for the target page only
  const textRenderer = useCallback(
    (textItem: { str: string }): string => {
      if (!highlightText || highlightText.length < 4) return textItem.str;

      const normalizedStr = normalizeText(textItem.str);
      if (normalizedStr.length < 3) return textItem.str;

      const normalizedHighlight = normalizeText(highlightText);

      // Direct substring match (either direction)
      if (normalizedHighlight.includes(normalizedStr) || normalizedStr.includes(normalizedHighlight)) {
        return `<mark style="background-color: #fef08a; padding: 1px 0;">${textItem.str}</mark>`;
      }

      // Word overlap match
      const highlightWords = normalizedHighlight.split(' ').filter((w) => w.length >= 4);
      const strWords = normalizedStr.split(' ').filter((w) => w.length >= 4);
      if (strWords.length > 0 && highlightWords.length > 0) {
        const matchCount = strWords.filter((w) => highlightWords.includes(w)).length;
        if (matchCount >= Math.min(2, strWords.length)) {
          return `<mark style="background-color: #fef08a; padding: 1px 0;">${textItem.str}</mark>`;
        }
      }

      return textItem.str;
    },
    [highlightText],
  );

  if (error) {
    return (
      <div className="flex items-center justify-center h-96 bg-gray-50 rounded-lg border border-gray-200">
        <p className="text-gray-500">Failed to load PDF</p>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="overflow-y-auto h-full bg-gray-100 rounded-lg">
      {loading && (
        <div className="flex items-center justify-center h-96">
          <div className="text-gray-500 flex items-center gap-2">
            <svg className="animate-spin h-5 w-5 text-indigo-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Loading PDF...
          </div>
        </div>
      )}
      <Document
        file={url}
        onLoadSuccess={onDocumentLoadSuccess}
        onLoadError={onDocumentLoadError}
        loading=""
      >
        {Array.from({ length: numPages }, (_, i) => {
          const page = i + 1;
          const isTarget = page === targetPage;

          return (
            <div
              key={page}
              ref={isTarget ? targetPageRef : undefined}
              className="relative mb-2"
            >
              {/* Page label */}
              <div className={`sticky top-0 z-10 flex items-center gap-2 px-3 py-1 text-xs ${isTarget ? 'bg-indigo-100 text-indigo-700 font-semibold' : 'bg-gray-200 text-gray-600'}`}>
                Page {page}
                {isTarget && <span className="bg-indigo-200 text-indigo-800 px-1.5 py-0.5 rounded text-[10px] uppercase tracking-wide font-bold">Cited</span>}
              </div>
              <div className="flex justify-center bg-gray-100 py-1">
                <Page
                  pageNumber={page}
                  width={PAGE_WIDTH}
                  renderTextLayer={isTarget}
                  renderAnnotationLayer={false}
                  customTextRenderer={isTarget ? textRenderer : undefined}
                />
              </div>
            </div>
          );
        })}
      </Document>
    </div>
  );
}
