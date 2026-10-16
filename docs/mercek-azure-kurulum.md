# Mercek — Azure Kurulum Adımları (SQL, Foundry, AI Search, Eşitleme)

Bu doküman, `mercek-sql-search-esitleme.md`'deki otomatik eşitlemenin çalışması için Azure'da **neyin, hangi sırayla** kurulacağını anlatır. Elle kurulan üç kaynak vardır: **Azure SQL**, **AI Foundry** ve **AI Search**. **Indexer portalda kurulmaz**; `load_all.py --search` komutu kendisi oluşturur. Toplam süre yaklaşık 45–60 dakikadır.

Portal menü adları zamanla küçük farklılıklar gösterebilir; aşağıda en yakın adlar verilmiştir.

```
Resource group → SQL (Entra admin + Azure erişimi) → Foundry (chat + embedding)
→ AI Search (Basic + kimlik açık) → roller (Search→Foundry, Search→SQL)
→ load_all --sql → load_all --search (indexer kendiliğinden kurulur) → validate
```

---

## Adım 0 — Ön kontrol (5 dk)

1. Tüm kaynakları takıma verilen **resource group** içinde oluştur (kılavuz kuralı).
2. Resource group → **Access control (IAM) → View my access**: rolün **Owner** veya **User Access Administrator** mı? Değilse rol atayamazsın; "yedek yol" adımlarını uygula.
3. **Tek bölge** seç, tüm kaynaklar orada olsun. Foundry'de kullanacağın modellerin o bölgede bulunduğunu model kataloğunda kontrol et.

---

## Adım 1 — Azure SQL (10–15 dk)

Portal → *Create a resource* → **SQL Database**

