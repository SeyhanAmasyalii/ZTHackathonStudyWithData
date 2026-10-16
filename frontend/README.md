# mercek-web (frontend)

Next.js 16. Tek sayfalık Mercek sohbet ekranı; mesajı backend'e (`POST /api/chat`) gönderir.

## Çalıştırma

Önce backend çalışıyor olmalı (`../backend/README.md`, port 8000).

```bash
cd frontend
npm install
copy .env.example .env.local      # macOS/Linux: cp .env.example .env.local
npm run dev
```

Tarayıcıda http://localhost:3000 → mesaj yaz → Enter.

| Ekranda | Anlamı |
|---|---|
| Mercek'in cevabı | Her şey çalışıyor |
| "Sunucuya ulaşılamadı…" | Backend kapalı ya da `NEXT_PUBLIC_API_URL` yanlış |
| "Model bağlantısı yapılandırılmamış." | `backend/.env` eksik |
| "Şu an yanıt üretilemiyor." | Model çağrısı başarısız; backend terminalindeki log satırına bak |

## Kontroller

```bash
npm run lint
npx tsc --noEmit
npm run build
```

Not: ESLint için `eslint-config-next` yerine sade bir kurulum kullanılıyor (`eslint.config.mjs`); `eslint-config-next` zinciri düzeltmesi olmayan yüksek seviyeli bir `npm audit` bulgusu getiriyor.
