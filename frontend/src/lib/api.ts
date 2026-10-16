const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const MAX_MESSAGE_LENGTH = 2000;

type ChatResponse = { reply: string };

/** Mesajı backend'e (POST /api/chat) gönderir ve Mercek'in cevabını döner. */
export async function sendChat(message: string): Promise<string> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
  } catch {
    throw new Error("Sunucuya ulaşılamadı. Backend çalışıyor mu?");
  }

  if (!response.ok) {
    const detail = await readDetail(response);
    throw new Error(detail ?? `Beklenmeyen hata (${response.status}).`);
  }

  const data = (await response.json()) as ChatResponse;
  return data.reply;
}

async function readDetail(response: Response): Promise<string | null> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    return typeof body.detail === "string" ? body.detail : null;
  } catch {
    return null;
  }
}
