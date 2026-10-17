# AI Search'ü portaldan elle kurma (build_search_index.py olmadan)

`scripts/build_search_index.py` bu klasördeki 8 JSON'u AI Search'e gönderir. Betik çalışmıyorsa aynı tanımları
portalda **JSON olarak yapıştırarak** kurabilirsiniz; sonuç birebir aynıdır (alan adları kodla uyumlu).

| Dosya | Portalda (AI Search hizmeti → Arama yönetimi / Search management) |
|---|---|
| `*-1-veri-kaynagi.json` | **Veri kaynakları (Data sources)** → **+ Veri kaynağı ekle (JSON) (Add data source (JSON))** |
| `*-2-indeks.json` | **Dizinler (Indexes)** → **+ Dizin ekle (Add index)** → **Dizin ekle (JSON) (Add index (JSON))** |
| `*-3-beceri-kumesi.json` | **Beceri kümeleri (Skillsets)** → **+ Beceri kümesi ekle (Add skillset)** (JSON düzenleyici açılır) |
| `*-4-indexer.json` | **Dizin oluşturucular (Indexers)** → **+ Dizin oluşturucu ekle (JSON) (Add indexer (JSON))** |

Önce `mercek-loglar-*` (hata_ara), sonra `mercek-cozumler-*` (benzer_cozum_ara); her biri **1 → 2 → 3 → 4** sırasıyla.
"Verileri içeri aktar ve vektörleştir (Import and vectorize data)" sihirbazını **kullanmayın**: kendi alan adlarını üretir, kod bulamaz.

## 0. SQL görünümleri (bir kez)

SQL veritabanı → **Sorgu düzenleyicisi (Query editor)** → `db/search_views.sql` içeriğini çalıştırın
(`load_sql.py` çalıştıysa zaten vardır). Query editor `GO` satırını tanımazsa `GO` ile ayrılmış her bloğu ayrı çalıştırın.
Kontrol: `SELECT COUNT(*) FROM dbo.v_hata_turleri;` → 107, `SELECT COUNT(*) FROM dbo.v_cozum_sablonlari;` → 37.

## 1. Yer tutucuları doldurun (yapıştırmadan önce)

| Yer tutucu | Nereden |
|---|---|
| `<SQL-SUNUCU>` | SQL sunucusu adı (`.database.windows.net` öncesi) |
| `<SQL-KULLANICI>`, `<SQL-PAROLA>` | SQL kimlik doğrulaması kullanıcısı (sunucu yöneticisi ya da `db_datareader` yetkili kullanıcı) |
| `<FOUNDRY-KAYNAK>` | Foundry → embedding deploy'u → **Hedef URI (Target URI)** başı: `https://<ad>.openai.azure.com` (ya da `https://<ad>.cognitiveservices.azure.com`); sonunda `/openai/...` olmasın |
| `<FOUNDRY-API-ANAHTARI>` | Foundry kaynağı → **Anahtarlar ve uç nokta (Keys and Endpoint)** → Anahtar 1 |

`text-embedding-3-small` deploy adınız farklıysa `deploymentId` ve `modelName` değerlerini değiştirin.
Doldurulmuş JSON'ları **repoya commit etmeyin** (parola/anahtar içerir); yalnızca portala yapıştırın.

### Parola/anahtar vermek istemiyorsanız (Managed Identity)
- AI Search → **Kimlik (Identity)** → Sistem tarafından atanan **Açık (On)**.
- SQL: Query editor'da (Entra yöneticisiyle) çalıştırın:
  ```sql
  CREATE USER [<search-hizmeti-adı>] FROM EXTERNAL PROVIDER;
  ALTER ROLE db_datareader ADD MEMBER [<search-hizmeti-adı>];
  ```
  Veri kaynağındaki `connectionString` şöyle olur:
  `Database=mercekdb;ResourceId=/subscriptions/<ABONELIK-ID>/resourceGroups/<KAYNAK-GRUBU>/providers/Microsoft.Sql/servers/<SQL-SUNUCU>;Connection Timeout=30;`
- Foundry: Foundry kaynağı → **Erişim denetimi (IAM)** → rol **Cognitive Services OpenAI User** → Yönetilen kimlik → AI Search hizmeti.
  Sonra beceri kümesi ve indeksteki `"apiKey": ...` satırlarını silin.
- Rol atamalarının etkinleşmesi 5–10 dk sürebilir. Ücretsiz katmanda sistem kimliği bulunmayabilir; o durumda parola/anahtarla devam edin.

## 2. Kontrol

- Indexer oluşturulunca **bir kez kendiliğinden çalışır**, sonra 5 dakikada bir.
  **Dizin oluşturucular (Indexers)** → `mercek-loglar-indexer` → **Yürütme geçmişi (Execution history)**: Başarılı (Success), 107 belge.
  `mercek-cozumler-indexer` → 37 belge.
- **Dizinler (Indexes)** → `mercek-loglar` → **Arama gezgini (Search explorer)** → `abone` → **Ara (Search)** → sonuç gelmeli.
- Hata: "Credentials ... invalid" → SQL kullanıcı/parola ya da güvenlik duvarı (SQL sunucusu → Ağ (Networking) →
  **Azure hizmetlerinin erişimine izin ver (Allow Azure services ...)** işaretli olmalı). "401/403 ... embedding" → Foundry adresi/anahtarı/rol.
- Zamanlamayı kapatmak için: indexer → **Zamanlama (Schedule)** → **Bir kez (Once)**.

## 3. Uygulamaya bağlayın

API App Service → **Ortam değişkenleri (Environment variables)**: `SEARCH_ENDPOINT=https://<search>.search.windows.net`,
`SEARCH_LOG_INDEX=mercek-loglar`, `SEARCH_SOLUTION_INDEX=mercek-cozumler` (anahtar ya da Managed Identity: `docs/AZURE-AI-SEARCH.md` §4–5).

JSON'lar `backend/app/services/log_index.py` ve `solution_index.py` tanımlarından üretildi; kod değişirse yeniden üretilmeli.
