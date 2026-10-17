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

/** Modelin son log sorgusu; etkilenen müşteri listesi backend'de bununla yeniden hesaplanır. */
export type AffectedQuery = {
  start_time: string;
  end_time: string;
  only_mine: boolean;
  screen_code?: string | null;
  institution_code?: string | null;
  error_number?: number | null;
  keyword?: string | null;
};

export type AffectedSummary = AffectedQuery & { customer_count: number };

export type AffectedCustomer = {
  customer_number: string;
  full_name: string | null;
  phone: string | null;
  can_call: boolean;
  channel: string;
  last_error_time: string;
  screen_code: string;
  error_number: number | null;
  institution_code: string | null;
};

export type AffectedCustomers = {
  total_customers: number;
  callable_customers: number;
  truncated: boolean;
  rows: AffectedCustomer[];
};

/** Eşleşen hazır çözümün ekran akışı (tur); bağlantıyı backend seçer. */
export type ScenarioLink = { solution_template_id: string; title: string; url: string };

export type ChatReply = {
  reply: string;
  affected_customers?: AffectedSummary;
  scenario_links?: ScenarioLink[];
  conversation_id?: string;
};

export type ConversationMessage = {
  role: "user" | "assistant";
  content: string;
  affected_customers?: AffectedSummary;
  scenario_links?: ScenarioLink[];
};

/** Sunucudaki (SQL) konuşma; sayfa yenilenince sohbeti geri yüklemek için. */
export function fetchConversation(
  conversationId: string,
  token: string,
): Promise<{ conversation_id: string; messages: ConversationMessage[] }> {
  return request(`/api/conversations/${encodeURIComponent(conversationId)}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

/** Mesajı, konuşma kimliğini ve yedek olarak önceki mesajları backend'e (POST /api/chat) gönderir. */
export async function sendChat(
  message: string,
  history: HistoryMessage[],
  token: string,
  conversationId: string | null = null,
): Promise<ChatReply> {
  return request<ChatReply>("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({
      message,
      // Geçmiş sunucuda tutulur; frontend'in geçmişi yalnızca sunucuda kayıt yoksa kullanılır.
      conversation_id: conversationId,
      history: history
        .slice(-MAX_HISTORY)
        .map((item) => ({ ...item, content: item.content.slice(0, MAX_HISTORY_CONTENT) })),
    }),
  });
}

/** Etkilenen müşteri listesi (yalnızca L2; liste modele gitmez, görüntüleme kayda alınır). */
export function fetchAffectedCustomers(
  query: AffectedQuery,
  token: string,
): Promise<AffectedCustomers> {
  const body: AffectedQuery = {
    start_time: query.start_time,
    end_time: query.end_time,
    only_mine: query.only_mine,
    screen_code: query.screen_code,
    institution_code: query.institution_code,
    error_number: query.error_number,
    keyword: query.keyword,
  };
  return request<AffectedCustomers>("/api/affected-customers", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  });
}
