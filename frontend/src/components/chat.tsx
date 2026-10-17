"use client";

import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from "react";

import { AffectedCustomersPanel } from "@/components/affected-customers";
import { Markdown } from "@/components/markdown";
import {
  type AffectedSummary,
  MAX_MESSAGE_LENGTH,
  sendChat,
  UnauthorizedError,
} from "@/lib/api";

type Message = {
  id: number;
  role: "user" | "assistant";
  text: string;
  affected?: AffectedSummary;
};

type ChatProps = { token: string; onUnauthorized: () => void };

export function Chat({ token, onUnauthorized }: ChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const nextId = useRef(0);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  function addMessage(role: Message["role"], text: string, affected?: AffectedSummary) {
    const id = nextId.current++;
    setMessages((current) => [...current, { id, role, text, affected }]);
  }

  async function submit() {
    const text = input.trim();
    if (!text || loading) return;

    // Hafıza: bu mesajdan önceki konuşma (hata mesajları dahil değil).
    const history = messages.map(({ role, text: content }) => ({ role, content }));
    addMessage("user", text);
    setInput("");
    setError(null);
    setLoading(true);
    try {
      const data = await sendChat(text, history, token);
      addMessage("assistant", data.reply, data.affected_customers);
    } catch (err) {
      if (err instanceof UnauthorizedError) {
        onUnauthorized();
        return;
      }
      setError(err instanceof Error ? err.message : "Bir hata oluştu.");
    } finally {
      setLoading(false);
    }
  }

  function newConversation() {
    setMessages([]);
    setError(null);
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void submit();
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submit();
    }
  }

  return (
    <>
      <div className="flex-1 space-y-3 overflow-y-auto py-4" aria-live="polite">
        {messages.length === 0 && (
          <p className="pt-10 text-center text-sm opacity-60">
            Örnek: &ldquo;ODMTTLMT ekranında hata alıyorum&rdquo;
          </p>
        )}
        {messages.map((message) => (
          <div
            key={message.id}
            className={message.role === "user" ? "flex justify-end" : "flex justify-start"}
          >
            {message.role === "user" ? (
              <p className="max-w-[80%] whitespace-pre-wrap rounded-2xl bg-violet-600 px-4 py-2 text-white">
                {message.text}
              </p>
            ) : (
              <div className="max-w-[80%] rounded-2xl bg-black/5 px-4 py-3 dark:bg-white/10">
                <Markdown text={message.text} />
                {message.affected && (
                  <AffectedCustomersPanel
                    summary={message.affected}
                    token={token}
                    onUnauthorized={onUnauthorized}
                  />
                )}
              </div>
            )}
          </div>
        ))}
        {loading && <p className="text-sm opacity-60">Mercek düşünüyor…</p>}
        {error && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}
        <div ref={bottomRef} />
      </div>

      {messages.length > 0 && (
        <div className="flex justify-end">
          <button
            type="button"
            onClick={newConversation}
            disabled={loading}
            className="text-sm text-violet-600 hover:underline disabled:opacity-40"
          >
            Yeni sohbet
          </button>
        </div>
      )}
      <form onSubmit={onSubmit} className="flex gap-2 border-t border-black/10 py-4 dark:border-white/15">
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={onKeyDown}
          maxLength={MAX_MESSAGE_LENGTH}
          rows={2}
          placeholder="Mesajınızı yazın (Enter gönderir, Shift+Enter yeni satır)"
          aria-label="Mesaj"
          className="flex-1 resize-none rounded-xl border border-black/15 bg-transparent px-3 py-2 outline-none focus:border-violet-500 dark:border-white/20"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="rounded-xl bg-violet-600 px-4 font-medium text-white disabled:opacity-40"
        >
          Gönder
        </button>
      </form>
    </>
  );
}
