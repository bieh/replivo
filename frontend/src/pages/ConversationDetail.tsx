import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getConversation, approveConversation, editAndSend,
  manualReply, closeConversation,
} from '../api/client';
import type { Conversation, Message, Citation } from '../types';
import StatusBadge from '../components/StatusBadge';
import Markdown from '../components/Markdown';

export default function ConversationDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [replyText, setReplyText] = useState('');
  const [editText, setEditText] = useState('');
  const [showEditor, setShowEditor] = useState(false);

  const { data: conv, isLoading } = useQuery<Conversation>({
    queryKey: ['conversation', id],
    queryFn: () => getConversation(id!).then((r) => r.data),
  });

  const approveMutation = useMutation({
    mutationFn: () => approveConversation(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversation', id] });
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });

  const editSendMutation = useMutation({
    mutationFn: () => editAndSend(id!, editText),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversation', id] });
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      setShowEditor(false);
    },
  });

  const replyMutation = useMutation({
    mutationFn: () => manualReply(id!, replyText),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversation', id] });
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      setReplyText('');
    },
  });

  const closeMutation = useMutation({
    mutationFn: () => closeConversation(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversation', id] });
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });

  if (isLoading || !conv) return <div className="text-gray-500">Loading...</div>;

  const messages = conv.messages || [];
  const inbound = messages.find((m) => m.direction === 'inbound');
  const aiDraft = [...messages].reverse().find((m) => m.direction === 'outbound' && m.is_ai_generated);
  const canApprove = conv.status === 'draft_ready' && aiDraft;
  const needsHuman = conv.status === 'needs_human';
  const isOpen = !['replied', 'auto_replied', 'closed'].includes(conv.status);

  return (
    <div>
      <button onClick={() => navigate('/conversations')} className="text-sm text-indigo-600 hover:text-indigo-800 mb-4">
        &larr; Back to Conversations
      </button>

      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{conv.subject || '(no subject)'}</h1>
        <StatusBadge status={conv.status} />
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Thread */}
        <div className="col-span-2 space-y-4">
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}

          {/* Action Area */}
          {isOpen && (
            <div className="bg-white rounded-lg shadow p-6 space-y-4">
              {canApprove && !showEditor && (
                <div className="flex gap-3">
                  <button
                    onClick={() => approveMutation.mutate()}
                    disabled={approveMutation.isPending}
                    className="px-4 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 disabled:opacity-50"
                  >
                    {approveMutation.isPending ? 'Sending...' : 'Approve & Send'}
                  </button>
                  <button
                    onClick={() => {
                      setEditText(aiDraft?.body_text || '');
                      setShowEditor(true);
                    }}
                    className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded-md hover:bg-gray-200"
                  >
                    Edit & Send
                  </button>
                  <button
                    onClick={() => closeMutation.mutate()}
                    className="px-4 py-2 text-gray-500 text-sm hover:text-gray-700"
                  >
                    Close
                  </button>
                </div>
              )}

              {showEditor && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Edit Response</label>
                  <textarea
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    rows={8}
                    className="w-full border border-gray-300 rounded-md p-3 text-sm"
                  />
                  <div className="flex gap-3 mt-3">
                    <button
                      onClick={() => editSendMutation.mutate()}
                      disabled={editSendMutation.isPending}
                      className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700 disabled:opacity-50"
                    >
                      {editSendMutation.isPending ? 'Sending...' : 'Send Edited Reply'}
                    </button>
                    <button onClick={() => setShowEditor(false)} className="text-sm text-gray-500">
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {needsHuman && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Write a reply</label>
                  <textarea
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    rows={6}
                    placeholder="Type your reply to the tenant..."
                    className="w-full border border-gray-300 rounded-md p-3 text-sm"
                  />
                  <div className="flex gap-3 mt-3">
                    <button
                      onClick={() => replyMutation.mutate()}
                      disabled={!replyText.trim() || replyMutation.isPending}
                      className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700 disabled:opacity-50"
                    >
                      {replyMutation.isPending ? 'Sending...' : 'Send Reply'}
                    </button>
                    <button
                      onClick={() => closeMutation.mutate()}
                      className="px-4 py-2 text-gray-500 text-sm hover:text-gray-700"
                    >
                      Close Without Reply
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-sm font-medium text-gray-900 mb-3">Details</h3>
            <dl className="space-y-2 text-sm">
              <div>
                <dt className="text-gray-500">From</dt>
                <dd className="text-gray-900">{conv.sender_email}</dd>
              </div>
              {conv.tenant_name && (
                <div>
                  <dt className="text-gray-500">Tenant</dt>
                  <dd className="text-gray-900">{conv.tenant_name} {conv.tenant_unit ? `(${conv.tenant_unit})` : ''}</dd>
                </div>
              )}
              {conv.community_name && (
                <div>
                  <dt className="text-gray-500">Community</dt>
                  <dd className="text-gray-900">{conv.community_name}</dd>
                </div>
              )}
              <div>
                <dt className="text-gray-500">Received</dt>
                <dd className="text-gray-900">{new Date(conv.created_at).toLocaleString()}</dd>
              </div>
            </dl>
          </div>

          {/* AI Analysis */}
          {aiDraft?.ai_response_data && (
            <div className="bg-white rounded-lg shadow p-4">
              <h3 className="text-sm font-medium text-gray-900 mb-3">AI Analysis</h3>
              <dl className="space-y-2 text-sm">
                <div>
                  <dt className="text-gray-500">Answer Type</dt>
                  <dd className="text-gray-900">{aiDraft.ai_response_data.answer_type}</dd>
                </div>
                <div>
                  <dt className="text-gray-500">Confidence</dt>
                  <dd className="text-gray-900">{aiDraft.ai_response_data.overall_confidence}</dd>
                </div>
                {aiDraft.ai_response_data.escalation_reason && (
                  <div>
                    <dt className="text-gray-500">Escalation Reason</dt>
                    <dd className="text-red-700">{aiDraft.ai_response_data.escalation_reason}</dd>
                  </div>
                )}
                {aiDraft.ai_response_data.sections_reviewed?.length > 0 && (
                  <div>
                    <dt className="text-gray-500">Sections Reviewed</dt>
                    <dd className="text-gray-900">{aiDraft.ai_response_data.sections_reviewed.join(', ')}</dd>
                  </div>
                )}
              </dl>
            </div>
          )}

          {/* Citations */}
          {aiDraft?.citations && aiDraft.citations.length > 0 && (
            <div className="bg-white rounded-lg shadow p-4">
              <h3 className="text-sm font-medium text-gray-900 mb-3">Citations</h3>
              <ul className="space-y-3">
                {aiDraft.citations.map((cit: Citation, i: number) => (
                  <li key={i} className="text-sm">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-indigo-700">{cit.section_reference}</span>
                      {cit.verified ? (
                        <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">Verified</span>
                      ) : (
                        <span className="text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded">Unverified</span>
                      )}
                    </div>
                    <p className="text-gray-600 mt-1">{cit.claim_text}</p>
                    {cit.source_quote && (
                      <p className="text-gray-400 mt-1 text-xs italic">"{cit.source_quote.substring(0, 150)}..."</p>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isInbound = message.direction === 'inbound';

  return (
    <div className={`bg-white rounded-lg shadow p-4 ${isInbound ? 'border-l-4 border-gray-300' : 'border-l-4 border-indigo-400'}`}>
      <div className="flex justify-between text-sm mb-2">
        <span className="font-medium text-gray-900">
          {isInbound ? message.from_email : 'Replivo AI'}
          {message.is_ai_generated && (
            <span className="ml-2 text-xs bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded">AI Generated</span>
          )}
        </span>
        <span className="text-gray-400">
          {message.sent_at ? `Sent ${new Date(message.sent_at).toLocaleString()}` :
           message.created_at ? new Date(message.created_at).toLocaleString() : ''}
        </span>
      </div>
      <Markdown>{message.body_text}</Markdown>
    </div>
  );
}
