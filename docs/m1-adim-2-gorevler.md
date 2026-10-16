# M1 · 2. adım — Görev listesi (Foundry/Search + Backend)

> Tasarım: [`m1-adim-2-basit.md`](m1-adim-2-basit.md). Önce 1. adımın görevleri bitmiş olmalı: [`m1-adim-1-gorevler.md`](m1-adim-1-gorevler.md).
> Her görevin **Bitti sayılır** satırı sağlanmadan sonrakine geçmeyin. Repoya anahtar, endpoint değeri yazılmaz (`<PLACEHOLDER>`).

---

## A. Foundry ve AI Search (Azure tarafını kuran kişi)

### A5 · `embedding` modelini deploy et (10 dk)
1. Foundry → **Deploy model** → `text-embedding-3-small`. Deploy adı: **`embedding`**.
2. `mercek-api` App Settings: `EMBEDDING_DEPLOYMENT=embedding`, `EMBEDDING_DIM=1536`. Başka model seçilirse boyut ona göre.

**Bitti sayılır:** Playground ya da kısa bir istekle 1536 boyutlu vektör dönüyor.

### A6 · AI Search kaynağı (10 dk)
1. Resource group'ta **Azure AI Search** `mercek-search`, aynı bölge, katman **Basic**.
2. Endpoint'i not et (`https://mercek-search.search.windows.net`); değeri repoya yazma.
3. Erişim: **ideal** `mercek-api` kimliğine **Search Index Data Reader**; kendi hesabına (betik için) **Search Service Contributor** + **Search Index Data Contributor**. **Yedek:** admin key yalnızca betiği çalıştıran terminalde ortam değişkeni (`SEARCH_API_KEY`); `mercek-api` App Settings'e **query key**.
4. `mercek-api` App Settings: `SEARCH_ENDPOINT=<endpoint>` (+ yedekte `SEARCH_API_KEY=<query key>`).

**Bitti sayılır:** Portal'da kaynak var; App Settings tamam.

### A7 · İndeksi doldur (15 dk, B9 bittikten sonra)
```bash
export SEARCH_ENDPOINT=<PLACEHOLDER> AZURE_OPENAI_ENDPOINT=<PLACEHOLDER>
export EMBEDDING_DEPLOYMENT=embedding EMBEDDING_DIM=1536
# yedek yolda: export SEARCH_API_KEY=<admin key> AZURE_OPENAI_API_KEY=<key>   (yalnızca terminalde)
python scripts/index_kibana_logs.py
```
**Bitti sayılır:** Portal → Indexes → `kibana_logs` **2.002** belge. Search explorer'da `13 hane abone` → üstte `110412 · SU01` logları.

---

## B. Backend

### B9 · İndeks betiği (45 dk)
`scripts/index_kibana_logs.py` (`m1-adim-2-basit.md` §3):
- İndeksi siler ve yeniden kurar (alanlar §3 tablosu, Türkçe analizör, HNSW cosine).
- `datav2/kibana_logs.json` → Warning/Error, `institution_code` / `error_code` `message_fields` ve `message_response`'tan.
- `search_text` → `embedding` ile vektör (16'lı partiler, hata olursa 3 kez yeniden dene).
- 500'lük partilerle yükler; sonda belge sayısını yazar.
- Kimlik: `DefaultAzureCredential`, yoksa ortamdaki anahtar. Anahtar loglanmaz.

> 🤖 Copilot: *"scripts/index_kibana_logs.py yaz: azure-search-documents ile `kibana_logs` indeksini (alanlar: …) sil-kur, datav2/kibana_logs.json'dan Warning/Error kayıtları al, search_text'i Azure OpenAI embedding ile vektörle, 500'lük partilerle yükle. Değerler ortam değişkeninden."*

**Bitti sayılır:** `--dry-run` seçeneği Azure'a gitmeden 2.002 belge hazırladığını ve örnek bir belgeyi yazıyor.

### B10 · Search istemcisi ve `embed` (30 dk)
- `app/clients/llm.py` → `embed(texts) -> list[list[float]]` (`EMBEDDING_DEPLOYMENT`).
- `app/clients/search.py` → `SearchClient.hybrid(index, text, vector, filter, top)`; `FakeSearchClient`: bellekteki `kibana_logs.json` üzerinde aynı filtre ve basit kelime eşleşmesi.
- Ayarlar: `search_endpoint`, `search_api_key` (opsiyonel), `embedding_deployment`.

**Bitti sayılır:** Fake istemciyle filtre testleri yeşil.

### B11 · Log deposu (30 dk)
`app/repositories/logs.py`:
- `build_filter(clues, user_name, now, widen)` → OData metni. Değerler yalnızca doğrulanmış fiş alanlarından; tek tırnak ikilenir; tarih aralığı `DEMO_NOW`'u geçmez.
- `search(clues, filter)` → hibrit sorgu, `top=20`.
- Yedek yol: Search hata verirse aynı filtre bellekteki JSON'a uygulanır.

**Bitti sayılır:** `build_filter` testleri: kullanıcı / müşteri / ekran / kurum / saat kombinasyonları ve `O'Brien` gibi tırnaklı değer kaçışlanıyor.

### B12 · Log bulucu (45 dk)
`app/services/log_finder.py` → `find_log(clues, user, now, search) -> LogMatch` (§2 akışı):
1. 1. tur: müşteri no varsa `customer_id`, yoksa `user_name`; sonuç yoksa saat aralığı kaldırılır (`widened`).
2. Sonuçları `signature`'a göre grupla → 1 grup `own` (en son log, `count` = o gün bu türdeki log sayısı) · birden fazla `choose` (en yeni 3 grup).
3. Kendi logu yok ve fişte ekran ya da kurum varsa 2. tur: kullanıcı filtresi yok, son 7 gün → en çok tekrarlanan grup `related`.
4. Hiçbiri yoksa `none`.
5. `selected_signature` geldiyse arama yapmadan o grubu `own` olarak döner.

Modeller: `app/models/logs.py` → `Signature`, `LogMatch`.

**Bitti sayılır:** `tests/test_log_finder.py`: `m1-adim-2-basit.md` §6'daki 7 test yeşil.

### B13 · Uca bağla (20 dk)
`POST /api/mercek/assist`: girdi `{message, selected_signature?}` → 1. adım (fiş) → 2. adım (`LogMatch`) → yanıt `{clues, log_match}`. `intent = durum_ozeti` ise şimdilik `log_match` boş.

**Bitti sayılır:** Yerelde `DEMO_NOW=2026-10-17T09:15+03:00`, kullanıcı `elif`, mesaj "Az önce Başkentgaz talimatında kurumdan yanıt alamadım" → `mode: own · 110731 · GAZ02 · count 8`.

### B14 · PR (15 dk)
`ruff check`, `ruff format --check`, `pytest` yeşil; testlerde gerçek Search/Foundry çağrısı yok; anahtar yok; CodeQL dosyası değişmedi.

---

## Sıra

| Zaman | Azure kişisi | Backend kişisi |
|---|---|---|
| 0:00 – 0:30 | A5, A6 | B9 |
| 0:30 – 1:00 | A7 (B9 hazır olunca) | B10 |
| 1:00 – 2:15 | (3. adım hazırlığı) | B11, B12 |
| 2:15 – 2:45 | B13'ü birlikte dene | B13, B14 |

**Takılırsanız:** Search 403 → A6 rolleri ya da anahtar · `Vector dimension mismatch` → `EMBEDDING_DIM` modelle aynı değil · indeks boş → A7 çıktısındaki hata satırı · Search hiç yoksa backend yedek yolla (bellekte filtre) çalışmaya devam eder.
