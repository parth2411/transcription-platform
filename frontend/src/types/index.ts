export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  subscription_tier: 'free' | 'pro' | 'business'
  is_active: boolean
  monthly_usage: number
  created_at: string
}

export interface Transcription {
  id: string
  title: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  file_type?: string
  file_size?: number
  duration_seconds?: number
  transcription_text?: string
  summary_text?: string
  language: string
  created_at: string
  completed_at?: string
  processing_time_seconds?: number
  error_message?: string
}

export interface TranscriptionList {
  transcriptions: Transcription[]
  total: number
  page: number
  per_page: number
}

export interface QueryResult {
  answer: string
  sources: QuerySource[]
  confidence: number
  query_id: string
}

export interface QuerySource {
  id: string
  title: string
  date: string
  confidence: number
  type: 'transcription' | 'summary'
}

export interface QueryHistory {
  id: string
  query: string
  answer: string
  confidence?: number
  response_time_ms?: number
  created_at: string
  source_count: number
}

export interface KnowledgeStats {
  transcription_count: number
  vector_count: number
  query_count: number
  total_duration_hours: number
  collection_name: string
}

export interface UserStats {
  total_transcriptions: number
  completed_transcriptions: number
  total_duration_hours: number
  total_queries: number
  monthly_usage: number
  subscription_tier: string
  usage_limit: number
  storage_used_mb: number
}

export interface ApiError {
  detail: string
  status_code: number
}

export interface AuthResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}
