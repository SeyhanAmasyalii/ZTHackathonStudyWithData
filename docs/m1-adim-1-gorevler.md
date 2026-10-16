# M1 · 1. adım — Görev listesi (Foundry + Backend)

> Ne yapılacağının tasarımı: [`m1-adim-1-basit.md`](m1-adim-1-basit.md). Prompt: [`prompts/varlik-cikar.md`](../prompts/varlik-cikar.md).
> Sırayla ilerleyin; her görevin **Bitti sayılır** satırı sağlanmadan sonrakine geçmeyin.
> Copilot'a her görevde yalnızca ilgili dosyaları ve `docs/m1-adim-1-basit.md`'yi verin; tüm repoyu vermeyin.

**Kesin kurallar:** repoya anahtar, şifre, endpoint değeri yazılmaz (örneklerde `<PLACEHOLDER>`). Değerler App Settings'te ya da yerelde `.env`'de (git'e girmez). CodeQL dosyasına dokunulmaz. Her değişiklik feature branch + PR.

---

## A. Foundry (Azure AI Foundry'yi kuran kişi)

### A1 · Kaynak ve proje (10 dk)
1. Takımın resource group'unda **Azure AI Foundry** kaynağı + proje: `mercek-foundry`, diğer kaynaklarla aynı bölge.
2. Portal → kaynak → **Keys and Endpoint** → endpoint'i not et (`https://<ad>.openai.azure.com`). Değeri repoya yazma.

**Bitti sayılır:** Portal'da kaynak ve proje görünüyor.

### A2 · `chat` modelini deploy et (10 dk)
1. **Models + endpoints → Deploy model.** Model: büyük, reasoning'siz genel model (gpt-4.1 sınıfı ya da bölgedeki güncel karşılığı). Yoksa gpt-5 sınıfı.
2. Deploy adı: **`chat`** (tam olarak bu). Tip: Global Standard ya da Standard. Kota: ≥ 30K TPM.
3. Model kartında **structured outputs / JSON schema** desteği olduğunu kontrol et.
4. İsteğe bağlı: karşılaştırma için ikinci aday (`chat-b`); A4'ten sonra silinir.

**Bitti sayılır:** Playground'da `chat`'e "merhaba" yazınca cevap geliyor.

### A3 · Erişim (10 dk)
- **İdeal:** `mercek-api` App Service → Identity → System assigned **On**. Foundry kaynağı → Access control (IAM) → **Cognitive Services OpenAI User** → `mercek-api`.
- **Yetki yoksa (yedek):** Foundry → Keys → anahtar → `mercek-api` App Settings'e `AZURE_OPENAI_API_KEY`.
- Her iki yolda `mercek-api` App Settings: `AZURE_OPENAI_ENDPOINT=<endpoint>`, `CHAT_DEPLOYMENT=chat`.
- Yerelde test için kendi `backend/.env` dosyana aynı adlarla yaz (dosya git'e girmez).

**Bitti sayılır:** App Settings'te iki (yedekte üç) ayar var; repoda hiçbir değer yok.

### A4 · Model doğrulama (15 dk, B6 bittikten sonra)
1. Backend'deki test setini (`m1-adim-1-basit.md` §7, 1–9) gerçek modelle çalıştır: `cd backend && uv run python -m scripts.eval_clues` (B6'da yazılır).
2. Kabul: 9/9 doğru, ortalama süre < 2 sn. İki aday varsa daha iyi olanı `chat` olarak bırak.
3. Sonucu ve seçilen modeli README'nin "Azure kaynakları" bölümüne bir satırla yaz.

**Bitti sayılır:** Rapor 9/9; README güncel.

---

## B. Backend (FastAPI'yi yazan kişi)

Ön koşul: `backend/` iskeleti ve `/api/health` var (F0).

**Veri kaynağı:** tüm veri `datav2/*.json` dosyalarından okunur; bu adımda SQL kullanılmaz.

### B1 · Ayarlar (15 dk)
`app/config.py` (`pydantic-settings`) alanları: `azure_openai_endpoint`, `azure_openai_api_key` (opsiyonel), `chat_deployment="chat"`, `demo_now` (opsiyonel), `data_dir` (varsayılan: repodaki `datav2/`). `.env.example`'a yalnızca `<PLACEHOLDER>`.

> 🤖 Copilot: *"backend/app/config.py'ye şu ayarları ekle: … Hiçbir varsayılan değer secret içermesin. .env.example'ı `<PLACEHOLDER>` ile güncelle."*

**Bitti sayılır:** `uv run pytest` ve `uv run ruff check .` yeşil.

### B2 · Veri okuma (30 dk)
`app/repositories/datastore.py`: `DATA_DIR` altındaki JSON'ları uygulama açılırken **bir kez** yükler, bellekte tutar (salt okunur).
- Bu adımda gerekenler: `screens.json`, `institutions.json`, `institution_screens.json`, `customers.json` (müşteri no kontrolü ve ad soyad listesi için).
- Dosya bulunamazsa ya da JSON bozuksa uygulama açılışta anlaşılır bir hatayla durur.

`app/repositories/catalog.py` (datastore'u kullanır):
- Ekranlar ve kurumlar koda göre sıralı.
- Yardımcılar: `screens_text()` → `KOD · Ad — description` satırları; `institutions_text()` → `KOD · Ad (bill_type)`; `screen_codes()`, `institution_codes()`, `screens_for_institution(code)`.

`customer_exists(number)`: `customers.json`'dan oluşturulan küme ile kontrol.

**Deploy notu:** `datav2/*.json` backend paketine girmeli. CI'daki build adımı JSON'ları `backend/data/` altına kopyalar; App Settings'te `DATA_DIR=data`. Dosyalar repoda zaten var, ek gizli bilgi yok.

**Bitti sayılır:** Birim testi: 9 ekran, 16 kurum, 40.005 müşteri; `screens_for_institution("GAZ02") == ["ODMTTLMT"]`; `customer_exists("10000004")` doğru, `customer_exists("99999999")` yanlış.

### B3 · KVKK maskeleme (45 dk)
`app/services/kvkk.py`: `mask(text) -> MaskResult(text, findings)` ve `scan(text) -> list[Finding]`. Tablo: `m1-adim-1-basit.md` §5.
- TCKN algoritması, Luhn, IBAN mod-97 kodda; regex tek başına yetmez.
- 8 haneli müşteri numarası maskelenmez.
- Ad soyad listesi `datav2/customers.json` ad/soyadlarından (datastore).

> 🤖 Copilot: *"app/services/kvkk.py yaz: TCKN (algoritma), telefon, @ornek.test dışı e-posta, IBAN (mod-97), kart (Luhn), ad soyad listesi, IP. Bulguları etiketle değiştir. 8 haneli sayıyı maskeleme. tests/test_kvkk.py ile her tür için olumlu ve olumsuz örnek."*

**Bitti sayılır:** `tests/test_kvkk.py` yeşil; geçerli TCKN maskelenir, algoritmayı geçmeyen 11 hane maskelenmez; `datav2/inbound_emails.json`'da yalnızca EML-0032 bulgu verir.

### B4 · LLM istemcisi (45 dk)
`app/clients/llm.py`:
- `azure_client.py` yapısı: `OpenAI(base_url=f"{endpoint}/openai/v1")`. Anahtar yoksa `azure-identity` ile token.
- `chat_json(prompt_name, variables, schema_model, json_schema) -> BaseModel`:
  - `prompts/<ad>.md` dosyasını okur, `## system` ve `## user` bloklarını ayırır, `{{değişken}}`leri doldurur.
  - `response_format = json_schema (strict)`, `temperature=0`, `max_tokens=300`, zaman aşımı 10 sn.
  - Pydantic doğrulaması başarısızsa 1 kez tekrar; yine olmazsa `LLMError`.
  - Süre ve token sayısını loglar; **mesaj metnini loglamaz**.
- `FakeLLMClient`: prompt adı + mesaja göre sabit JSON döner (testler için).
- Bağımlılık enjeksiyonu: servisler istemciyi parametre olarak alır (global değişken yok).

**Bitti sayılır:** Fake istemciyle prompt yükleme, değişken doldurma ve yeniden deneme testleri yeşil.

### B5 · Modeller (15 dk)
`app/models/clues.py`:
- `ExtractedClues`: AI çıktısı (`m1-adim-1-basit.md` §4 alanları).
- `Clues`: kontrol edilmiş sonuç + `masked: bool`, `extraction_method: "ai" | "fallback"`.
- `build_json_schema(catalog)`: §4 şemasını üretir; `screen_codes` ve `institution_code` enum'ları katalogdan.

**Bitti sayılır:** Şema testi: enum'larda 9 ekran ve 16 kurum var.

### B6 · İpucu servisi (60 dk)
`app/services/clues.py` → `extract_clues(message, user, now, llm, catalog) -> Clues`:
1. Boşsa AI çağırma; 1.000 karakterde kırp; `<` `>` temizle.
2. `kvkk.mask` → ikinci `scan` bulgu verirse `KvkkBlocked` hatası.
3. `llm.chat_json("varlik-cikar", {...}, ExtractedClues, schema)`.
4. Kontroller: `m1-adim-1-basit.md` §6 tablosu (müşteri no `customers.json`'da var mı dahil).
5. `LLMError` ya da zaman aşımında yedek yol (regex) → `extraction_method="fallback"`.

Ek: `backend/scripts/eval_clues.py` (backend kodunu import ettiği için backend içinde): §7'deki 1–9 numaralı mesajları **gerçek** Foundry'ye gönderir, beklenenle karşılaştırır, doğru sayısı ve süreyi yazar (A4'te kullanılır; CI'da çalışmaz).

**Bitti sayılır:** `tests/test_clues.py`: §7'deki 10 test `FakeLLMClient` ile yeşil.

### B7 · Geçici uç (20 dk)
`POST /api/mercek/assist` içinde şimdilik yalnızca bu adım: girdi `{message}`, kullanıcı oturumdan; çıktı `Clues` JSON'u. Pydantic ile girdi doğrulama (uzunluk sınırı). 2. adım eklenince aynı uç genişler.

**Bitti sayılır:** Yerelde `uv run uvicorn app.main:app --reload` → `/docs`'tan örnek 3 gönderilince `GAZ02 · ODMTTLMT · 2026-10-16 16:30–17:30` dönüyor (`DEMO_NOW=2026-10-17T12:10`).

### B8 · PR (15 dk)
1. `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest` → hepsi yeşil; çıktıyı PR açıklamasına ekle.
2. PR kontrol listesi: secret yok · CodeQL dosyası değişmedi · mesaj metni loglanmıyor · testlerde gerçek Foundry çağrısı yok.
3. CI yeşil olunca merge.

---

## Sıra ve paralellik

| Zaman | Foundry kişisi | Backend kişisi |
|---|---|---|
| 0:00 – 0:30 | A1, A2 | B1, B2 |
| 0:30 – 1:15 | A3 | B3 |
| 1:15 – 2:30 | (2. adım hazırlığı: AI Search) | B4, B5, B6 |
| 2:30 – 3:00 | A4 (B6 ile birlikte) | B7, B8 |

**Takılırsanız:** Foundry 401/403 → A3'teki rol ya da anahtar · "json_schema" / "response_format" hatası → model structured outputs desteklemiyor, A2'de başka model · `DATA_DIR` bulunamadı → yerelde `backend/.env`'de `DATA_DIR=../datav2`.
