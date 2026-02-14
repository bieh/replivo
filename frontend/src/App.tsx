import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, useEffect } from 'react';
import { getMe } from './api/client';
import type { User } from './types';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Communities from './pages/Communities';
import CommunityDetail from './pages/CommunityDetail';
import Conversations from './pages/Conversations';
import ConversationDetail from './pages/ConversationDetail';
import Playground from './pages/Playground';
import CitationView from './pages/CitationView';
import Layout from './components/Layout';

const queryClient = new QueryClient();

function AuthWrapper() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMe()
      .then((res) => setUser(res.data))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return <Login onLogin={setUser} />;
  }

  return (
    <Layout user={user} onLogout={() => setUser(null)}>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/communities" element={<Communities />} />
        <Route path="/communities/:id" element={<CommunityDetail />} />
        <Route path="/conversations" element={<Conversations />} />
        <Route path="/conversations/:id" element={<ConversationDetail />} />
        <Route path="/playground" element={<Playground />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </Layout>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/citations/:token" element={<CitationView />} />
          <Route path="*" element={<AuthWrapper />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
