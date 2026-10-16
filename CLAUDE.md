# Mercek — Claude Code talimatları

Ziraat Teknoloji YZ Hackathonu (16–17.10.2026), proje **Mercek**. Şu anki iş: **Modül 1** (Akıllı Problem Çözüm ve Çağrı Yönetimi).
Ayrıntılı plan, fazlar (F0–F11) ve senaryo kabul kriterleri: **`datav2/M1-GELISTIRME-BASLANGIC.md`**. Yeni bir faza başlamadan ilgili bölümünü oku.

## Doğru kaynak sırası
1. `datav2/M1-GELISTIRME-BASLANGIC.md` · 2. `datav2/SCHEMA.md` · 3. `datav2/README.md` · 4. `datav2/HANDOFF.md`
5. `docs/mercek-uygulama-rehberi.md` (eski adlarla yazılmış; başlangıç dosyası §2 sözlüğüyle oku), `docs/COPILOT_REBUILD_GUIDE.md`, `docs/mercek-azure-kurulum.md`, `docs/mercek-sql-search-esitleme.md`, `docs/hackathon-teknik-kilavuz.md`

## Veri
- Veri kaynağı **yalnızca `datav2/`** (JSON + `generators/`). `data/seed`, `data/out`, `tools/`, `tools/output` eski şemada: yalnızca fikir için okunabilir; **veri ya da kod kaynağı olarak kullanma, değiştirme.**
- Uygulama kodu yeni klasörlerde: `frontend/`, `backend/`, `db/`, `prompts/`, `tools/mercek/` (yeni betikler).

## Mimari
- Next.js 16 (`mercek-web`) + FastAPI (`mercek-api`, `/api/health` → 200), Azure SQL, Azure AI Search (hibrit RAG), Azure AI Foundry (`chat`, `embedding`).
- Backend katmanları: `api` → `services` → `repositories` / `clients`. Prompt'lar `prompts/<ad>.md`.
- **Hesabı kod yapar, AI açıklar.** Sayılar, eşikler, departman ataması, eşleşme eşiği (%75) kodda; AI çıkarır, sınıflar, açıklar. AI'a ham log değil özet gider; kullanıcı metni `<veri>…</veri>` içinde.
- Mercek'in türettiği alanlar `mercek_assigned_*`. AI önerir, insan onaylar.

## Kesin kurallar
- `.github/workflows/` altında **CodeQL dosyasına dokunma**; ikinci CodeQL yok; `.github/` ignore edilmez.
- Repoya **secret, API key, şifre, connection string, token yazma**; örneklerde `<PLACEHOLDER>`. Değerler ortam değişkeni / App Settings / Managed Identity.
- **KVKK:** Foundry'ye giden her metin önce taranır; bulgu varsa gönderilmez. Gerçek kişi verisi yok; firma adı `fineart`.
- Güvenli kod: girdi doğrulama, parametreli sorgu, çıktı encoding; sabit ve güncel bağımlılık sürümleri.
- Her iş mantığına birim testi; AI çağrıları testte mock (`FakeLLMClient`).
- Her değişiklikten sonra: `npm run build`, `npx tsc --noEmit`, `npm run lint` (frontend); `uv run pytest`, `uv run ruff check .` (backend). Sonuçları göster.
- Bir fazın kabul kriteri karşılanmadan sonrakine geçme. Değişiklikler feature branch + PR.

## Çalışma biçimi
- Yanıtlar **Türkçe, kısa ve odaklı**; kod tanımlayıcıları İngilizce, arayüz metinleri Türkçe.
- Karar gereken noktaları **numaralı** sor; kullanıcı "1. uygun 2. ok" diye yanıtlar. Belirsizse basit dille ve örnekle açıkla.
- Büyük veri ürettirme; betik yaz. İstenmeyen dosyayı baştan yazma, yalnızca gerekli değişikliği yap.
- Commit mesajı sonu: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (+ oturumun `Claude-Session:` satırı).
