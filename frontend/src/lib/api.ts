import type {
  AutomationLogsResponse,
  AutomationSetting,
  ClerkUserSyncPayload,
  EmailResponse,
  GeneratePostResponse,
  ImageResponse,
  LinkedInStatus,
  OpenAiKeyStatus,
  PostRecord,
  PostStatus,
  ProfileInsights,
  PublishResponse,
  SuggestTopicsResponse,
  SetOpenAiKeyResponse,
} from '../types';

const API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(
  /\/$/,
  '',
);

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers || undefined);
  // Default all requests to JSON unless the caller explicitly sets a different Content-Type.
  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = (data as any)?.detail;
    const message =
      typeof detail === 'string'
        ? detail
        : detail
          ? JSON.stringify(detail)
          : (data as any)?.message || 'Request failed';
    throw new Error(message);
  }
  return data as T;
}

function authHeaders(authToken?: string | null): Record<string, string> {
  return authToken ? { Authorization: `Bearer ${authToken}` } : {};
}

export async function fetchPosts(status?: PostStatus | null) {
  const query = status ? `?status=${status}` : '';
  return apiFetch<{ success: boolean; posts: PostRecord[]; count: number }>(
    `/posts${query}`,
  );
}

export async function fetchLinkedInStatus(
  { clerkUserId }: { clerkUserId?: string } = {},
) {
  const query = clerkUserId ? `?clerk_user_id=${encodeURIComponent(clerkUserId)}` : '';
  return apiFetch<LinkedInStatus>(`/auth/status${query}`);
}

export async function fetchProfileInsights() {
  return apiFetch<ProfileInsights>('/profile/insights');
}

export async function generatePost(payload: {
  topic: string;
  additional_context?: string | null;
}, opts?: { authToken?: string | null }) {
  return apiFetch<GeneratePostResponse>('/generate', {
    method: 'POST',
    headers: {
      ...authHeaders(opts?.authToken),
    },
    body: JSON.stringify(payload),
  });
}

export async function generateImage(prompt: string, model?: string) {
  return apiFetch<ImageResponse>('/generate/image', {
    method: 'POST',
    body: JSON.stringify({ prompt, model }),
  });
}

export async function publishPost(postId: number, visibility: string = 'PUBLIC') {
  return apiFetch<PublishResponse>('/publish', {
    method: 'POST',
    body: JSON.stringify({ post_id: postId, visibility }),
  });
}

export async function schedulePost(postId: number, payload: { scheduled_for: string; visibility?: string }) {
  return apiFetch<{ success: boolean; post: PostRecord; message: string }>(`/posts/${postId}/schedule`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function emailPost(
  postId: number,
  payload: { recipients: string[]; subject?: string; intro?: string; include_image?: boolean },
) {
  return apiFetch<EmailResponse>(`/posts/${postId}/email`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updatePost(
  postId: number,
  payload: Partial<
    Pick<
      PostRecord,
      'content' | 'status' | 'image_base64' | 'image_mime_type' | 'image_url' | 'image_storage_path'
    >
  >,
) {
  return apiFetch<{ success: boolean; post: PostRecord }>(`/posts/${postId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function deletePost(postId: number) {
  return apiFetch<{ success: boolean; message: string }>(`/posts/${postId}`, {
    method: 'DELETE',
  });
}

export async function syncClerkUser(payload: ClerkUserSyncPayload) {
  return apiFetch<{ success: boolean }>(`/users/sync`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getOpenAiKeyStatus(opts: { authToken: string }) {
  return apiFetch<OpenAiKeyStatus>(`/users/openai-key/status`, {
    headers: {
      ...authHeaders(opts.authToken),
    },
  });
}

export async function setOpenAiKey(opts: { authToken: string; openaiApiKey: string }) {
  return apiFetch<SetOpenAiKeyResponse>(`/users/openai-key`, {
    method: 'POST',
    headers: {
      ...authHeaders(opts.authToken),
    },
    body: JSON.stringify({
      openai_api_key: opts.openaiApiKey,
    }),
  });
}

export async function suggestTopics(
  payload: { occupation: string; limit?: number },
  opts?: { authToken?: string | null },
) {
  return apiFetch<SuggestTopicsResponse>(`/topics/suggest`, {
    method: 'POST',
    headers: {
      ...authHeaders(opts?.authToken),
    },
    body: JSON.stringify(payload),
  });
}

export function openLinkedInConnect(
  { clerkUserId }: { clerkUserId?: string } = {},
) {
  const query = clerkUserId ? `?clerk_user_id=${encodeURIComponent(clerkUserId)}` : '';
  window.location.assign(`${API_BASE}/auth/connect${query}`);
}

export async function getAutomationSetting(opts: { authToken: string }) {
  return apiFetch<AutomationSetting>(`/me/automation`, {
    headers: { ...authHeaders(opts.authToken) },
  });
}

export async function setAutomationSetting(
  payload: { enabled?: boolean; frequency?: 'daily' | 'weekly'; occupation?: string; auto_publish?: boolean },
  opts: { authToken: string },
) {
  return apiFetch<AutomationSetting>(`/me/automation`, {
    method: 'PATCH',
    headers: { ...authHeaders(opts.authToken) },
    body: JSON.stringify(payload),
  });
}

export async function getAutomationLogs(opts: { authToken: string }, limit = 20) {
  return apiFetch<AutomationLogsResponse>(`/me/automation/logs?limit=${limit}`, {
    headers: { ...authHeaders(opts.authToken) },
  });
}

export const API = {
  BASE_URL: API_BASE,
};

