import type { ChatRequest, SSEEvent } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* ignore */
    }
    throw new ApiError(detail || "Request failed", response.status);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function buildUrl(path: string): string {
  return `${API_BASE}${path}`;
}

export const api = {
  async get<T>(path: string): Promise<T> {
    const response = await fetch(buildUrl(path), {
      credentials: "include",
      headers: { "Content-Type": "application/json" },
    });
    return handleResponse<T>(response);
  },

  async post<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(buildUrl(path), {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    return handleResponse<T>(response);
  },

  async put<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(buildUrl(path), {
      method: "PUT",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    return handleResponse<T>(response);
  },

  async delete<T>(path: string): Promise<T> {
    const response = await fetch(buildUrl(path), {
      method: "DELETE",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
    });
    return handleResponse<T>(response);
  },

  async upload<T>(path: string, formData: FormData): Promise<T> {
    const response = await fetch(buildUrl(path), {
      method: "POST",
      credentials: "include",
      body: formData,
    });
    return handleResponse<T>(response);
  },
};

export async function streamChat(
  payload: ChatRequest,
  onEvent: (event: SSEEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(buildUrl("/api/chat/stream"), {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    let detail = "Request failed";
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(detail, response.status);
  }

  if (!response.body) {
    throw new ApiError("Streaming is not supported by this browser.", 0);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const processLine = (line: string) => {
    const trimmed = line.trim();
    if (!trimmed.startsWith("data:")) return;
    const data = trimmed.slice(5).trim();
    if (data === "[DONE]") return;
    try {
      const event = JSON.parse(data) as SSEEvent;
      onEvent(event);
    } catch {
      /* skip malformed frames */
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      processLine(line);
    }
  }
  if (buffer.trim()) processLine(buffer);
}

export function fileUrl(path: string): string {
  if (!path) return "#";
  return `${API_BASE}${path}`;
}