| Alan | Değer |
|---|---|
| Database name | `mercek` |
| Server | *Create new* → `mercek-sql-<takım>` · aynı bölge |
| Authentication | **Use both SQL and Microsoft Entra authentication** → Entra admin: kendi hesabın · SQL admin kullanıcı/şifre (yedek yol için; paylaşma, repoya yazma) |
| Compute + storage | **Basic** (2 GB) ya da **Standard S0** (veri 100 MB'ın altında). *Serverless* seçilirse otomatik duraklatma kapatılmalı, yoksa demoda ilk istek gecikir |
| Backup redundancy | Locally-redundant |

**Networking:**

- Connectivity: **Public endpoint**
- **Allow Azure services and resources to access this server: Yes** (AI Search ve App Service için)
- **Add current client IP address: Yes** (VDI makinesi için)

**Kontrol:** veritabanı → **Query editor** → Entra hesabıyla gir → `SELECT 1`.

---

## Adım 2 — Azure AI Foundry ve modeller (10 dk)

1. Portal'da ya da ai.azure.com'da **Azure AI Foundry** kaynağı ve proje oluştur (aynı bölge).
2. **Models + endpoints → Deploy model** ile iki model kur:

| Deploy adı | Model | Not |
|---|---|---|
| `chat` | Bölgede bulunan küçük ve ucuz bir sohbet modeli (ör. gpt-4o-mini sınıfı) | Mercek'in yazdığı tüm metinler |
| `embedding` | `text-embedding-3-small` (1536 boyut) | Başka model seçilirse `EMBEDDING_MODEL` ve `EMBEDDING_DIM` buna göre ayarlanır |

Ardından **Endpoint** adresini not et (`https://<ad>.openai.azure.com`).

**Kontrol:** Playground'da `chat` modeline bir soru sor, cevap gelsin.

---

## Adım 3 — Azure AI Search (10 dk)

Portal → *Create a resource* → **Azure AI Search**

| Alan | Değer |
|---|---|
| Service name | `mercek-search-<takım>` |
| Location | aynı bölge |
| Pricing tier | **Basic** (Free katmanda kimlik desteği ve kapasite kısıtlı; indexer + embedding için uygun değil) |

Oluşunca:

1. **Identity → System assigned → On → Save** (Search, SQL'i ve Foundry'yi şifresiz kullanabilsin).
2. **Keys → API access control → "Both"** (rol tabanlı + API anahtarı).

**Kontrol:** Overview → **URL**'yi not et (`https://mercek-search-<takım>.search.windows.net`).

---

## Adım 4 — Yetkiler (10 dk)

**4a. Foundry'de Search'e rol ver:** Foundry kaynağı → **Access control (IAM) → Add role assignment**

- Rol: **Cognitive Services OpenAI User**
- Assign access to: **Managed identity** → *Search service* → `mercek-search-<takım>`

**4b. SQL'de Search'e okuma izni:** SQL veritabanı → **Query editor**, **Entra admin** hesabıyla:

```sql
CREATE USER [mercek-search-<takım>] FROM EXTERNAL PROVIDER;
ALTER ROLE db_datareader ADD MEMBER [mercek-search-<takım>];
GRANT VIEW CHANGE TRACKING ON SCHEMA::dbo TO [mercek-search-<takım>];
```

**4c. Betikleri çalıştıracak kendi hesabına** (anahtar kullanılacaksa atlanabilir):

- Search: **Search Service Contributor** ve **Search Index Data Contributor**
- Foundry: **Cognitive Services OpenAI User**

**Yedek yol (rol atanamıyorsa):** 4a ve 4c yerine anahtarlar (Foundry *Keys and Endpoint*, Search *Keys* → admin key), 4b yerine SQL admin kullanıcı/şifre. Bunlar yalnızca terminalde ortam değişkeni olarak durur; repoya girmez.

---

## Adım 5 — Komutları çalıştıracak makine (5–10 dk)

VDI'da ya da kendi makinende:

```bash
pip install pyodbc azure-identity        # ODBC Driver 18 for SQL Server da kurulu olmalı
az login                                 # kurumsal hesapla

export SQL_SERVER=mercek-sql-<takım>.database.windows.net SQL_DATABASE=mercek
export SQL_RESOURCE_ID=$(az sql server show -g <resource-group> -n mercek-sql-<takım> --query id -o tsv)
export SEARCH_ENDPOINT=https://mercek-search-<takım>.search.windows.net
export AZURE_OPENAI_ENDPOINT=https://<foundry>.openai.azure.com
export EMBEDDING_DEPLOYMENT=embedding EMBEDDING_MODEL=text-embedding-3-small EMBEDDING_DIM=1536
# Yedek yolda ek olarak: SQL_USER, SQL_PASSWORD, SEARCH_API_KEY, AZURE_OPENAI_API_KEY,
#   SEARCH_SQL_CONNECTION="Server=tcp:...;Database=mercek;User ID=...;Password=...;Encrypt=True"
```

---

## Adım 6 — Yükle, eşitle, doğrula (5 dk)

ZtHackathonStudyWithData kopyasında:

```bash
python3 tools/mercek_data/load_all.py --sql       # 15 tablo + değişiklik takibi
python3 tools/mercek_data/load_all.py --search    # veri kaynağı, skillset, indeks, indexer → ilk eşitleme
python3 tools/mercek_data/demo_reset.py --sql --sync-search
python3 tools/mercek_data/validate_scenarios.py --sql --search --eval
```

**Portalda kontrol:**

- Search → **Indexers**: 3 indexer, son çalışma **Success**
- **Indexes**: solutions 37 · requests 95 · announcements 20 belge
- **Search explorer**: `Başkentgaz yanıt alınamadı` → SOL-031 üstte

---

## Adım 7 — Uygulama için (App Service kurulunca)

`mercek-api` App Service → **Identity → System assigned → On**, sonra:

| Kaynak | İzin |
|---|---|
| SQL (Query editor) | `CREATE USER [mercek-api] FROM EXTERNAL PROVIDER;` · `ALTER ROLE db_datareader ADD MEMBER [mercek-api];` · `ALTER ROLE db_datawriter ADD MEMBER [mercek-api];` |
| AI Search | **Search Index Data Reader** (uygulama indexer'ı hemen çalıştıracaksa ek olarak **Search Service Contributor**) |
| Foundry | **Cognitive Services OpenAI User** |
| App Settings | `SQL_SERVER`, `SQL_DATABASE`, `SEARCH_ENDPOINT`, `AZURE_OPENAI_ENDPOINT`, `CHAT_DEPLOYMENT=chat`, `EMBEDDING_DEPLOYMENT=embedding`, `MATCH_THRESHOLD=0.75` |

---

## Sık takılınan yerler

| Belirti | Neden | Çözüm |
|---|---|---|
| `CREATE USER … FROM EXTERNAL PROVIDER` hata veriyor | Query editor'e SQL kullanıcısıyla girildi | Entra admin hesabıyla gir |
| Indexer: `Login failed for user '<token-identified principal>'` | 4b yapılmadı ya da Search kimliği kapalı | Adım 3 (Identity) ve 4b |
| Skillset 401/403 | Foundry rolü (4a) yok | 4a ya da `AZURE_OPENAI_API_KEY` |
| SQL bağlantı zaman aşımı | Güvenlik duvarı | Adım 1 Networking |
| `Vector dimension mismatch` | `EMBEDDING_DIM` modelle uyuşmuyor | Deploy'daki modele göre düzelt, `--search` tekrar |

Ayrıntılı eşitleme bilgisi ve sorun giderme: `mercek-sql-search-esitleme.md`.
