import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getCommunity, getTenants, getDocuments,
  createTenant, deleteTenant, uploadDocument, deleteDocument,
  updateCommunity,
} from '../api/client';
import type { Community, Tenant, Document } from '../types';

export default function CommunityDetail() {
  const { id } = useParams<{ id: string }>();
  const [tab, setTab] = useState<'tenants' | 'documents' | 'settings'>('tenants');
  const queryClient = useQueryClient();

  const { data: community } = useQuery<Community>({
    queryKey: ['community', id],
    queryFn: () => getCommunity(id!).then((r) => r.data),
  });

  if (!community) return <div className="text-gray-500">Loading...</div>;

  const tabs = [
    { key: 'tenants', label: `Tenants (${community.tenant_count})` },
    { key: 'documents', label: `Documents (${community.document_count})` },
    { key: 'settings', label: 'Settings' },
  ] as const;

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-1">{community.name}</h1>
      <p className="text-sm text-gray-500 mb-6">{community.description}</p>

      <div className="border-b border-gray-200 mb-6">
        <nav className="flex space-x-8">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`py-2 px-1 border-b-2 text-sm font-medium ${
                tab === t.key
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      {tab === 'tenants' && <TenantsTab communityId={id!} />}
      {tab === 'documents' && <DocumentsTab communityId={id!} />}
      {tab === 'settings' && <SettingsTab community={community} />}
    </div>
  );
}

function TenantsTab({ communityId }: { communityId: string }) {
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [unit, setUnit] = useState('');
  const queryClient = useQueryClient();

  const { data: tenants } = useQuery<Tenant[]>({
    queryKey: ['tenants', communityId],
    queryFn: () => getTenants(communityId).then((r) => r.data),
  });

  const addMutation = useMutation({
    mutationFn: () => createTenant(communityId, { name, email, unit }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants', communityId] });
      queryClient.invalidateQueries({ queryKey: ['community', communityId] });
      setShowForm(false);
      setName(''); setEmail(''); setUnit('');
    },
  });

  const removeMutation = useMutation({
    mutationFn: (tenantId: string) => deleteTenant(communityId, tenantId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants', communityId] });
      queryClient.invalidateQueries({ queryKey: ['community', communityId] });
    },
  });

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-medium text-gray-900">Tenants</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
        >
          Add Tenant
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={(e) => { e.preventDefault(); addMutation.mutate(); }}
          className="bg-gray-50 p-4 rounded-lg mb-4 flex gap-3 items-end"
        >
          <div>
            <label className="block text-xs font-medium text-gray-600">Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} required
              className="mt-1 block w-40 rounded border-gray-300 text-sm border px-2 py-1.5" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600">Email</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} required type="email"
              className="mt-1 block w-48 rounded border-gray-300 text-sm border px-2 py-1.5" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600">Unit</label>
            <input value={unit} onChange={(e) => setUnit(e.target.value)}
              className="mt-1 block w-24 rounded border-gray-300 text-sm border px-2 py-1.5" />
          </div>
          <button type="submit" className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700">
            Save
          </button>
        </form>
      )}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Unit</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {tenants?.map((t) => (
              <tr key={t.id}>
                <td className="px-6 py-4 text-sm text-gray-900">{t.name}</td>
                <td className="px-6 py-4 text-sm text-gray-500">{t.email}</td>
                <td className="px-6 py-4 text-sm text-gray-500">{t.unit || '-'}</td>
                <td className="px-6 py-4 text-right">
                  <button
                    onClick={() => removeMutation.mutate(t.id)}
                    className="text-sm text-red-600 hover:text-red-800"
                  >
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {(!tenants || tenants.length === 0) && (
          <div className="px-6 py-8 text-center text-gray-500 text-sm">No tenants yet.</div>
        )}
      </div>
    </div>
  );
}

function DocumentsTab({ communityId }: { communityId: string }) {
  const [uploading, setUploading] = useState(false);
  const queryClient = useQueryClient();

  const { data: docs } = useQuery<Document[]>({
    queryKey: ['documents', communityId],
    queryFn: () => getDocuments(communityId).then((r) => r.data),
    refetchInterval: 5000,
  });

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await uploadDocument(communityId, file);
      queryClient.invalidateQueries({ queryKey: ['documents', communityId] });
      queryClient.invalidateQueries({ queryKey: ['community', communityId] });
    } catch (err) {
      alert('Upload failed');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const removeMutation = useMutation({
    mutationFn: (docId: string) => deleteDocument(communityId, docId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents', communityId] });
      queryClient.invalidateQueries({ queryKey: ['community', communityId] });
    },
  });

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-medium text-gray-900">Documents</h2>
        <label className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700 cursor-pointer">
          {uploading ? 'Uploading...' : 'Upload Document'}
          <input type="file" accept=".pdf,.txt" onChange={handleUpload} className="hidden" />
        </label>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Filename</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Chunks</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tokens</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {docs?.map((d) => (
              <tr key={d.id}>
                <td className="px-6 py-4 text-sm text-gray-900">{d.filename}</td>
                <td className="px-6 py-4 text-sm text-gray-500">{d.total_chunks}</td>
                <td className="px-6 py-4 text-sm text-gray-500">{d.total_tokens.toLocaleString()}</td>
                <td className="px-6 py-4">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    d.status === 'ready' ? 'bg-green-100 text-green-700' :
                    d.status === 'processing' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-red-100 text-red-700'
                  }`}>{d.status}</span>
                </td>
                <td className="px-6 py-4 text-right">
                  <button
                    onClick={() => removeMutation.mutate(d.id)}
                    className="text-sm text-red-600 hover:text-red-800"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {(!docs || docs.length === 0) && (
          <div className="px-6 py-8 text-center text-gray-500 text-sm">
            No documents. Upload a CC&R PDF to get started.
          </div>
        )}
      </div>
    </div>
  );
}

function SettingsTab({ community }: { community: Community }) {
  const [autoReply, setAutoReply] = useState(community.settings?.auto_reply_enabled ?? false);
  const [saved, setSaved] = useState(false);
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => updateCommunity(community.id, {
      settings: { ...community.settings, auto_reply_enabled: autoReply },
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['community', community.id] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
  });

  return (
    <div className="max-w-lg">
      <h2 className="text-lg font-medium text-gray-900 mb-4">Settings</h2>

      <div className="bg-white rounded-lg shadow p-6 space-y-6">
        <div>
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="font-medium text-gray-900">Auto-Reply</p>
              <p className="text-sm text-gray-500">
                When enabled, confident answers are sent automatically. Uncertain answers still go to the review queue.
              </p>
            </div>
            <button
              onClick={() => setAutoReply(!autoReply)}
              className={`relative inline-flex h-6 w-11 flex-shrink-0 items-center rounded-full transition-colors ${
                autoReply ? 'bg-indigo-600' : 'bg-gray-200'
              }`}
            >
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                autoReply ? 'translate-x-6' : 'translate-x-1'
              }`} />
            </button>
          </div>
        </div>

        <div>
          <p className="font-medium text-gray-900">Inbox Email</p>
          <p className="text-sm text-gray-500 mt-1">{community.inbox_email || 'Not configured'}</p>
        </div>

        <div>
          <p className="font-medium text-gray-900 opacity-50">Response Tone</p>
          <p className="text-sm text-gray-400 mt-1">Coming soon — Professional, Friendly, or Formal</p>
        </div>

        <button
          onClick={() => mutation.mutate()}
          className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700"
        >
          {saved ? 'Saved!' : 'Save Settings'}
        </button>
      </div>
    </div>
  );
}
