# Mercek — Hackathon ortamına kurulum (adım adım)

> Bu rehber tek başına yeterlidir: kişisel abonelikte provası yapılan kurulumun hackathon aboneliğine **sırayla**, portal
> tıklamaları düzeyinde taşınması. Konu bazlı ayrıntı ve arka plan: `docs/AZURE-SQL.md`, `docs/AZURE-AI-SEARCH.md`,
> `docs/AZURE-APP-SERVICE.md`, `docs/FOUNDRY-AGENT.md`. Kod Copilot ile yazılacaksa: `docs/COPILOT-MERCEK-PROMPTLARI.md`.
>
> **Kod dizini (hackathon bilgisayarı):** `C:\Users\hackadmin\AIOverflow` — aşağıdaki tüm komutlar bu klasörde çalışır.
> **Tahmini süre:** ~2,5 saat (rol atamalarının etkinleşme beklemeleri dahil).
> **Kural:** anahtar, parola, bağlantı dizesi **repoya yazılmaz**; yalnızca `backend\.env` (git'e girmez) ve
> App Service → Ortam değişkenleri ekranına girilir.
> **Portal dili:** ekran adları Türkçe portala göredir; İngilizce karşılığı parantez içinde.

**Sıra:** 0 Değerler → 1 Bilgisayar → 2 Foundry modelleri → 3 Azure SQL → 4 AI Search → 5 App Service → 6 Foundry agent →
7 Kimlik ve roller → 8 Ortam değişkenleri → 9 Paketle ve yükle → 10 Kontrol → 11 Sorunlar → 12 Demo günü

---

## 0. Değerleri topla (10 dk)

Bu tabloyu bir not dosyasına kopyalayıp doldurarak ilerleyin. Aşağıda `<…>` yazan her yere buradaki değer gelir.

| Kısaltma | Ne | Nereden bulunur | Örnek |
|---|---|---|---|
| `<rg>` | Resource group | Takıma verilen; başka yerde kaynak açılmaz | `rg-aioverflow` |
| `<bölge>` | Bölge | Foundry kaynağıyla aynı bölge | Sweden Central |
| `<takım>` | Ad eki | Adlar Azure genelinde benzersiz olmalı | `aioverflow` |
| `<kiracı>` | Kiracı (tenant) kimliği | Portal → arama: `Microsoft Entra ID` → Genel Bakış → **Kiracı Kimliği** | `xxxxxxxx-…` |
| `<foundry>` | Foundry kaynağı | Takıma verilen ya da §2'de açılan | `…-resource` |
| `<proje>` | Foundry projesi | ai.azure.com → proje adı | `mercek` |
| `<openai-uç>` | Model uç noktası | §2.3 | `https://<foundry>.openai.azure.com/openai/v1` |
| `<foundry-anahtar>` | Model anahtarı | §2.3 | (gizli) |
| `<proje-uç>` | Proje uç noktası | §2.4 | `https://<foundry>.services.ai.azure.com/api/projects/<proje>` |
| `<sql>` | SQL sunucu adı | §3.1'de verilir | `mercek-sql-<takım>` |
| `<sql-parola>` | SQL yönetici parolası | §3.1'de belirlenir | (gizli) |
| `<search>` | AI Search adı | §4.1'de verilir | `mercek-search-<takım>` |
| `<search-anahtar>` | AI Search yönetici anahtarı | §4.2 | (gizli) |
| `<api>` / `<web>` | App Service adları | §5'te verilir | `mercek-api-<takım>` / `mercek-web-<takım>` |
| `<api-adres>` / `<web-adres>` | Uygulamaların gerçek adresi | §5.4 (rastgele ek alabilir) | `mercek-api-…-….azurewebsites.net` |

---

## 1. Bilgisayar hazırlığı (15 dk)

### 1.1 Araçlar
Bir CMD penceresinde sırayla kontrol edin; eksik olanı kurun:

| Araç | Kontrol | Kurulum |
|---|---|---|
| Git | `git --version` | `winget install -e --id Git.Git` |
| uv (Python ortamı) | `uv --version` | `winget install -e --id astral-sh.uv` |
| Python 3.12 | `python --version` | `uv python install 3.12` |
| Node.js 22 | `node --version` | `winget install -e --id OpenJS.NodeJS.LTS` |
| Azure CLI | `az --version` | `winget install -e --id Microsoft.AzureCLI` |

Kurulumdan sonra **yeni bir CMD penceresi** açın (açık pencere yeni araçları görmez).

### 1.2 Kod
Repo henüz bilgisayarda yoksa:
```cmd
git clone <hackathon-repo-adresi> C:\Users\hackadmin\AIOverflow
```
Sonra (ve her çalışmaya başlarken):
```cmd
cd /d C:\Users\hackadmin\AIOverflow
git checkout main
git pull
uv sync --directory backend
cd frontend
npm install
cd ..
```
Kod Copilot ile sıfırdan yazılıyorsa önce `docs/COPILOT-MERCEK-PROMPTLARI.md` fazlarını tamamlayın; betikler (`scripts\…`) o fazlarda oluşur.

### 1.3 Azure girişi (hackathon kiracısı)
```cmd
az login --tenant <kiracı>
```
- Tarayıcı açılır → hackathon hesabınızla girin → MFA'yı tamamlayın (telefon onayı/kod).
- Terminalde abonelik listesi çıkarsa hackathon aboneliğinin numarasını yazıp Enter.
- Kontrol: `az account show --query "{abonelik:name, kiraci:tenantId}" -o table` → hackathon aboneliği ve `<kiracı>`.
- Tarayıcı açılmıyorsa: `az login --tenant <kiracı> --use-device-code` → ekrandaki kodu `https://microsoft.com/devicelogin`'e girin.

### 1.4 `.env` dosyası
```cmd
cd /d C:\Users\hackadmin\AIOverflow
copy backend\.env.example backend\.env
notepad backend\.env
```
Not Defteri'nde satırları sonraki adımlarda doldurun (her adımda hangi satırın ekleneceği yazılı; tam liste §8.3).
Aynı bilgisayarda başka bir ortamın `.env`'i varsa önce yedekleyin: `copy backend\.env backend\.env.yedek`
(`.env` ve `.env.*` git'e girmez).

---

## 2. Foundry: modeller ve uç noktalar (15 dk)

Takıma Foundry kaynağı ve projesi verildiyse 2.1'i atlayın.

### 2.1 Foundry kaynağı ve projesi (yoksa)
1. `https://ai.azure.com` → hackathon hesabıyla giriş → sağ üst **Yeni Atölye** anahtarı açık olsun.
2. **+ Yeni proje** (Create project) → proje adı: `mercek` → **Gelişmiş seçenekler**: abonelik = hackathon, resource group = `<rg>`,
   bölge = `<bölge>` → **Oluştur** (2–3 dk). Bu, `<foundry>` kaynağını ve `<proje>`'yi birlikte açar.

### 2.2 Model dağıtımları
1. ai.azure.com → üstte proje seçili → sol menü **Modeller** (Models + endpoints) → **+ Model dağıt** → **Temel modeli dağıt**.
2. Listede `gpt-5.5` → **Onayla** → Dağıtım adı: **`gpt-5.5`** (aynen) → Dağıtım türü: **Global Standart** (yoksa Standart) → **Dağıt**.
3. Aynı yoldan `text-embedding-3-small` → Dağıtım adı: **`text-embedding-3-small`** → **Dağıt**.
4. Adları farklı verirseniz `CHAT_DEPLOYMENT` ve `EMBEDDING_DEPLOYMENT` ayarlarına o adları yazmanız gerekir.

### 2.3 Model uç noktası ve anahtar
1. **Modeller** → `gpt-5.5` dağıtımına tıklayın → **Uç nokta** bölümü.
2. **Hedef URI**'nin başındaki `https://<foundry>.openai.azure.com` kısmını alın, sonuna `/openai/v1` ekleyin → `<openai-uç>`.
3. **Anahtar** (Key) → kopyala → `<foundry-anahtar>`.
4. `backend\.env`:
   ```
   AZURE_OPENAI_ENDPOINT=<openai-uç>
   AZURE_OPENAI_API_KEY=<foundry-anahtar>
   CHAT_DEPLOYMENT=gpt-5.5
   EMBEDDING_DEPLOYMENT=text-embedding-3-small
   ```

### 2.4 Proje uç noktası
1. ai.azure.com → proje → **Genel bakış** (Overview) → **Proje uç noktası** (Project endpoint) → kopyala → `<proje-uç>`.
   Biçimi: `https://<foundry>.services.ai.azure.com/api/projects/<proje>`.
2. **Elle yazmayın, kopyala-yapıştır yapın**: provada sondaki bir rakam eksik yazıldı ve `404 The project does not exist` alındı.

---

## 3. Azure SQL (30 dk)

### 3.1 Veritabanı ve sunucuyu oluştur (portal)
1. `https://portal.azure.com` → üstteki arama: **`SQL veritabanları`** (SQL databases) → **+ Oluştur**.
   - Aramada "SQL Server veritabanları (Azure Arc)" çıkarsa o değil. Doğrusu **SQL veritabanları**.
   - Üstte **"Ücretsiz Azure SQL Veritabanı teklifi"** bandı çıkarsa **uygulamayın** (AI Search indexer'ı 5 dk'da bir bağlanacağı için ücretsiz kota birkaç günde biter).
2. **Temel Bilgiler** sekmesi:
   - Abonelik: hackathon · Kaynak grubu: `<rg>`
   - Veritabanı adı: **`mercekdb`**
   - Sunucu: **Yeni oluştur** → açılan panel:
     - Sunucu adı: `<sql>` (küçük harf, Azure genelinde benzersiz)
     - Konum: `<bölge>`
     - Kimlik doğrulama yöntemi: **Hem SQL hem de Microsoft Entra kimlik doğrulamasını kullan**
     - Microsoft Entra yöneticisi: **Yönetici ayarla** → kendi hesabınızı seçin → **Seç**
     - Sunucu yöneticisi oturum açma: **`mercekadmin`** · Parola: güçlü bir parola → `<sql-parola>` (bir yere not edin, **repoya yazmayın**)
     - **Tamam**
   - SQL elastik havuzu: **Hayır**
   - İş yükü ortamı: **Geliştirme**
   - İşlem + depolama: **Veritabanını yapılandır** → **Hizmet katmanı: Basic** (DTU tabanlı satın alma modeli altında; "Temel" yazabilir)
     → DTU **5**, Veri en fazla boyutu **2 GB** → **Uygula**. Sağdaki maliyet ~5 $/ay görünmeli.
   - Yedek depolama yedekliliği: **Yerel olarak yedekli** (en ucuz)
3. **İleri: Ağ İletişimi** sekmesi:
   - Bağlantı yöntemi: **Genel uç nokta**
   - **Azure hizmetlerinin ve kaynaklarının bu sunucuya erişmesine izin ver: Evet** (App Service ve AI Search için şart)
   - **Geçerli istemci IP adresini ekle: Evet** (bilgisayarınızdan veri yüklemek için)
   - Bağlantı ilkesi: Varsayılan · En düşük TLS: 1.2
4. **Güvenlik** ve **Ek ayarlar** sekmeleri: varsayılan (Ek ayarlar → Mevcut verileri kullan: **Hiçbiri**).
5. **Gözden geçir + oluştur** → **Oluştur** (3–5 dk) → **Kaynağa git**.
6. **Genel Bakış → Sunucu adı** satırını kopyalayın: `<sql>.database.windows.net`.

### 3.2 Güvenlik duvarını kontrol et
SQL **sunucusu** (`<sql>`, veritabanı değil) → sol menü **Güvenlik → Ağ İletişimi**:
- Genel ağ erişimi: **Seçili ağlar**
- Güvenlik duvarı kuralları: kendi IP'niz listede olmalı; yoksa **+ İstemci IPv4 adresinizi ekleyin**
- Özel durumlar: **Azure hizmetlerinin ve kaynaklarının bu sunucuya erişmesine izin ver** ✓
- **Kaydet**. (IP'niz değişirse burada tekrar ekleyin.)

### 3.3 `backend\.env`
```
SQL_SERVER=<sql>.database.windows.net
SQL_DATABASE=mercekdb
SQL_USER=mercekadmin
SQL_PASSWORD=<sql-parola>
```
`SQL_USER/SQL_PASSWORD` **yalnızca yerelde** kalır (veri yükleme ve AI Search indexer'ı bunlarla bağlanır). App Service'e girilmez; o Managed Identity kullanır (§7).

### 3.4 Veriyi yükle (bilgisayarda, 2–5 dk)
```cmd
cd /d C:\Users\hackadmin\AIOverflow
uv run --directory backend python ..\scripts\load_sql.py
```
Beklenen: her tablo için `✓ <tablo>: N satır, içerik JSON ile aynı` ve sonunda
`✓ Kontrol: 21 tablo; sohbet kataloğu 2002 hata logu, 700 çağrı` (`customers` 40.005, `loans` 33.000 satır).
Betik tabloları silip yeniden kurar; tekrar çalıştırmak güvenlidir.

### 3.5 Uygulama tablolarını kur
```cmd
uv run --directory backend python ..\scripts\setup_app_tables.py
```
Beklenen: `✓ Tablolar hazır: app_users, audit_log, conversations, conversation_messages`, ardından
`elif sube müşteri listesi: hayır`, `zeynep cagri_merkezi … hayır`, `kerem l2 … evet` ve tablo sayıları (0 kayıt).
Bu tablolar `load_sql.py` tekrar çalışsa da silinmez.

### 3.6 Kontrol (portal sorgu düzenleyicisi)
`mercekdb` (veritabanı) → **Sorgu düzenleyicisi (önizleme)** → **Microsoft Entra kimlik doğrulaması ile devam et** →
```sql
SELECT COUNT(*) AS hata_logu FROM dbo.kibana_logs WHERE log_level IN ('Warning','Error');
SELECT user_name, role, can_view_customers FROM dbo.app_users;
```
→ `2002` ve üç kullanıcı. IP hatası çıkarsa sayfadaki bağlantıyla IP'nizi güvenlik duvarına ekleyin.

---

## 4. Azure AI Search (25 dk)

### 4.1 Hizmeti oluştur
1. Portal → arama: **`AI Search`** → **Hizmetler** altında **Yapay Zeka Arama (Foundry IQ)** (Türkçe portalda Azure AI Search'ün adı) → **+ Oluştur**.
   Market'teki üçüncü taraf ürünleri (Algolia vb.) seçmeyin.
2. Temel Bilgiler:
   - Kaynak grubu: `<rg>` · Hizmet adı: `<search>`
   - Konum: `<bölge>`; **gri/devre dışıysa** ("yüksek talep") açık bir yakın bölge seçin (provada Norway East çalıştı). Aramanın farklı bölgede olması sorun değil.
   - Fiyatlandırma katmanı: **Fiyatlandırma Katmanını Değiştir → Ücretsiz** (varsayılan Standart **ücretlidir**). Takıma Basic verildiyse o.
3. **Gözden geçir + oluştur** → maliyet **$0,00** (Ücretsiz) → **Oluştur** → **Kaynağa git**.
4. **Genel Bakış → URL**: `https://<search>.search.windows.net` → not edin.
5. Oluşturma "out of the resources" hatası verirse aynı adla başka bölgede tekrar deneyin (başarısız dağıtım kaynak bırakmaz).

### 4.2 Anahtar ve erişim modu
1. `<search>` → **Ayarlar → Anahtarlar** (bazı portallarda Güvenlik ve ağ → Anahtarlar).
2. **API Erişim denetimi: Her ikisi** → **Kaydet** (Managed Identity ile sorgu için şart; §7.2).
3. **Birincil yönetici anahtarı** → kopyala → `<search-anahtar>` (yalnızca `backend\.env`'e).

### 4.3 `backend\.env`
```
SEARCH_ENDPOINT=https://<search>.search.windows.net
SEARCH_API_KEY=<search-anahtar>
SEARCH_LOG_INDEX=mercek-loglar
SEARCH_SOLUTION_INDEX=mercek-cozumler
```
(`AZURE_OPENAI_*` ve `EMBEDDING_DEPLOYMENT` §2.3'te eklenmişti; indexer embedding için bunları kullanır.)

### 4.4 İki indeksi kur (bilgisayarda, 2–4 dk)
```cmd
cd /d C:\Users\hackadmin\AIOverflow
uv run --directory backend python ..\scripts\build_search_index.py --indeks hepsi
```
Beklenen:
```
✓ SQL görünümleri: dbo.v_hata_turleri 107 hata türü · dbo.v_cozum_sablonlari 37 hazır çözüm
✓ AI Search: … indeks 'mercek-loglar' … indexer (5 dakikada bir)
✓ Indexer çalıştı: 107 belge işlendi · indekste 107 belge
Örnek arama: 'abone numarası kabul edilmiyor'
  ODMTTLMT 110412 SUBSCRIBER_NO_INVALID SU01 · … log · Abone numarası 13 hane; …
✓ AI Search: … indeks 'mercek-cozumler' … indexer (5 dakikada bir)
✓ Indexer çalıştı: 37 belge işlendi · indekste 37 belge
Arama: 'müşteri adres bilgisini kaydedemiyorum' (eşik %75)
  ✓ SOL-026 %… …
```
Eşik kontrolü (kurulum yapmaz):
```cmd
uv run --directory backend python ..\scripts\build_search_index.py --dene "adres değişikliği yapamıyorum, alan hatası veriyor"
uv run --directory backend python ..\scripts\build_search_index.py --dene "Input string was not in a correct format"
```
→ İlki `✓ SOL-026 %8x`, ikincisinde ✓ yok.

### 4.5 Portalda kontrol
`<search>` → **Arama yönetimi → Dizinler**: `mercek-loglar` (107), `mercek-cozumler` (37) ·
**Dizin oluşturucular**: iki indexer, **Yürütme geçmişi**'nde "Başarılı" (5 dk'da bir satır eklenir).

---

## 5. App Service: plan, backend, frontend (30 dk)

### 5.1 App Service planı
Portal → **Kaynak oluştur** → **App Service planı** →
- Kaynak grubu `<rg>` · Ad `mercek-plan` · İşletim sistemi **Linux** · Bölge `<bölge>`
- Fiyatlandırma planı: **Basic B1** (Always On ve sistem durumu denetimi için) → **Gözden geçir + oluştur → Oluştur**.

### 5.2 Backend uygulaması `<api>`
1. **Kaynak oluştur** → **Web Uygulaması** (Web App):
   - Kaynak grubu `<rg>` · Ad `<api>` · Yayımla: **Kod** · Çalışma zamanı yığını: **Python 3.12** · İşletim sistemi: **Linux**
   - Bölge `<bölge>` · Linux Planı: **`mercek-plan`**
   - "Güvenli benzersiz varsayılan ana bilgisayar adı": varsayılan (Etkin) kalabilir
   - **Dağıtım** sekmesi: sürekli dağıtım **Devre dışı** · **İzleme** sekmesi: Application Insights **Hayır** (Foundry izlemesi ayrı)
   - **Gözden geçir + oluştur → Oluştur** → **Kaynağa git**
2. **Ayarlar → Yapılandırma → Yığın ayarları** (Stack settings) → **Başlangıç komutu**:
   `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000` → **Kaydet**.
3. **Ayarlar → Yapılandırma → Genel ayarlar** → **Always On: Açık** · **Yalnızca HTTPS: Açık** → **Kaydet**.
4. **İzleme → Sistem durumu denetimi** (Health check) → **Etkinleştir** → Yol: `/api/health` → **Kaydet**.
5. **Ayarlar → Kimlik** (Identity) → **Sistem tarafından atanan** → Durum **Açık** → **Kaydet → Evet** (Managed Identity; §7'de yetki verilecek).

### 5.3 Frontend uygulaması `<web>`
1. **Kaynak oluştur → Web Uygulaması**: Ad `<web>` · **Kod** · Çalışma zamanı: **Node 22 LTS** · **Linux** · Plan **`mercek-plan`** → **Oluştur**.
2. **Yığın ayarları → Başlangıç komutu**: `node server.js` → Kaydet.
3. **Genel ayarlar**: Always On **Açık**, Yalnızca HTTPS **Açık** → Kaydet.
4. **Sistem durumu denetimi** → Yol: `/giris` → Kaydet.

### 5.4 Gerçek adresleri al
Her iki uygulamada **Genel Bakış → Varsayılan etki alanı** satırını kopyalayın → `<api-adres>`, `<web-adres>`
(ör. `mercek-api-aioverflow-abc123.westeurope-01.azurewebsites.net`). Aşağıdaki her yerde bu tam adresi kullanın.

---

## 6. Foundry agent ve izleme (15 dk)

### 6.1 Kendi hesabınızın Foundry yetkisi
Kaynağı siz açtıysanız genelde vardır. `setup_agent.py` **403** verirse:
portal → `<foundry>` → **Erişim denetimi (IAM)** → **+ Ekle → Rol ataması ekle** → `Azure AI` / `Cognitive Services` ara →
**Azure AI User** (yoksa **Cognitive Services User**, o da yoksa **Cognitive Services Data Contributor (Preview)**) → **Sonraki** →
**Kullanıcı, grup veya hizmet sorumlusu** → **+ Üye seç** → kendi hesabınız → **Gözden geçir + ata**.

### 6.2 `backend\.env`
```
FOUNDRY_PROJECT_ENDPOINT=<proje-uç>
FOUNDRY_AGENT_NAME=mercek-cagri
```

### 6.3 Agent'ı kur
```cmd
cd /d C:\Users\hackadmin\AIOverflow
uv run --directory backend python ..\scripts\setup_agent.py
```
Beklenen:
```
✓ Agent 'mercek-cagri' sürüm 1 · model gpt-5.5 · araçlar: kibana_sorgula, cagri_ara, hata_ara, benzer_cozum_ara
Deneme: Ben Mercek; …
```
`DefaultAzureCredential failed to retrieve a token` → `az login --tenant <kiracı>` (§1.3) ve tekrar.
Portalda: ai.azure.com → **Aracılar** → `mercek-cagri` (yeşil tik). **Ayrıntılar**'da talimat ve araçlar görünür; **portalda düzenlemeyin**
(prompt ya da araç değişince betiği tekrar çalıştırın; yeni sürüm oluşur). **Deneme alanı**'nda araçlar çalışmaz (araçları backend çalıştırır).

### 6.4 İzleme (App Insights) — jüriye gösterilecek ekran
1. ai.azure.com → **Aracılar** → `mercek-cagri` → **İzleme** sekmesi → üstteki mor bant → **Bağla**.
2. **İzleyici ayarları** penceresi: Application insights kaynak adı **Yeni kaynak oluştur** · Ad `mercek-appinsights` ·
   Log Analytics çalışma alanı: varsayılan (`[yeni] DefaultWorkspace-…`) · Kimlik Doğrulama Türü: **Proje Yönetilen Kimliği** → **Oluştur**.
3. Gizlilik notu: izlerde kullanıcı mesajları ve araç sonuçları saklanır; *Log Analytics Reader* rolünü yalnızca takıma verin.
4. Kurulum bitince (§10) birkaç soru sorup 5–10 dk sonra **İzlemeler** sekmesine bakın: her çalıştırmada araç adımları görünür.

---

## 7. Kimlik ve roller: Managed Identity (20 dk + 10 dk bekleme)

`<api>`'nin kimliği §5.2/5'te açıldı. Üç yere yetki verilir. Sonunda 5–10 dk bekleyip `<api>` → **Genel Bakış → Yeniden başlat**.

### 7.1 Azure SQL
1. `mercekdb` → **Sorgu düzenleyicisi (önizleme)** → **Microsoft Entra kimlik doğrulaması ile devam et** (SQL kullanıcısıyla değil;
   `FROM EXTERNAL PROVIDER` yalnızca Entra girişte çalışır).
2. Çalıştırın (`<api>` = uygulamanın **tam adı**, adres değil):
   ```sql
   CREATE USER [<api>] FROM EXTERNAL PROVIDER;
   ALTER ROLE db_datareader ADD MEMBER [<api>];
   ALTER ROLE db_datawriter ADD MEMBER [<api>];
   ```
   Beklenen: "Sorgu başarılı". Kontrol: `SELECT name, type_desc FROM sys.database_principals WHERE name = '<api>';` → `EXTERNAL_USER`.
   - `Principal '<api>' could not be found` → §5.2/5 kimlik açılmamış ya da ad yanlış.
   - `Only connections established with Active Directory accounts…` → düzenleyiciye Entra ile girin.

### 7.2 Azure AI Search
`<search>` → **Erişim denetimi (IAM)** → **+ Ekle → Rol ataması ekle** → arama kutusuna `Arama` yazın →
**Arama Dizini Veri Okuyucusu** (Search Index Data Reader) → **Sonraki** →
Erişim ata: **Yönetilen kimlik** → **+ Üye seç** → Yönetilen kimlik: **App Service** → `<api>` → **Seç** → **Gözden geçir + ata**.
"Yönetilen Uygulama İşletmeni" ve "Arama Dizini Veri Katkıda Bulunanı" rollerini **seçmeyin**. (§4.2'deki **Her ikisi** ayarı yapılmış olmalı.)

### 7.3 Foundry
`<foundry>` → **Erişim denetimi (IAM)** → **+ Ekle → Rol ataması ekle** → arama: `Azure AI` ya da `Cognitive Services` →
1. **Azure AI User** varsa onu,
2. yoksa **Cognitive Services User**,
3. o da yoksa **Cognitive Services Data Contributor (Preview)** (provada bu çalıştı)

→ **Sonraki** → **Yönetilen kimlik** → **App Service** → `<api>` → **Gözden geçir + ata**.
*Azure AI Developer* (provada 403), *Cognitive Services OpenAI User* ve *Data Reader* agent çağrısına **yetmez**.

### 7.4 Kontrol
Her kaynakta **Erişim denetimi (IAM) → Rol atamaları** sekmesinde `<api>` ilgili rolle görünmeli.

---

## 8. App Service ortam değişkenleri (10 dk)

### 8.1 Backend `<api>`
`<api>` → **Ayarlar → Ortam değişkenleri** → **Uygulama ayarları** sekmesi. İki yol:
- **Tek tek:** **+ Ekle** → Ad / Değer → **Uygula**; hepsi bitince en alttaki **Uygula → Onayla**.
- **Toplu:** **Gelişmiş düzenleme** → mevcut JSON listesinin sonuna aşağıdaki şablonu ekleyin (önceki son öğeden sonra virgül) → **Tamam → Uygula → Onayla**.

| Ad | Değer | Not |
|---|---|---|
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` | yüklemede paketler kurulur |
| `CORS_ORIGINS` | `https://<web-adres>` | sonda `/` yok |
| `SESSION_SECRET` | uzun rastgele metin | üret: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `AZURE_OPENAI_ENDPOINT` | `<openai-uç>` | `chat` modu (geri dönüş) için |
| `AZURE_OPENAI_API_KEY` | `<foundry-anahtar>` | |
| `CHAT_DEPLOYMENT` | `gpt-5.5` | |
| `SQL_SERVER` | `<sql>.database.windows.net` | |
| `SQL_DATABASE` | `mercekdb` | `SQL_USER`/`SQL_PASSWORD` **eklemeyin** (MI) |
| `SEARCH_ENDPOINT` | `https://<search>.search.windows.net` | `SEARCH_API_KEY` **eklemeyin** (MI) |
| `SEARCH_LOG_INDEX` | `mercek-loglar` | |
| `SEARCH_SOLUTION_INDEX` | `mercek-cozumler` | |
| `LLM_MODE` | `agent` | sorun olursa `chat` |
| `FOUNDRY_PROJECT_ENDPOINT` | `<proje-uç>` | kopyala-yapıştır |
| `FOUNDRY_AGENT_NAME` | `mercek-cagri` | |

`LLM_DEBUG` eklemeyin (Azure'da kapalı kalmalı; kullanıcı mesajlarını loglar). `DEMO_NOW` varsayılanı `2026-10-17T09:15:00+03:00`.

Gelişmiş düzenleme şablonu (değerleri doldurun; doldurulmuş hali repoya kaydedilmez):
```json
  { "name": "SCM_DO_BUILD_DURING_DEPLOYMENT", "value": "true", "slotSetting": false },
  { "name": "CORS_ORIGINS", "value": "https://<web-adres>", "slotSetting": false },
  { "name": "SESSION_SECRET", "value": "<uzun-rastgele-metin>", "slotSetting": false },
  { "name": "AZURE_OPENAI_ENDPOINT", "value": "<openai-uç>", "slotSetting": false },
  { "name": "AZURE_OPENAI_API_KEY", "value": "<foundry-anahtar>", "slotSetting": false },
  { "name": "CHAT_DEPLOYMENT", "value": "gpt-5.5", "slotSetting": false },
  { "name": "SQL_SERVER", "value": "<sql>.database.windows.net", "slotSetting": false },
  { "name": "SQL_DATABASE", "value": "mercekdb", "slotSetting": false },
  { "name": "SEARCH_ENDPOINT", "value": "https://<search>.search.windows.net", "slotSetting": false },
  { "name": "SEARCH_LOG_INDEX", "value": "mercek-loglar", "slotSetting": false },
  { "name": "SEARCH_SOLUTION_INDEX", "value": "mercek-cozumler", "slotSetting": false },
  { "name": "LLM_MODE", "value": "agent", "slotSetting": false },
  { "name": "FOUNDRY_PROJECT_ENDPOINT", "value": "<proje-uç>", "slotSetting": false },
  { "name": "FOUNDRY_AGENT_NAME", "value": "mercek-cagri", "slotSetting": false }
```

### 8.2 Frontend `<web>`
| Ad | Değer |
|---|---|
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `false` |
| `HOSTNAME` | `0.0.0.0` |

### 8.3 Tam `backend\.env` (yerel betikler için)
```
AZURE_OPENAI_ENDPOINT=<openai-uç>
AZURE_OPENAI_API_KEY=<foundry-anahtar>
CHAT_DEPLOYMENT=gpt-5.5
EMBEDDING_DEPLOYMENT=text-embedding-3-small
SQL_SERVER=<sql>.database.windows.net
SQL_DATABASE=mercekdb
SQL_USER=mercekadmin
SQL_PASSWORD=<sql-parola>
SEARCH_ENDPOINT=https://<search>.search.windows.net
SEARCH_API_KEY=<search-anahtar>
SEARCH_LOG_INDEX=mercek-loglar
SEARCH_SOLUTION_INDEX=mercek-cozumler
FOUNDRY_PROJECT_ENDPOINT=<proje-uç>
FOUNDRY_AGENT_NAME=mercek-cagri
# Yerelde agent modunda denemek için: LLM_MODE=agent
```

---

## 9. Paketle ve yükle (15 dk)

### 9.1 Paketleri üret (bilgisayarda)
```cmd
cd /d C:\Users\hackadmin\AIOverflow
git pull
python scripts\package_azure.py --api-url https://<api-adres>
```
- Sonuç: `C:\Users\hackadmin\AIOverflow\dist\mercek-api.zip` ve `…\dist\mercek-web.zip`.
- Çıktıdaki **`Sürüm: <commit> · <tarih saat>`** satırını not edin (sitenin sol üstünde görünecek).
- `--api-url` frontend'e gömülür: `https://` ile, sonda `/` olmadan, **tam** `<api-adres>`. Adres değişirse tekrar paketleyin.
- **Her paketlemeden önce `git pull`** (provada eski commit paketlendi, yeni özellik görünmedi).

### 9.2 Cloud Shell'e yükle
1. Portal üst çubuğu → **Cloud Shell** (`>_`) → **Bash** → ilk açılışta "Depolama hesabı gerekmez" → **Uygula**.
2. Eski zip'leri silin:
   ```bash
   rm -f ~/mercek-api.zip ~/mercek-web.zip
   ```
3. Cloud Shell araç çubuğu → **Dosyaları yönet → Karşıya yükle** → `C:\Users\hackadmin\AIOverflow\dist\mercek-api.zip`;
   sonra aynı yoldan `mercek-web.zip`.
4. Tarihleri kontrol: `ls -l ~/*.zip` → saat şimdi olmalı.

### 9.3 Dağıt
```bash
az webapp deploy -g <rg> -n <api> --src-path ~/mercek-api.zip --type zip
az webapp deploy -g <rg> -n <web> --src-path ~/mercek-web.zip --type zip --clean true
az webapp restart -g <rg> -n <web>
```
- `-n` uygulamanın **adı**dır (`<api>`), uzun adres değil.
- Her komutun sonunda `"status": "RuntimeSuccessful"`. İlk backend yüklemesi paket kurulumu nedeniyle 2–4 dk sürer.
- Frontend **her zaman `--clean true` + `restart`** (onsuz eski arayüz kalabiliyor).

---

## 10. Kontrol (15 dk)

İzlemek için `<api>` → **İzleme → Günlük akışı** (Log stream) ayrı sekmede açık kalsın (F5 ile yenileyin).

| # | Nerede / ne | Beklenen |
|---|---|---|
| 1 | `https://<api-adres>/api/health` | `{"status":"ok"}` |
| 2 | Günlük akışı | `Veri kaynağı: Azure SQL (mercekdb) · 2002 hata logu · 700 çağrı`, `ManagedIdentityCredential` |
| 3 | `https://<web-adres>` sol üst | **sürüm** = §9.1'deki commit. Değilse frontend'i `--clean true` + restart ile tekrar yükleyin, gizli pencerede açın |
| 4 | Elif → "ODMTTLMT ekranında hata alıyorum" | 7 hata, GAZ02 110731, SOL-031 (6 çağrı) + **▶ Akışı izle · SOL-031**; günlükte `…/responses "200 OK"` ve `ad=kibana_sorgula` |
| 5 | Aynı sohbet → "Peki nasıl çözerim?" → **F5** | SOL-031 adımları (önceki konuyu hatırlar); F5 sonrası konuşma geri gelir |
| 6 | Elif → Yeni sohbet → "abone numarasını sistem kabul etmiyor" | günlükte `ad=hata_ara … sonuç=5`; İSKİ 13 hane, SOL-005 temkinli |
| 7 | Kerem → "Müşteri güncelleme ekranında 'Input string was not in a correct format' hatası" | `ad=benzer_cozum_ara`; "hazır çözüm yok", aday adımları verilmez |
| 8 | Kerem → "Müşteriye fatura talimatı tanımlanamıyor, 'aktif talimat zaten var' diyor. Kaç müşteri etkilendi?" | **Etkilenen müşteriler (31)** → tablo, 11 aranabilir |
| 9 | Sorgu düzenleyicisi: `SELECT TOP 5 created_at, user_name, action, row_count FROM dbo.audit_log ORDER BY audit_id DESC;` | `kerem · affected_customers_view · 31` |
| 10 | ai.azure.com → Aracılar → `mercek-cagri` → **İzlemeler** | çalıştırmalar ve araç adımları (5–10 dk gecikmeli) |

Diğer sorular ve beklenen cevaplar: `docs/MERCEK-TEST-SORULARI.md`.

---

## 11. Sorunlar ve hızlı çözüm (provada yaşananlar)

| Belirti | Sebep → çözüm |
|---|---|
| `az login`: MFA / "No subscriptions found" | `az login --tenant <kiracı>` |
| `'az' is not recognized` | Azure CLI kurulduktan sonra yeni CMD açın |
| Betik: `Client with IP address … is not allowed` | §3.2: IP'nizi ekleyin |
| Betik: `Login failed for user` | `.env`'deki `SQL_USER`/`SQL_PASSWORD` yanlış; portal → SQL sunucusu → Genel Bakış → **Parolayı sıfırla** |
| AI Search oluşturulamıyor (kapasite) | Başka bölge (Norway East çalıştı) |
| Indexer: `Login failed` | `.env` SQL kullanıcı/parola; `git pull` (eski betikte parola biçimi hatası vardı) |
| Indexer: `embedding` / `DeploymentNotFound` / `401` | `text-embedding-3-small` dağıtımı yok ya da `AZURE_OPENAI_*` yanlış |
| `/api/health` açılmıyor, "Application Error" | Günlük akışı; `ModuleNotFoundError` ise `SCM_DO_BUILD_DURING_DEPLOYMENT=true` mi, paketi tekrar yükleyin |
| Giriş ekranında "Sunucuya ulaşılamadı" | `--api-url` yanlış (https, tam adres, sonda `/` yok) ya da `CORS_ORIGINS` ≠ `https://<web-adres>` |
| Yeni özellik/düğme görünmüyor, sürüm eski | Paketlemeden önce `git pull` yapılmamış ya da web `--clean true` + restart ile yüklenmemiş |
| F5'te konuşma gelmiyor | Frontend eski (sürüm) ya da `db_datawriter` yok (günlükte `INSERT permission was denied`) |
| "Şu an yanıt üretilemiyor" + `404 The project does not exist` | `FOUNDRY_PROJECT_ENDPOINT` yanlış yazılmış |
| "Şu an yanıt üretilemiyor" + `403 Forbidden` (agent) | §7.3 rolü yok ya da etkinleşmedi → 10 dk bekleyin, `<api>`'yi yeniden başlatın |
| "Şu an yanıt üretilemiyor" + `turda cevap üretilemedi` | Eski kod (tur sınırı 5); güncel paket yükleyin |
| Günlükte `hata_ara başarısız: Arama servisi 403` | §7.2 rolü etkinleşmedi ya da §4.2 "Her ikisi" değil |
| Günlükte `Azure SQL okunamadı; JSON verisine geçildi` | §7.1 kullanıcısı yok ya da §3.2'de "Azure hizmetlerine izin ver" kapalı |
| Chrome'da kırmızı "Tehlikeli" uyarısı | Yeni `azurewebsites.net` adresindeki giriş sayfası; kod sorunu değil. Google Safe Browsing'e bildirin, demodan önce jüri tarayıcısında kontrol edin |
| İzlemeler boş | App Insights bağlantısından sonraki sorular 5–10 dk sonra görünür |

---

## 12. Demo günü

- **Önce:** §10'daki kontrolleri bir kez yapın; Günlük akışı ve Foundry İzlemeler sekmeleri açık dursun.
- **Agent tarafında sorun:** `<api>` → Ortam değişkenleri → `LLM_MODE` = `chat` → Uygula (1 dk). Her şey doğrudan model çağrısıyla çalışır.
- **AI Search sorunu:** `SEARCH_ENDPOINT` satırını silmek arama araçlarını kapatır; sohbet `kibana_sorgula`/`cagri_ara` ile çalışır.
- **İlk açılış yavaşsa:** Always On açık mı (§5.2/3).
- **Maliyet:** demodan sonra AI Search indexer'ları portalda **Zamanlama → Bir kez** yapılabilir; SQL Basic sabit ücretlidir.
