import type { Session, User } from "@/lib/session";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const MAX_MESSAGE_LENGTH = 2000;
/** Konuşma hafızası: modele gönderilen önceki mesaj sayısı (backend sınırı 20). */
export const MAX_HISTORY = 20;
const MAX_HISTORY_CONTENT = 8000;

export type HistoryMessage = { role: "user" | "assistant"; content: string };

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

/** Mesajı ve aynı sohbetin önceki mesajlarını backend'e (POST /api/chat) gönderir. */
export async function sendChat(
  message: string,
  history: HistoryMessage[],
  token: string,
): Promise<string> {
  const data = await request<{ reply: string }>("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({
      message,
      history: history
        .slice(-MAX_HISTORY)
        .map((item) => ({ ...item, content: item.content.slice(0, MAX_HISTORY_CONTENT) })),
    }),
  });
  return data.reply;
}
