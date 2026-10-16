import { Chat } from "@/components/chat";

export default function Home() {
  return (
    <main className="mx-auto flex h-dvh w-full max-w-3xl flex-col px-4">
      <header className="border-b border-black/10 py-4 dark:border-white/15">
        <h1 className="text-xl font-semibold">Mercek</h1>
        <p className="text-sm opacity-70">Yaşadığınız sorunu yazın, birlikte bakalım.</p>
      </header>
      <Chat />
    </main>
  );
}
