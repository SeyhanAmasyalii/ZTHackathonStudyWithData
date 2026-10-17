"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { fetchUsers, login } from "@/lib/api";
import { saveSession, type User } from "@/lib/session";

export function Login() {
  const router = useRouter();
  const [users, setUsers] = useState<User[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchUsers()
      .then((list) => !cancelled && setUsers(list))
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Kullanıcılar alınamadı.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function choose(userName: string) {
    setPending(userName);
    setError(null);
    try {
      saveSession(await login(userName));
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Giriş yapılamadı.");
    } finally {
      // Next.js önceki sayfanın durumunu korur; çıkışta liste kilitli kalmasın.
      setPending(null);
    }
  }

  return (
    <div className="space-y-3">
      {error && (
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
      {!users && !error && <p className="text-sm opacity-60">Kullanıcılar yükleniyor…</p>}
      <ul className="grid gap-2 sm:grid-cols-2">
        {users?.map((user) => (
          <li key={user.user_name}>
            <button
              type="button"
              onClick={() => void choose(user.user_name)}
              disabled={pending !== null}
              className="w-full rounded-xl border border-black/10 px-4 py-3 text-left hover:border-violet-500 disabled:opacity-50 dark:border-white/15"
            >
              <span className="block font-medium">{user.name}</span>
              <span className="block text-sm opacity-70">
                {user.title} · {user.unit}
              </span>
              {pending === user.user_name && (
                <span className="block text-sm text-violet-600">Giriş yapılıyor…</span>
              )}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
