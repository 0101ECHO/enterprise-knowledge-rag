// ---- Auth & User ----
export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface User {
  id: string;
  username: string;
  email: string;
  role: "admin" | "maintainer" | "user";
  full_name: string;
  tenant_id: string;
  is_active: boolean;
  last_login_at: string;
  created_at: string;
}

// ---- Knowledge Base ----
export interface KnowledgeBase {
  id: string;
  tenant_id: string;
  name: string;
  description: string;
  collection_name: string;
  visibility: "public" | "private" | "role_based";
  document_count: number;
  chunk_count: number;
  embedding_model: string;
  embedding_dim: number;
  is_active: boolean;
  created_by: string;
  created_at: string;
}

export interface KBListResponse {
  total: number;
  items: KnowledgeBase[];
}

// ---- Document ----
export interface Document {
  id: string;
  title: string;
  file_name: string;
  file_type: string;
  file_size: number;
  status: "pending" | "processing" | "completed" | "failed";
  chunk_count: number;
  processing_error?: string;
  kb_id: string;
  created_at: string;
}

// ---- Chat ----
export interface ChatRequest {
  kb_id: string;
  question: string;
  conversation_id?: string;
}

export interface Source {
  document_id?: string;
  document_title: string;
  page?: number;
  chunk_index?: number;
  score: number;
  content?: string;
}

export interface SSEChunk {
  type: "sources" | "token" | "done" | "error";
  data: string;
  sources?: Source[];
}

export interface Conversation {
  id: string;
  title: string;
  status: "active" | "archived";
  message_count: number;
  kb_id?: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  created_at: string;
}
