export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type User = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  org_id: string;
  is_active: boolean;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

export type DocumentItem = {
  id: string;
  original_filename: string;
  file_type: string;
  file_size: number;
  status: string;
  access_level: string;
  chunk_count: number;
  summary?: string | null;
  created_at: string;
  error_message?: string | null;
};

export type QuerySource = {
  document_name: string;
  chunk_content: string;
  page_number?: number | null;
  section_title?: string | null;
  relevance_score: number;
};

export type QueryResponse = {
  answer: string;
  sources: QuerySource[];
  conversation_id: string;
  query_time_ms: number;
};

type RequestOptions = {
  method?: "GET" | "POST" | "DELETE";
  token?: string;
  body?: unknown;
  formData?: FormData;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};

  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? "GET",
    headers: options.formData ? headers : { ...headers, "Content-Type": "application/json" },
    body: options.formData ?? (options.body ? JSON.stringify(options.body) : undefined),
    cache: "no-store",
  });

  if (!response.ok) {
    let message = "Request failed";
    try {
      const payload = await response.json();
      message = payload.detail ?? payload.message ?? message;
    } catch {
      message = response.statusText || message;
    }
    throw new Error(message);
  }

  return (await response.json()) as T;
}

export function login(email: string, password: string) {
  return request<TokenResponse>("/api/auth/login", {
    method: "POST",
    body: { email, password },
  });
}

export function signup(payload: {
  org_name: string;
  full_name: string;
  email: string;
  password: string;
}) {
  return request<TokenResponse>("/api/auth/register", {
    method: "POST",
    body: payload,
  });
}

export function getCurrentUser(token: string) {
  return request<User>("/api/auth/me", { token });
}

export function listDocuments(token: string) {
  return request<{ documents: DocumentItem[]; total: number }>("/api/documents/", { token });
}

export function askQuestion(token: string, question: string, conversationId?: string | null) {
  return request<QueryResponse>("/api/query/", {
    method: "POST",
    token,
    body: {
      question,
      conversation_id: conversationId ?? null,
      top_k: 5,
    },
  });
}

export function uploadDocument(token: string, file: File, accessLevel = "public") {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("access_level", accessLevel);

  return request<{ doc_id: string; status: string; filename: string }>("/api/documents/upload", {
    method: "POST",
    token,
    formData,
  });
}
