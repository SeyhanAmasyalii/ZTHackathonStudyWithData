"use client";

import { useRouter } from "next/navigation";
import { useEffect, useSyncExternalStore } from "react";

import { Chat } from "@/components/chat";
import { clearSession, getServerSession, getSession, subscribe } from "@/lib/session";

/** Paketleme anında gömülür (scripts/package_azure.py): Azure'da hangi sürümün çalıştığı görülür. */
const BUILD_ID = process.env.NEXT_PUBLIC_BUILD_ID;

/** Oturum yoksa giriş sayfasına yönlendirir; varsa başlık + sohbet. */
export function Home() {
  const router = useRouter();
  const session = useSyncExternalStore(subscribe, getSession, getServerSession);

  useEffect(() => {
    if (session === null) router.replace("/giris");
  }, [session, router]);

  if (!session) return null;

  function logout() {
    clearSession();
  }

  return (
    <main className="mx-auto flex h-dvh w-full max-w-3xl flex-col px-4">
      <header className="flex items-start justify-between gap-4 border-b border-black/10 py-4 dark:border-white/15">
        <div>
          <h1 className="text-xl font-semibold">Mercek</h1>
          <p className="text-sm opacity-70">Yaşadığınız sorunu yazın, birlikte bakalım.</p>
          {BUILD_ID && <p className="text-[10px] opacity-40">sürüm {BUILD_ID}</p>}
        </div>
        <div className="text-right text-sm">
          <p className="font-medium">{session.user.name}</p>
          <p className="opacity-70">{session.user.unit}</p>
          <button type="button" onClick={logout} className="mt-1 text-violet-600 hover:underline">
            Çıkış
          </button>
        </div>
      </header>
      <Chat
        key={session.user.user_name}
        token={session.token}
        userName={session.user.user_name}
        onUnauthorized={logout}
      />
    </main>
  );
}
