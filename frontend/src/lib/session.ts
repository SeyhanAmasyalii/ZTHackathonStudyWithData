/** Demo oturumu: backend'in verdiği imzalı token ve kullanıcı bilgisi tarayıcıda saklanır. */

export type User = { user_name: string; name: string; title: string; unit: string };
export type Session = { token: string; user: User };

const STORAGE_KEY = "mercek.session";
const listeners = new Set<() => void>();

let cachedRaw: string | null | undefined;
let cachedSession: Session | null = null;

function readRaw(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function parse(raw: string | null): Session | null {
  if (!raw) return null;
  try {
    const value = JSON.parse(raw) as Partial<Session>;
    return typeof value.token === "string" && value.user ? (value as Session) : null;
  } catch {
    return null;
  }
}

/** useSyncExternalStore için: aynı içerik için aynı nesneyi döner. */
export function getSession(): Session | null {
  const raw = readRaw();
  if (raw !== cachedRaw) {
    cachedRaw = raw;
    cachedSession = parse(raw);
  }
  return cachedSession;
}

/** Sunucuda oturum bilinmez. */
export function getServerSession(): undefined {
  return undefined;
}

export function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  window.addEventListener("storage", listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

function notify() {
  listeners.forEach((listener) => listener());
}

export function saveSession(session: Session) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  } catch {
    // Depolama kapalıysa oturum yalnızca bu sayfada kalır.
  }
  notify();
}

export function clearSession() {
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // yok say
  }
  notify();
}

/** Sunucudaki konuşmanın kimliği (yalnızca kimlik; mesajlar SQL'de). Sayfa yenilenince geçmiş geri yüklenir. */
function conversationKey(userName: string): string {
  return `mercek.conversation.${userName}`;
}

export function loadConversationId(userName: string): string | null {
  try {
    const value = window.localStorage.getItem(conversationKey(userName));
    return value && /^[0-9a-f]{32}$/.test(value) ? value : null;
  } catch {
    return null;
  }
}

export function saveConversationId(userName: string, conversationId: string) {
  try {
    window.localStorage.setItem(conversationKey(userName), conversationId);
  } catch {
    // Depolama kapalıysa geçmiş yalnızca bu sayfada kalır.
  }
}

export function clearConversationId(userName: string) {
  try {
    window.localStorage.removeItem(conversationKey(userName));
  } catch {
    // yok say
  }
}
