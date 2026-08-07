export interface ChatRequest {
  client_id: string;
  conversation_id?: string | null;
  question: string;
}

export interface Source {
  document_id: string;
  filename: string;
  title: string;
  document_type: string;
  page_number: number | null;
  chunk_id: string;
  relevance_score: number;
  download_url: string;
  view_url: string;
}

export interface ChatMessageData {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  sources?: Source[];
}

export interface ConversationSummary {
  id: string;
  session_id: string;
  client_id: string;
  title: string;
  message_count: number;
  last_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail {
  id: string;
  session_id: string;
  client_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessageData[];
}

export interface SSEEvent {
  type: "start" | "delta" | "done" | "error";
  content?: string;
  conversation_id?: string;
  message_id?: string;
  sources?: Source[];
  rewritten_query?: string | null;
  message?: string;
}

export interface DocumentOut {
  id: string;
  filename: string;
  title: string;
  description: string | null;
  category: string | null;
  year: number | null;
  version: string | null;
  document_type: string;
  file_size: number;
  status: string;
  error_message: string | null;
  is_active: boolean;
  department: string | null;
  program: string | null;
  language: string | null;
  effective_date: string | null;
  expiration_date: string | null;
  chunk_count: number;
  created_at: string;
  updated_at: string;
  download_url: string | null;
  view_url: string | null;
}

export interface UploadResult {
  document: DocumentOut;
  message: string;
}

export interface LLMProvider {
  id: string;
  name: string;
  provider_type: string;
  base_url: string;
  model: string;
  temperature: number;
  max_tokens: number;
  timeout: number;
  enabled: boolean;
  priority: number;
  has_api_key: boolean;
  api_key_masked: string;
  extra: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface RAGConfig {
  embedding_provider: string;
  embedding_model: string;
  embedding_base_url: string;
  embedding_api_key: string;
  reranker_provider: string;
  reranker_model: string;
  chunk_size: number;
  chunk_overlap: number;
  top_k: number;
  final_k: number;
  similarity_threshold: number;
  enable_query_rewrite: boolean;
  enable_reranker: boolean;
}

export interface SystemLog {
  id: string;
  timestamp: string;
  level: string;
  event_type: string;
  conversation_id: string | null;
  question: string | null;
  rewritten_query: string | null;
  retrieved_documents: unknown;
  retrieved_scores: unknown;
  reranker_scores: unknown;
  selected_sources: unknown;
  llm_provider: string | null;
  llm_model: string | null;
  latency_ms: number | null;
  status: string;
  error: string | null;
  details: unknown;
}

export interface DashboardStats {
  total_documents: number;
  indexed_documents: number;
  processing_documents: number;
  failed_documents: number;
  total_conversations: number;
  total_messages: number;
  llm_requests: number;
  rag_queries: number;
  recent_activity: SystemLog[];
}

export interface PublicSettings {
  site_name: string;
  chatbot_name: string;
  welcome_message: string;
}

export interface Settings {
  general: {
    site_name: string;
    chatbot_name: string;
    welcome_message: string;
  };
  security: {
    chat_rate_limit_per_minute: number;
    max_upload_size_mb: number;
  };
  metadata: {
    categories: { name: string; keywords: string[] }[];
    departments: string[];
    programs: string[];
  };
}

export interface MetadataField {
  value: string | number | null;
  confidence: number;
  method: string;
}

export interface MetadataExtractionResult {
  filename: string;
  title: MetadataField;
  category: MetadataField;
  year: MetadataField;
  version: MetadataField;
  department: MetadataField;
  program: MetadataField;
  language: MetadataField;
  description: MetadataField;
}

export interface AdminUser {
  id: string;
  username: string;
  email: string | null;
  is_active: boolean;
  created_at: string;
}
