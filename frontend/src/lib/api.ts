import type { Session, User } from "@/lib/session";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const MAX_MESSAGE_LENGTH = 2000;

/** Oturum geçersiz ya da süresi dolmuş (401). */
export class UnauthorizedError extends Error {}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new Error("Sunucuya ulaşılamadı. Backend çalışıyor mu?");
  }

  if (!response.ok) {
    const detail = (await readDetail(response)) ?? `Beklenmeyen hata (${response.status}).`;
    throw response.status === 401 ? new UnauthorizedError(detail) : new Error(detail);
  }
  return (await response.json()) as T;
}

async function readDetail(response: Response): Promise<string | null> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    return typeof body.detail === "string" ? body.detail : null;
  } catch {
    return null;
  }
}

export function fetchUsers(): Promise<User[]> {
  return request<User[]>("/api/users");
}

export function login(userName: string): Promise<Session> {
  return request<Session>("/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_name: userName }),
  });
}

/** Mesajı backend'e (POST /api/chat) gönderir ve Mercek'in cevabını döner. */
export async function sendChat(message: string, token: string): Promise<string> {
  const data = await request<{ reply: string }>("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ message }),
  });
  return data.reply;
}
