# mercek-api (backend)

FastAPI. Mercek sohbet mesajını Azure AI Foundry'deki modele (`gpt-5.5`) iletir.

| Uç | Ne yapar |
|---|---|
| `GET /api/health` | `{"status": "ok"}` |
| `POST /api/chat` | `{"message": "..."}` → `{"reply": "..."}` |

Katmanlar: `app/api` (HTTP) → `app/services` (iş mantığı, araçlar) → `app/repositories` (`datav2` JSON) / `app/clients` (model). System prompt: `../prompts/mercek-chat.md`.

**Araç:** `kibana_sorgula`. Model kapsamı seçer (ekran, kurum, hata no, zaman aralığı, yalnızca kullanıcının logları mı, anahtar kelime); backend sorguyu `datav2/kibana_logs.json` (Warning/Error) üzerinde çalıştırır. En fazla 7 gün, en fazla 5 tur.

**Demo ayarları** (varsayılanlar; `.env`'de değiştirilebilir): `DEMO_NOW=2026-10-17T09:15:00+03:00` (veri 09:00'da biter), `DEMO_USER=elif` (giriş ekranı gelene kadar).

## Kurulum

Gerekli: [uv](https://docs.astral.sh/uv/) (Python 3.12'yi kendisi kurar).

```bash
cd backend
uv sync
cp .env.example .env
```

`.env` dosyasını Foundry'den doldur (Foundry → gpt-5.5 → **Uç noktayı görüntüle**):

```
AZURE_OPENAI_ENDPOINT=https://<kaynak-adi>.openai.azure.com
AZURE_OPENAI_API_KEY=<anahtar>
CHAT_DEPLOYMENT=gpt-5.5
```

- Endpoint olarak **kaynak adresini** yaz (`https://<ad>.openai.azure.com` ya da `https://<ad>.services.ai.azure.com`). Sonunda `/openai/v1` olabilir de olmayabilir de; kod ikisini de kabul eder.
- `.env` repoya girmez. Anahtarı kimseyle paylaşma.

## Çalıştırma

```bash
uv run uvicorn app.main:app --reload --port 8000
```

Tarayıcıda http://localhost:8000/docs → `POST /api/chat` → **Try it out** → `{"message": "merhaba"}` → **Execute**.

| Cevap | Anlamı |
|---|---|
| 200 + `reply` | Model çalışıyor |
| 503 | `.env`'de endpoint ya da anahtar eksik |
| 502 | Model çağrısı başarısız (endpoint, anahtar ya da deploy adı yanlış); terminaldeki log satırına bak |

## Test ve lint

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Testler gerçek modeli çağırmaz (`FakeLLMClient`).
