import ReactMarkdown from 'react-markdown';

interface Props {
  children: string;
  className?: string;
}

export default function Markdown({ children, className = '' }: Props) {
  return (
    <div className={`markdown-content text-sm text-gray-700 ${className}`}>
      <ReactMarkdown
        components={{
          p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
          strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
          em: ({ children }) => <em className="italic">{children}</em>,
          ul: ({ children }) => <ul className="list-disc pl-5 mb-3 space-y-1">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal pl-5 mb-3 space-y-1">{children}</ol>,
          li: ({ children }) => <li>{children}</li>,
          h1: ({ children }) => <h1 className="text-lg font-bold mb-2">{children}</h1>,
          h2: ({ children }) => <h2 className="text-base font-bold mb-2">{children}</h2>,
          h3: ({ children }) => <h3 className="text-sm font-bold mb-1">{children}</h3>,
          blockquote: ({ children }) => (
            <blockquote className="border-l-3 border-gray-300 pl-3 text-gray-500 italic mb-3">{children}</blockquote>
          ),
          hr: () => <hr className="my-4 border-gray-200" />,
          a: ({ href, children }) => (
            <a href={href} className="text-indigo-600 hover:text-indigo-800 underline" target="_blank" rel="noopener noreferrer">{children}</a>
          ),
          code: ({ children }) => (
            <code className="bg-gray-100 text-gray-800 px-1 py-0.5 rounded text-xs font-mono">{children}</code>
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
