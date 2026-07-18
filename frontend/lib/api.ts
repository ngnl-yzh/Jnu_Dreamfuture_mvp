export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
export const RUN_BASE =
  process.env.NEXT_PUBLIC_RUN_BASE ?? "http://localhost:8080";

const TOKEN_KEY = "jnu_access_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token === null) localStorage.removeItem(TOKEN_KEY);
  else localStorage.setItem(TOKEN_KEY, token);
}

interface ApiOptions {
  method?: string;
  body?: unknown;
  form?: FormData;
}

export async function api<T = any>(path: string, opts: ApiOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let body: BodyInit | undefined;
  if (opts.form) {
    body = opts.form;
  } else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method: opts.method ?? (body ? "POST" : "GET"),
    headers,
    body,
  });
  if (res.status === 204) return null as T;

  const contentType = res.headers.get("content-type") ?? "";
  const data = contentType.includes("json") ? await res.json().catch(() => null) : await res.text();
  if (!res.ok) {
    const detail = (data as any)?.detail;
    throw new Error(
      typeof detail === "string" ? detail : detail ? JSON.stringify(detail) : `요청 실패 (${res.status})`
    );
  }
  return data as T;
}
