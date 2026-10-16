# M1 — Basit akış görev listesi (Foundry + Backend)

> Ne yapılacağı, örnek girdi/çıktılar, prompt'lar ve şemalar: [`m1-basit-akis.md`](m1-basit-akis.md) (adım numaraları oradakiyle aynı).
> Prompt dosyaları: [`prompts/varlik-cikar.md`](../prompts/varlik-cikar.md) (1. AI çağrısı), [`prompts/log-acikla.md`](../prompts/log-acikla.md) (2. AI çağrısı).
> Sırayla ilerleyin; **Bitti sayılır** satırı sağlanmadan sonrakine geçmeyin. Copilot'a yalnızca ilgili dosyaları ve `m1-basit-akis.md`'yi verin.

**Kurallar:** repoya anahtar, endpoint değeri yazılmaz (`<PLACEHOLDER>`); değerler App Settings'te ya da yerelde `backend/.env`'de (git'e girmez). CodeQL dosyasına dokunulmaz. Değişiklik feature branch + PR. Testlerde gerçek Foundry çağrısı yok (`FakeLLMClient`).

---

## A. Foundry (Azure tarafı)

### A1 · Kaynak ve `chat` modeli (20 dk)
1. Takımın resource group'unda **Azure AI Foundry** kaynağı + proje (`mercek-foundry`).
2. **Deploy model:** büyük, reasoning'siz genel model (gpt-4.1 sınıfı ya da bölgedeki güncel karşılığı); yoksa gpt-5 sınıfı. Deploy adı **`chat`**. Kota ≥ 30K TPM.
3. Model kartında **structured outputs (`json_schema`)** desteği olmalı — iki AI çağrısı da buna dayanıyor.

**Bitti sayılır:** Playground'da `chat` cevap veriyor.

### A2 · Erişim (10 dk)
- **İdeal:** `mercek-api` → Identity → System assigned **On**; Foundry → IAM → **Cognitive Services OpenAI User** → `mercek-api`.
- **Yedek:** Foundry → Keys → anahtar → `mercek-api` App Settings `AZURE_OPENAI_API_KEY`.
- `mercek-api` App Settings: `AZURE_OPENAI_ENDPOINT=<endpoint>`, `CHAT_DEPLOYMENT=chat`, `DEMO_NOW=2026-10-17T09:15:00+03:00`, `DATA_DIR=data`.
- Yerelde aynı adlar `backend/.env`'de (`DATA_DIR=../datav2`).

**Bitti sayılır:** App Settings tamam; repoda hiçbir değer yok.

### A3 · Gerçek modelle deneme (15 dk, B7 bittikten sonra)
`m1-basit-akis.md` test setindeki 1–6. mesajları yerel backend'e (gerçek Foundry ile) gönder. Beklenen fiş ve cevap geliyor mu, süre kaç saniye? Sonucu README'ye bir satır yaz (model adı, doğru sayısı, ortalama süre).

**Bitti sayılır:** 6/6 beklenen sonuç; ortalama < 4 sn (iki çağrı toplamı).

---

## B. Backend (FastAPI)

Ön koşul: `backend/` iskeleti ve `/api/health` var.

### B1 · Ayarlar (15 dk)
`app/config.py` (`pydantic-settings`): `azure_openai_endpoint`, `azure_openai_api_key` (opsiyonel), `chat_deployment="chat"`, `demo_now` (opsiyonel; yoksa şimdiki zaman, `Europe/Istanbul`), `data_dir`. `.env.example`'da yalnızca `<PLACEHOLDER>`.

**Bitti sayılır:** `uv run pytest`, `uv run ruff check .` yeşil.

### B2 · Veri deposu — akış 2. adım (30 dk)
`app/repositories/datastore.py`: `DATA_DIR` altındaki 5 JSON'u **ilk erişimde bir kez** yükler, bellekte tutar (salt okunur).
- `screens()`, `institutions()` (koda göre sıralı), `screen_name(code)`, `institution_name(code)`
- `logs()`, `rules()`, `solution_templates()`
- Dosya yoksa ya da bozuksa anlaşılır hata.

**Deploy notu:** CI build adımı `datav2/*.json`'ı `backend/data/` altına kopyalar (`DATA_DIR=data`).

**Bitti sayılır:** Test: 9 ekran, 16 kurum, 10.555 log, 20 kural, 37 şablon; ikinci çağrıda dosya tekrar okunmuyor.

### B3 · LLM istemcisi (45 dk)
`app/clients/llm.py`:
- `azure_client.py` yapısı: `OpenAI(base_url=f"{endpoint}/openai/v1")`; anahtar yoksa `azure-identity` token.
- `load_prompt(name)`: `prompts/<ad>.md` → `## schema` (JSON), `## system`, `## user` bloklarını ayırır.
- `chat_json(name, variables, schema, model_cls, max_tokens)`: `{{değişken}}`leri doldurur; `response_format={"type": "json_schema", "json_schema": schema}`, `temperature=0`, zaman aşımı 10 sn; Pydantic ile doğrular; hata olursa **1 kez** yeniden dener, yine olmazsa `LLMError`.
- Süre ve token sayısını loglar; mesaj metnini loglamaz.
- `FakeLLMClient`: prompt adına ve mesaja göre sabit JSON döner.

**Bitti sayılır:** Fake ile prompt yükleme, değişken doldurma, yeniden deneme testleri yeşil.

### B4 · Modeller ve şemalar (30 dk)
`app/models/assist.py`:
- `AssistRequest {message: 1–1000 karakter, user_name: 1–50, ^[a-z0-9]+$}`
- `Fis` (akış §3), `LogResult` (§5), `Rule` (§6), `Cevap` (§8), `AssistResponse` (§9)
- `fis_schema(datastore)`: `FIS_SCHEMA`; `screen_code` / `institution_code` enum'ları JSON'lardan.
- `cevap_schema(candidate_ids)`: `CEVAP_SCHEMA`; `solution_id` enum'u adaylardan.

**Bitti sayılır:** Test: fiş şemasında 9 ekran + 16 kurum enum'u; cevap şemasında verilen adaylar.

### B5 · Kod adımları — akış 4–7 (60 dk)
`app/services/assist_steps.py` (saf fonksiyonlar, AI yok):
- `check_fis(fis, now) -> Fis | message` (§4 tablosu)
- `find_log(fis, user_name, now, logs) -> LogResult | None` (§5: filtre, en son log, `count`)
- `find_rule(screen_code, error_number, rules) -> Rule | None` (§6: önce ekran, sonra `*`)
- `find_candidates(error_code, templates) -> list` (§7: en fazla 5)
- `build_log_summary`, `build_rule_text`, `build_candidates_text` → 2. AI çağrısının `{{…}}` metinleri (§8 user prompt biçimi)

**Bitti sayılır:** `tests/test_assist_steps.py`: Elif + ODMTTLMT → log 08:57:46, count 8; kural 7; 5 aday (SOL-001…004, SOL-031); Elif + KRDTKULL → log yok; tarih/saat kontrolleri.

### B6 · Akışı birleştir — akış 3 + 8 (45 dk)
`app/services/assist.py` → `assist(request, llm, datastore, now) -> AssistResponse`:
1. §3: `llm.chat_json("varlik-cikar", {now, screens, institutions, message}, fis_schema, Fis)`
2. §4–7: B5 fonksiyonları; akış duruyorsa `message` ile dön (2. AI çağrısı yapılmaz)
3. §8: `llm.chat_json("log-acikla", {user_name, message, log_summary, rule_text, candidates}, cevap_schema, Cevap, max_tokens=600)`
4. §9: `AssistResponse`; `LLMError` → `message = "Şu an yanıt üretemiyorum, lütfen tekrar deneyin."`

**Bitti sayılır:** `tests/test_assist.py`: `m1-basit-akis.md` test setinin 8 maddesi `FakeLLMClient` ile yeşil.

### B7 · API ucu — akış 1 + 9 (20 dk)
`app/api/mercek.py`: `POST /api/mercek/assist` → `AssistRequest` doğrulama → `assist(...)` → `AssistResponse`. Router `/api` önekiyle `main.py`'ye eklenir.

**Bitti sayılır:** `uv run uvicorn app.main:app --reload` → `/docs`'tan `{"message": "ODMTTLMT ekranında hata alıyorum", "user_name": "elif"}` → `answer.solution_id = "SOL-031"` (gerçek Foundry ile; A3).

### B8 · PR (15 dk)
`uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest` yeşil; çıktılar PR açıklamasında. Kontrol: secret yok · CodeQL değişmedi · testlerde gerçek Foundry yok · mesaj metni loglanmıyor.

---

## Frontend (bilgi)
Mercek sohbet sayfası mesajı `POST {NEXT_PUBLIC_API_URL}/api/mercek/assist` ile gönderir (`user_name` = giriş yapan demo kullanıcısı). Cevaptaki `answer` kart olarak, `message` düz metin olarak gösterilir (`m1-basit-akis.md` §9).

## Sıra

| Zaman | Foundry kişisi | Backend kişisi |
|---|---|---|
| 0:00 – 0:30 | A1, A2 | B1, B2 |
| 0:30 – 1:30 | (frontend'e destek) | B3, B4 |
| 1:30 – 2:45 | | B5, B6 |
| 2:45 – 3:15 | A3 | B7, B8 |

**Takılırsanız:** 401/403 → A2 rol ya da anahtar · `response_format` / `json_schema` hatası → model structured outputs desteklemiyor (A1) · `DATA_DIR` bulunamadı → `.env`'de `DATA_DIR=../datav2` · cevap boş ya da şema hatası → `LLMError` logundaki doğrulama mesajı.
