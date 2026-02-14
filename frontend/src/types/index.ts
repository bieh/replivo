export interface User {
  id: string;
  email: string;
  username: string;
  role: string;
  organization_id: string;
}

export interface Community {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  description: string;
  inbox_email: string | null;
  settings: {
    auto_reply_enabled: boolean;
    [key: string]: any;
  };
  tenant_count: number;
  document_count: number;
  created_at: string;
}

export interface Tenant {
  id: string;
  community_id: string;
  name: string;
  email: string;
  unit: string | null;
  is_active: boolean;
  created_at: string;
}

export interface Document {
  id: string;
  community_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  total_pages: number | null;
  total_chunks: number;
  total_tokens: number;
  status: string;
  created_at: string;
}

export interface Citation {
  claim_text: string;
  section_reference: string;
  source_quote: string;
  confidence: string;
  verified: boolean;
}

export interface Message {
  id: string;
  conversation_id: string;
  direction: 'inbound' | 'outbound';
  from_email: string;
  to_email: string;
  subject: string;
  body_text: string;
  body_html: string | null;
  citations: Citation[] | null;
  ai_response_data: any;
  is_ai_generated: boolean;
  sent_at: string | null;
  created_at: string;
}

export interface Conversation {
  id: string;
  community_id: string;
  tenant_id: string | null;
  subject: string;
  status: string;
  sender_email: string;
  community_name?: string;
  tenant_name?: string;
  tenant_unit?: string;
  last_message_preview?: string;
  messages?: Message[];
  created_at: string;
  updated_at: string;
}

export interface DashboardStats {
  status_counts: Record<string, number>;
  total: number;
  needs_attention: number;
  recent: Conversation[];
  inboxes: Array<{ community_name: string; inbox_email: string }>;
}
