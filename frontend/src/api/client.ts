import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

// Auth
export const login = (username: string, password: string) =>
  api.post('/auth/login', { username, password });

export const logout = () => api.post('/auth/logout');

export const getMe = () => api.get('/auth/me');

// Dashboard
export const getDashboardStats = () => api.get('/dashboard/stats');

// Communities
export const getCommunities = () => api.get('/communities');
export const getCommunity = (id: string) => api.get(`/communities/${id}`);
export const createCommunity = (data: any) => api.post('/communities', data);
export const updateCommunity = (id: string, data: any) => api.put(`/communities/${id}`, data);
export const deleteCommunity = (id: string) => api.delete(`/communities/${id}`);

// Tenants
export const getTenants = (communityId: string) =>
  api.get(`/communities/${communityId}/tenants`);
export const createTenant = (communityId: string, data: any) =>
  api.post(`/communities/${communityId}/tenants`, data);
export const updateTenant = (communityId: string, tenantId: string, data: any) =>
  api.put(`/communities/${communityId}/tenants/${tenantId}`, data);
export const deleteTenant = (communityId: string, tenantId: string) =>
  api.delete(`/communities/${communityId}/tenants/${tenantId}`);

// Documents
export const getDocuments = (communityId: string) =>
  api.get(`/communities/${communityId}/documents`);
export const uploadDocument = (communityId: string, file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post(`/communities/${communityId}/documents`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};
export const deleteDocument = (communityId: string, docId: string) =>
  api.delete(`/communities/${communityId}/documents/${docId}`);

// Conversations
export const getConversations = (params?: { status?: string; community_id?: string }) =>
  api.get('/conversations', { params });
export const getConversation = (id: string) => api.get(`/conversations/${id}`);
export const approveConversation = (id: string) => api.post(`/conversations/${id}/approve`);
export const editAndSend = (id: string, body: string) =>
  api.post(`/conversations/${id}/edit-and-send`, { body });
export const manualReply = (id: string, body: string) =>
  api.post(`/conversations/${id}/reply`, { body });
export const closeConversation = (id: string) => api.post(`/conversations/${id}/close`);

// Playground
export const playgroundAsk = (communityId: string, question: string, conversationHistory?: Array<{role: string, text: string}>) =>
  api.post('/playground/ask', { community_id: communityId, question, conversation_history: conversationHistory });

// Citations (public)
export const getCitation = (token: string) => api.get(`/citations/${token}`);

export default api;
