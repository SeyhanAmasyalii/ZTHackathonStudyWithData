import type { Metadata } from "next";

import { Login } from "@/components/login";

export const metadata: Metadata = { title: "Giriş · Mercek" };

export default function LoginPage() {
  return (
    <main className="mx-auto w-full max-w-2xl px-4 py-10">
      <h1 className="text-2xl font-semibold">Mercek</h1>
      <p className="mb-6 text-sm opacity-70">
        Demo kullanıcısı seçerek giriş yapın. Kullanıcılar sentetiktir, şifre yoktur.
      </p>
      <Login />
    </main>
  );
}
