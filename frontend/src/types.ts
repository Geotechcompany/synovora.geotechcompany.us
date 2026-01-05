export type PostStatus = 'draft' | 'scheduled' | 'publishing' | 'published' | 'failed';

export interface PostRecord {
  id: number;
  topic: string;
  content: string;
  status: PostStatus;
  linkedin_post_id?: string;
  scheduled_for?: string | null;
  scheduled_visibility?: string | null;
  publish_attempts?: number;
  last_publish_error?: string | null;
  created_at: string;
  updated_at?: string;
  published_at?: string | null;
  image_base64?: string | null;
  image_mime_type?: string | null;
  image_url?: string | null;
  image_storage_path?: string | null;
}

export interface PostsResponse {
  success: boolean;
  posts: PostRecord[];
}

export interface GeneratePostResponse {
  success: boolean;
  post: PostRecord;
  message?: string;
  image?: {
    base64?: string;
    mime_type?: string;
    error?: string;
  };
}

export interface ImageResponse {
  success: boolean;
  image_url: string;
  storage_path?: string;
  mime_type: string;
}

export interface PublishResponse {
  success: boolean;
  message: string;
  post?: PostRecord;
  error?: string;
}

export interface EmailResponse {
  success: boolean;
  message: string;
}

export interface ProfileMetrics {
  followers?: number | null;
  connections?: number | null;
}

export interface ContentStats {
  total: number;
  drafts: number;
  published: number;
  scheduled: number;
  avg_word_count: number;
  recent_topics: string[];
  last_published_at?: string | null;
}

export interface ProfileSummary {
  first_name?: string;
  last_name?: string;
  headline?: string;
  bio?: string;
  industry?: string;
  vanity_name?: string;
  location?: string | {
    city?: string | null;
    province?: string | null;
    country?: string | null;
  } | null;
}

export interface ProfileInsights {
  success: boolean;
  profile?: ProfileSummary;
  metrics?: ProfileMetrics;
  content?: ContentStats;
  summary?: string;
  timestamp?: string;
  error?: string;
  scrape?: {
    used: boolean;
    error?: string | null;
    timestamp?: string | null;
  };
}

export interface LinkedInStatus {
  authenticated: boolean;
  profile?: Record<string, unknown> & {
    localizedFirstName?: string;
    localizedLastName?: string;
  };
  message?: string;
  cached?: boolean;
  last_checked_at?: string;
}

export interface OpenAiKeyStatus {
  has_key: boolean;
  last4?: string | null;
  set_at?: string | null;
}

export interface SetOpenAiKeyResponse {
  success: boolean;
  has_key: boolean;
  last4: string;
  set_at: string;
}

export interface SuggestTopicsResponse {
  success: boolean;
  occupation: string;
  topics: string[];
  intel?: {
    trend_error?: string | null;
    trending_topics?: Array<Record<string, unknown>>;
  };
}

export interface ClerkUserSyncPayload {
  clerk_user_id: string;
  email?: string;
  first_name?: string;
  last_name?: string;
  username?: string;
  image_url?: string;
  external_id?: string;
  last_sign_in_at?: string;
  created_at?: string;
}

