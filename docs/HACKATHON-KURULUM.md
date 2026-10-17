# Mercek — Hackathon ortamına kurulum (baştan sona kontrol listesi)

> Kişisel abonelikte provası yapılan kurulumun hackathon aboneliğine **sırayla** taşınması. Her adımın ayrıntısı ilgili
> rehberde; burada sıra, girilecek değerler ve provada yaşanan tuzaklar var. Tahmini süre: **~2 saat** (bekleme süreleri dahil).
> **Repoya anahtar/parola yazılmaz**: değerler yalnızca `backend\.env` (git'e girmez) ve App Service → Ortam değişkenleri.

| Rehber | Konu |
|---|---|
| `docs/AZURE-APP-SERVICE.md` | App Service planı, `<api>`, `<web>`, paketleme ve yükleme |
| `docs/AZURE-SQL.md` | Azure SQL, veri yükleme, Managed Identity, uygulama tabloları |
| `docs/AZURE-AI-SEARCH.md` | AI Search, `mercek-loglar` ve `mercek-cozumler` indeksleri, MI |
| `docs/FOUNDRY-AGENT.md` | Foundry projesi, `mercek-cagri` agent'ı, izleme (App Insights) |
| `docs/MERCEK-TEST-SORULARI.md` | Kurulum sonrası deneme soruları ve beklenen cevaplar |
| `docs/COPILOT-MERCEK-PROMPTLARI.md` | Kodu hackathon reposunda Copilot'a yazdırmak için sistem talimatı ve faz istemleri |

---

## 0. Değerleri topla (10 dk) — bu tabloyu doldurarak ilerleyin

| Kısaltma | Ne | Nereden | Prova değeri (örnek) |
|---|---|---|---|
| `<rg>` | Resource group | Takıma verilen (başka yerde kaynak açılmaz) | `rg-mercek` |
| `<bölge>` | Bölge | Foundry ile aynı bölge | Sweden Central |
| `<takım>` | Ad eki | Adlar Azure genelinde benzersiz olmalı | `seyhan` |
| `<kiracı>` | Kiracı (tenant) kimliği | Portal → Microsoft Entra ID → Genel Bakış → Kiracı Kimliği | `08477593-…` |
| `<foundry>` | Foundry kaynağı | Takıma verilen ya da açılan | `seyhanamasyali-7898-resource` |
| `<proje>` | Foundry projesi | ai.azure.com → proje → Genel bakış | `seyhanamasyali-7898` |
| `<openai-uç>` | Model uç noktası | Foundry → model → Uç noktayı görüntüle | `https://<foundry>.openai.azure.com/openai/v1` |
| `<proje-uç>` | Proje uç noktası | ai.azure.com → proje → Genel bakış → Proje uç noktası | `https://<foundry>.services.ai.azure.com/api/projects/<proje>` |
| `<api>` / `<web>` | App Service adları | §4'te oluşturulur | `mercek-api-<takım>` / `mercek-web-<takım>` |
| `<api-adres>` | Backend adresi | `<api>` → Genel Bakış → Varsayılan etki alanı (rastgele ekli olabilir) | `mercek-api-seyhan-agczfxe0…azurewebsites.net` |
| `<web-adres>` | Frontend adresi | `<web>` → Genel Bakış → Varsayılan etki alanı | `mercek-web-seyhan-hhfmcnb2…azurewebsites.net` |
| `<sql>` | SQL sunucusu | §2'de oluşturulur | `mercek-sql-<takım>` |
| `<search>` | AI Search hizmeti | §3'te oluşturulur | `mercek-search-<takım>` |

Foundry'de iki **model dağıtımı** gerekir (adları aynen böyle olursa ayar değiştirmek gerekmez):
`gpt-5.5` (sohbet/agent) ve `text-embedding-3-small` (AI Search vektörleri). Farklı adlar → `CHAT_DEPLOYMENT`, `EMBEDDING_DEPLOYMENT`.

## 1. Bilgisayar hazırlığı (10 dk)

```cmd
cd /d c:\Seyhan\ZTHackhton\niha
git checkout main
git pull
uv sync --directory backend
```
- Azure CLI yoksa: `winget install -e --id Microsoft.AzureCLI` → **yeni** CMD penceresi.
- Hackathon kiracısına giriş (MFA tarayıcıda): `az login --tenant <kiracı>` → abonelik sorulursa hackathon aboneliğini seçin.
  Kontrol: `az account show --query "{abonelik:name, kiraci:tenantId}" -o table`.
- **`backend\.env`'i ayırın:** kişisel ortamın dosyasını saklayın, hackathon için yenisini açın:
  ```cmd
  copy backend\.env backend\.env.kisisel
  copy backend\.env.example backend\.env
  ```
  Kişisel ortama dönmek için `copy /y backend\.env.kisisel backend\.env`. (`.env*` git'e girmez.)
  Aşağıdaki adımlarda `backend\.env`'e eklenecek satırlar her adımda yazılı; tam liste §8'de.

## 2. Azure SQL (20 dk) — `docs/AZURE-SQL.md`

1. **§1** Veritabanı `mercekdb`, sunucu `<sql>`, kimlik doğrulama **SQL + Microsoft Entra** (Entra yöneticisi: kendi hesabınız).
   Katman **Basic (5 DTU)** (§1.1; ücretsiz teklifi uygulamayın — indexer 5 dk'da bir bağlandığı için).
   Ağ: **Azure hizmetlerine izin ver: Evet**, **istemci IP'nizi ekle: Evet**.
2. `backend\.env`:
   ```
   SQL_SERVER=<sql>.database.windows.net
   SQL_DATABASE=mercekdb
   SQL_USER=mercekadmin
   SQL_PASSWORD=<parola>
   ```
   (`SQL_USER/SQL_PASSWORD` yerelde kalır: AI Search indexer'ı SQL'e bunlarla bağlanır.)
3. Veri + uygulama tabloları:
   ```cmd
   uv run --directory backend python ..\scripts\load_sql.py
   uv run --directory backend python ..\scripts\setup_app_tables.py
   ```
   Beklenen: `✓ Kontrol: 21 tablo; … 2002 hata logu, 700 çağrı` ve `✓ Tablolar hazır …` + elif/zeynep/kerem.

## 3. AI Search (20 dk) — `docs/AZURE-AI-SEARCH.md`

1. **§1** Foundry'de `text-embedding-3-small` dağıtımı.
2. **§2** AI Search `<search>`: katman **Ücretsiz** (indeks sınırı 3; Mercek 2 kullanır) ya da verilmişse Basic.
   **Bölgede kapasite yoksa** ("out of the resources") başka bölgede açın (provada Sweden Central dolu, Norway East kullanıldı) —
   arama başka bölgede olabilir. Anahtarlar → API erişim denetimi: **Her ikisi**.
3. `backend\.env`:
   ```
   SEARCH_ENDPOINT=https://<search>.search.windows.net
   SEARCH_API_KEY=<yönetici anahtarı>
   SEARCH_LOG_INDEX=mercek-loglar
   SEARCH_SOLUTION_INDEX=mercek-cozumler
   AZURE_OPENAI_ENDPOINT=<openai-uç>
   AZURE_OPENAI_API_KEY=<Foundry anahtarı>
   EMBEDDING_DEPLOYMENT=text-embedding-3-small
   ```
4. İki indeksi birden kur:
   ```cmd
   uv run --directory backend python ..\scripts\build_search_index.py --indeks hepsi
   ```
   Beklenen: `mercek-loglar` 107 belge, `mercek-cozumler` 37 belge ve iki örnek arama.
   Eşik kontrolü: `…build_search_index.py --dene "adres değişikliği yapamıyorum, alan hatası veriyor"` → `✓ SOL-026 %8x`.

## 4. App Service (30 dk) — `docs/AZURE-APP-SERVICE.md` §1–§3

Plan (Linux, B1), `<api>` (Python 3.12, başlangıç: `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`),
`<web>` (Node 22, başlangıç: `node server.js`). **`<api-adres>` ve `<web-adres>`'i Genel Bakış'tan kopyalayın** (rastgele ek olabilir).
Ortam değişkenlerini şimdi değil §7'de toplu girin.

## 5. Foundry projesi ve agent (15 dk) — `docs/FOUNDRY-AGENT.md`

1. **§1** ai.azure.com → `<foundry>` altında proje (yoksa oluşturun) → `<proje-uç>`'u kopyalayın. Projede `gpt-5.5` görünmeli.
2. **§2** Kendi hesabınızın `<foundry>` üzerinde rolü (kaynağı siz açtıysanız genelde var; `setup_agent.py` 403 verirse ekleyin).
3. `backend\.env`:
   ```
   FOUNDRY_PROJECT_ENDPOINT=<proje-uç>
   FOUNDRY_AGENT_NAME=mercek-cagri
   ```
   **Adresi kopyala-yapıştır** yapın (provada sondaki bir rakam eksik yazıldı → `404 The project does not exist`).
4. Agent:
   ```cmd
   uv run --directory backend python ..\scripts\setup_agent.py
   ```
   Beklenen: `✓ Agent 'mercek-cagri' sürüm 1 · model gpt-5.5 · araçlar: kibana_sorgula, cagri_ara, hata_ara, benzer_cozum_ara`.
5. **§4.1** İzleme: ai.azure.com → Aracılar → `mercek-cagri` → İzleme → **Bağla** → yeni App Insights,
   kimlik türü **Proje Yönetilen Kimliği**.

## 6. Kimlikler ve roller (15 dk + 10 dk bekleme)

`<api>` → **Ayarlar → Kimlik** → Sistem tarafından atanan: **Açık** → Kaydet. Sonra:

| Nerede | Ne | Nasıl |
|---|---|---|
| SQL (`mercekdb` → Sorgu düzenleyicisi, **Entra ile giriş**) | `CREATE USER [<api>] FROM EXTERNAL PROVIDER;`<br>`ALTER ROLE db_datareader ADD MEMBER [<api>];`<br>`ALTER ROLE db_datawriter ADD MEMBER [<api>];` | `docs/AZURE-SQL.md` §4.2, §5.2 |
| `<search>` → Erişim denetimi (IAM) | **Search Index Data Reader** → Yönetilen kimlik → App Service → `<api>` | Türkçe portalda "Arama Dizini Veri Okuyucusu"; aramaya `Arama` yazın; "Yönetilen Uygulama…" rolünü **seçmeyin** |
| `<foundry>` → Erişim denetimi (IAM) | **Azure AI User**; listede yoksa **Cognitive Services User**; o da yoksa **Cognitive Services Data Contributor (Preview)** → Yönetilen kimlik → `<api>` | Provada Türkçe portalda ilk ikisi yoktu; **Data Contributor (Preview) ile çalıştı**. *Azure AI Developer* `403` verdi; *OpenAI User* ve *Data Reader* yetmez |

Rol atamaları **5–10 dk**'da etkinleşir; sonra `<api>` → **Yeniden başlat**.

## 7. App Service ortam değişkenleri (10 dk)

**`<api>`** → Ayarlar → Ortam değişkenleri → Uygulama ayarları (her satır ayrı, sonunda **Uygula → Onayla**):

| Ad | Değer | Not |
|---|---|---|
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` | |
| `CORS_ORIGINS` | `https://<web-adres>` | sonda `/` yok |
| `SESSION_SECRET` | uzun rastgele metin | `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `AZURE_OPENAI_ENDPOINT` | `<openai-uç>` | `chat` modu (geri dönüş) için kalır |
| `AZURE_OPENAI_API_KEY` | Foundry anahtarı | |
| `CHAT_DEPLOYMENT` | `gpt-5.5` | |
| `SQL_SERVER` | `<sql>.database.windows.net` | |
| `SQL_DATABASE` | `mercekdb` | `SQL_USER/SQL_PASSWORD` **eklemeyin** (MI) |
| `SEARCH_ENDPOINT` | `https://<search>.search.windows.net` | `SEARCH_API_KEY` **eklemeyin** (MI) |
| `SEARCH_LOG_INDEX` | `mercek-loglar` | |
| `SEARCH_SOLUTION_INDEX` | `mercek-cozumler` | |
| `LLM_MODE` | `agent` | sorun olursa `chat` |
| `FOUNDRY_PROJECT_ENDPOINT` | `<proje-uç>` | kopyala-yapıştır |
| `FOUNDRY_AGENT_NAME` | `mercek-cagri` | |

`LLM_DEBUG` eklemeyin (Azure'da kapalı kalmalı). `DEMO_NOW` varsayılanı `2026-10-17T09:15:00+03:00`.

**`<web>`**: `SCM_DO_BUILD_DURING_DEPLOYMENT=false`, `HOSTNAME=0.0.0.0`.

## 8. Paketle ve yükle (15 dk) — `docs/AZURE-APP-SERVICE.md` §4–§5

```cmd
cd /d c:\Seyhan\ZTHackhton\niha
git pull
python scripts\package_azure.py --api-url https://<api-adres>
```
Çıktıdaki **sürüm** (commit) not edilir. Portal → Cloud Shell (Bash) → önce `rm -f ~/mercek-api.zip ~/mercek-web.zip` →
**Dosyaları yönet → Karşıya yükle** (`dist\mercek-api.zip`, `dist\mercek-web.zip`) → `ls -l ~/*.zip` (saat şimdi mi) →
```bash
az webapp deploy -g <rg> -n <api> --src-path ~/mercek-api.zip --type zip
az webapp deploy -g <rg> -n <web> --src-path ~/mercek-web.zip --type zip --clean true
az webapp restart -g <rg> -n <web>
```

**Tam `backend\.env` (yerel betikler için)**:
```
AZURE_OPENAI_ENDPOINT=<openai-uç>
AZURE_OPENAI_API_KEY=<Foundry anahtarı>
CHAT_DEPLOYMENT=gpt-5.5
EMBEDDING_DEPLOYMENT=text-embedding-3-small
SQL_SERVER=<sql>.database.windows.net
SQL_DATABASE=mercekdb
SQL_USER=mercekadmin
SQL_PASSWORD=<parola>
SEARCH_ENDPOINT=https://<search>.search.windows.net
SEARCH_API_KEY=<yönetici anahtarı>
SEARCH_LOG_INDEX=mercek-loglar
SEARCH_SOLUTION_INDEX=mercek-cozumler
FOUNDRY_PROJECT_ENDPOINT=<proje-uç>
FOUNDRY_AGENT_NAME=mercek-cagri
# Yerelde agent modunda denemek için: LLM_MODE=agent
```

## 9. Kontrol (15 dk)

| # | Nerede | Beklenen |
|---|---|---|
| 1 | `https://<api-adres>/api/health` | `{"status":"ok"}` |
| 2 | `<api>` → Günlük akışı (F5) | `Veri kaynağı: Azure SQL (mercekdb) · 2002 hata logu · 700 çağrı`, `ManagedIdentityCredential` |
| 3 | `https://<web-adres>` sol üst | **sürüm** = §8'deki commit (değilse web'i `--clean true` + restart ile tekrar yükleyin, gizli pencere) |
| 4 | Elif → "ODMTTLMT ekranında hata alıyorum" | 7 hata, GAZ02 110731, SOL-031 (6 çağrı) + **▶ Akışı izle · SOL-031**; günlükte `…/responses "200 OK"` ve `ad=kibana_sorgula` |
| 5 | Aynı sohbet → "Peki nasıl çözerim?" → F5 | SOL-031 adımları; F5 sonrası konuşma geri gelir |
| 6 | Elif → "abone numarasını sistem kabul etmiyor" | günlükte `ad=hata_ara … sonuç=5` (AI Search + MI) |
| 7 | Kerem → "Müşteri güncelleme ekranında 'Input string was not in a correct format' hatası" | `ad=benzer_cozum_ara`; "hazır çözüm yok", aday adımları verilmez |
| 8 | Kerem → K8 (aktif talimat, kaç müşteri) → **Etkilenen müşteriler (31)** | Tablo; SQL'de `SELECT TOP 5 * FROM dbo.audit_log ORDER BY audit_id DESC` → `affected_customers_view` |
| 9 | ai.azure.com → Aracılar → `mercek-cagri` → İzlemeler | Çalıştırmalar ve araç adımları (5–10 dk gecikmeli) |

Diğer sorular: `docs/MERCEK-TEST-SORULARI.md`.

## 10. Provada yaşanan sorunlar (hızlı çözüm)

| Belirti | Sebep → çözüm |
|---|---|
| `az login`: MFA / "No subscriptions found" | `az login --tenant <kiracı>` |
| `'az' is not recognized` | Azure CLI kurulumundan sonra yeni CMD açın |
| Script: `Client with IP address … is not allowed` | SQL sunucusu → Ağ iletişimi → istemci IP'nizi ekleyin (IP değişince tekrar) |
| AI Search oluşturulamıyor (kapasite) | Başka bölge (Norway East çalıştı) |
| Indexer: `Login failed` | `.env`'deki `SQL_USER/SQL_PASSWORD` yanlış; `git pull` (eski betikte parola biçimi hatası vardı) |
| Yeni özellik/düğme görünmüyor | Eski frontend: `--clean true` + `az webapp restart`; sol üst sürümü kontrol |
| Sürüm eski commit | Paketlemeden önce `git pull` yapılmamış |
| F5'te konuşma gelmiyor | Frontend eski (sürüm) ya da SQL'de `db_datawriter` yok (günlükte `INSERT permission was denied`) |
| "Şu an yanıt üretilemiyor" + `404 The project does not exist` | `FOUNDRY_PROJECT_ENDPOINT` yanlış yazılmış |
| "Şu an yanıt üretilemiyor" + `403 Forbidden` (agent) | `<api>` kimliğine Foundry rolü (§6) yok/etkinleşmedi → 10 dk bekleyin, yeniden başlatın |
| "Şu an yanıt üretilemiyor" + `400 Invalid value: ''` | Eski kod; `git pull` + yeniden paketle |
| "Şu an yanıt üretilemiyor" + `turda cevap üretilemedi` | Eski kod (tur sınırı 5); güncel kodda 8 |
| `hata_ara başarısız: Arama servisi 403` | `<search>` rolü (§6) etkinleşmedi ya da API erişim denetimi "Her ikisi" değil |
| İzleme ekranı boş | App Insights bağlantısından sonraki sorular 5–10 dk sonra görünür; **İzlemeler** sekmesine bakın |

**Demo günü geri dönüş:** agent tarafında sorun → `<api>` → Ortam değişkenleri → `LLM_MODE=chat` → Uygula (1 dk).
AI Search sorunu → `SEARCH_ENDPOINT` satırını silmek araçları kapatır, sohbet `kibana_sorgula`/`cagri_ara` ile çalışır.
