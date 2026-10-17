# Mercek — Azure SQL (portal ile)

> Hedef: `datav2` verisi Azure SQL'de (`mercekdb`) dursun, `mercek-api` veriyi SQL'den okusun.
> Önce `docs/AZURE-APP-SERVICE.md` tamamlanmış olmalı. **Şifre repoya yazılmaz**; yalnızca `backend/.env` (yerel, git'e girmez) ve App Service → Ortam değişkenleri.

Aşağıda `<sql>` = SQL sunucu adı (ör. `mercek-sql-<takım>`), `<rg>` = resource group, `<api>` = backend uygulama adı.

## 1. Veritabanını oluştur (5 dk)

Portal → arama: `SQL veritabanları` → **+ Oluştur**
> Aramada **"SQL Server veritabanları"** (Azure Arc) çıkarsa o değil. Doğru sayfa **"SQL veritabanları"**; ya da arama: `Azure SQL` → **+ Oluştur** → **SQL veritabanları** kutusunda *Kaynak türü: Tek veritabanı* → **Oluştur**.
- Üstte **"Ücretsiz Azure SQL Veritabanı teklifi"** bandı varsa → **Uygula** (aylık ücretsiz kota; hackathon aboneliğinde yoksa en küçük serverless seçilir)
- Resource group: `<rg>` · Veritabanı adı: `mercekdb`
- Sunucu → **Yeni oluştur**
  - Ad: `<sql>` (Azure genelinde benzersiz) · Konum: Foundry/App Service ile aynı bölge
  - Kimlik doğrulama: **Hem SQL hem Microsoft Entra kimlik doğrulaması kullan**
  - Microsoft Entra yöneticisi: **Yönetici ayarla** → kendi hesabınız
  - Sunucu yöneticisi oturum açma: `mercekadmin` · Parola: güçlü bir parola (bir yere not edin, **repoya yazmayın**)
- Ücretsiz teklif uygulandıysa "Ücretsiz sınıra ulaşıldığında": **Veritabanını ay sonuna kadar otomatik duraklat** (ücret çıkmaz)
- **Ağ** sekmesi: Bağlantı yöntemi **Genel uç nokta**
  - **Azure hizmetlerinin ve kaynaklarının bu sunucuya erişmesine izin ver: Evet** (App Service için)
  - **Geçerli istemci IP adresini ekle: Evet** (bilgisayarınızdan yükleme için)
- **Gözden geçir + oluştur** → **Oluştur** (2–5 dk)

Sunucu adresi: veritabanı → **Genel Bakış → Sunucu adı** (`<sql>.database.windows.net`).

> Ücretsiz teklifin sade oluşturma ekranında **Ağ** sekmesi yoktur. Oluşturduktan sonra: SQL sunucusu (`<sql>`) → **Güvenlik → Ağ İletişimi** → Genel ağ erişimi **Seçili ağlar** → **+ İstemci IPv4 adresinizi ekleyin** → Özel durumlar: **Azure hizmetlerinin ve kaynaklarının bu sunucuya erişmesine izin ver** ✓ → **Kaydet**.

## 2. Veriyi yükle (bilgisayarda, 2 dk)

`backend\.env` dosyasına ekleyin (bu dosya git'e girmez):

```
SQL_SERVER=<sql>.database.windows.net
SQL_DATABASE=mercekdb
SQL_USER=mercekadmin
SQL_PASSWORD=<parola>
```

Repo kökünde (CMD):

```cmd
cd /d <repo-klasörü>
git pull
uv run --directory backend python ..\scripts\load_sql.py
```

Beklenen: 21 tablonun her biri için `✓ <tablo>: N satır, içerik JSON ile aynı` ve son satırda
`✓ Kontrol: 21 tablo; sohbet kataloğu 2002 hata logu, 700 çağrı` (1–2 dk; `customers` 40.005, `loans` 33.000 satır).

- Yüklenen: `datav2/*.json`'daki tüm tablolar, tüm kolonlarıyla + `datav2/ui/scenarios.ts` → `scenarios` tablosu.
  Yüklenmeyen: `*.stats.json` (özet) ve `kibana_logs_partNN.json` (`kibana_logs.json`'un parçaları).
- Betik tabloları her çalıştırmada silip yeniden oluşturur (`db/schema.sql`); tekrar çalıştırmak güvenlidir.
- Veride kolon/tablo değişirse önce şemayı yeniden üretin: `python scripts\build_schema.py` (tipler veriden çıkarılır).

Yerelde backend'i (`uv run uvicorn app.main:app --reload --port 8000`) başlatınca terminalde
`Veri kaynağı: Azure SQL (mercekdb) · 2002 hata logu · 700 çağrı` satırı görünür.

## 3. App Service'e bağla (3 dk)

`<api>` → **Ayarlar → Ortam değişkenleri** → **+ Ekle** → **Uygula**

| Ad | Değer |
|---|---|
| `SQL_SERVER` | `<sql>.database.windows.net` |
| `SQL_DATABASE` | `mercekdb` |
| `SQL_USER` | `mercekadmin` |
| `SQL_PASSWORD` | parola |

Backend paketini yeniden üretip yükleyin (yeni sürücü `mssql-python` eklendi):

```cmd
python scripts\package_azure.py --only api
```
Cloud Shell → Karşıya yükle → `az webapp deploy -g <rg> -n <api> --src-path mercek-api.zip --type zip`

Kontrol: `<api>` → **İzleme → Günlük akışı**'nda `Veri kaynağı: Azure SQL (mercekdb) · 2002 hata logu · 700 çağrı`.
Sohbette "ODMTTLMT ekranında hata alıyorum" → aynı cevap (7 hata, GAZ02 110731, SOL-031).

## 4. (Ek puan) Şifresiz bağlantı: Managed Identity (10 dk, yalnızca portal)

**Ne değişir:** `<api>` SQL'e kullanıcı adı/parola yerine Azure'un verdiği kimlikle (Managed Identity) bağlanır.
App Settings'te SQL parolası kalmaz. Kodda değişiklik gerekmez: `SQL_USER` boşsa kod
`Authentication=ActiveDirectoryDefault` ile bağlanır; App Service'te bu, uygulamanın kimliğini kullanır.

Ön koşul: SQL sunucusunda **Microsoft Entra yöneticisi** tanımlı olmalı (§1'de kendi hesabınız).
Yoksa: SQL sunucusu → **Ayarlar → Microsoft Entra ID** → **Yönetici ayarla** → hesabınız → Kaydet.

### 4.1 Uygulamaya kimlik ver
`<api>` → **Ayarlar → Kimlik** → **Sistem tarafından atanan** sekmesi → Durum: **Açık** → **Kaydet** → **Evet**.
Birkaç saniye sonra **Nesne (sorumlu) kimliği** görünür; kimliğin adı uygulama adıyla aynıdır (`<api>`).

### 4.2 Veritabanında bu kimliğe kullanıcı aç
1. `mercekdb` (SQL veritabanı) → **Sorgu düzenleyicisi (önizleme)**.
2. **Microsoft Entra kimlik doğrulaması** ile devam edin (SQL kullanıcısıyla değil; `FROM EXTERNAL PROVIDER`
   yalnızca Entra ile giriş yapınca çalışır). IP hatası çıkarsa: sayfadaki bağlantıyla IP'nizi güvenlik duvarına ekleyin.
3. Sorgu penceresine yazıp **Çalıştır** (`<api>` yerine uygulamanın tam adı, ör. `mercek-api-seyhan`):
   ```sql
   CREATE USER [<api>] FROM EXTERNAL PROVIDER;
   ALTER ROLE db_datareader ADD MEMBER [<api>];
   ```
   Beklenen: "Sorgu başarılı". Kontrol için:
   ```sql
   SELECT name, type_desc FROM sys.database_principals WHERE name = '<api>';
   ```
   → bir satır, `EXTERNAL_USER`.
   - Şimdilik yalnızca okuma yetkisi (`db_datareader`). Mercek SQL'e yazmaya başlayınca (konuşma geçmişi, çağrı kaydı)
     `ALTER ROLE db_datawriter ADD MEMBER [<api>];` eklenir.

### 4.3 Parolayı App Service'ten kaldır
`<api>` → **Ayarlar → Ortam değişkenleri** → `SQL_USER` ve `SQL_PASSWORD` satırlarında 🗑 → **Uygula** → **Onayla**.
`SQL_SERVER` ve `SQL_DATABASE` kalır. Uygulama yeniden başlar.

### 4.4 Kontrol
- `<api>` → **İzleme → Günlük akışı** (sayfayı F5 ile yenileyin; akış eski satırlarda takılı kalabilir):
  - `DefaultAzureCredential acquired a token from ManagedIdentityCredential` → kimlikle token alındı
  - `Veri kaynağı: Azure SQL (mercekdb) · 2002 hata logu · 700 çağrı` → SQL'e parolasız bağlanıldı
- Sohbette "ODMTTLMT ekranında hata alıyorum" → aynı cevap.
- Hata olursa günlükte `Azure SQL okunamadı; JSON verisine geçildi` ve altında sebep görünür (aşağıdaki tablo).
  Uygulama bu sırada JSON'la çalışmaya devam eder; geri dönmek için `SQL_USER`/`SQL_PASSWORD`'u tekrar ekleyin.

### Notlar
- **Yerelde** (bilgisayarınızda) `backend\.env`'deki `SQL_USER`/`SQL_PASSWORD` kalabilir; `load_sql.py` onlarla çalışır.
  Parolasız yüklemek isterseniz `.env`'den bu iki satırı silin, Azure CLI ile `az login` yapın; betik Entra hesabınızla bağlanır.
- **Hackathon ortamında** sunucu yalnızca Entra kimlik doğrulamasına izin veriyorsa (SQL parolası yoksa) doğrudan bu
  bölümle başlayın: App Service'e `SQL_SERVER` + `SQL_DATABASE` girin, 4.1–4.2'yi yapın; yükleme için yukarıdaki `az login` yolu.
- Foundry için de aynı yöntem kullanılabilir (anahtar yerine kimlik): ayrı adım, şu an kod anahtarla çalışıyor.

## Sorun giderme

| Belirti | Çözüm |
|---|---|
| Betik: `Client with IP address ... is not allowed` | SQL sunucusu → **Güvenlik → Ağ İletişimi** → Güvenlik duvarı kuralları → **İstemci IP adresinizi ekleyin** → Kaydet (ev/ofis IP'si değişince tekrar) |
| Betik: `✗ SQL'den okunan veri JSON ile aynı değil` | Yükleme yarım kalmış ya da tablo elle değiştirilmiş; betiği tekrar çalıştırın (tablolar baştan kurulur) |
| Betik: `Login failed for user` | `SQL_USER` / `SQL_PASSWORD` yanlış; parola portaldan sıfırlanabilir (SQL sunucusu → Genel Bakış → Parolayı sıfırla) |
| İlk bağlantı 30–60 sn sürüyor ya da `database ... is not currently available` | Ücretsiz/serverless veritabanı uykudaydı; kod 3 kez dener. Tekrar çalıştırın |
| Günlük akışında `Azure SQL okunamadı; JSON verisine geçildi` | Uygulama çalışır ama JSON'dan okur. Satırın altındaki hatayı okuyun: güvenlik duvarı ("Azure hizmetlerine izin ver"), kullanıcı/parola ya da Managed Identity kullanıcısı |
| `SQL_SERVER tanımlı değil` | `backend\.env` dosyasında `SQL_SERVER` satırı yok |
| MI sonrası: `Login failed for user '<token-identified principal>'` | 4.2 yapılmamış ya da `CREATE USER` adı uygulama adıyla aynı değil |
| `CREATE USER` çalışırken: `Principal '<api>' could not be found` | 4.1'de kimlik açılmamış/kaydedilmemiş ya da ad yanlış yazılmış (tam uygulama adı) |
| `CREATE USER` çalışırken: `Only connections established with Active Directory accounts can create other Active Directory users` | Sorgu düzenleyicisine SQL kullanıcısıyla girilmiş; çıkıp **Microsoft Entra** ile girin |
| MI sonrası: `DefaultAzureCredential failed to retrieve a token` | `<api>` → Kimlik → Sistem tarafından atanan **Açık** mı? Açtıktan sonra uygulamayı yeniden başlatın |
