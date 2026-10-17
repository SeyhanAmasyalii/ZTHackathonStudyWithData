# Mercek — Azure SQL (portal ile)

> Hedef: `datav2` verisi Azure SQL'de (`mercekdb`) dursun, `mercek-api` veriyi SQL'den okusun.
> Önce `docs/AZURE-APP-SERVICE.md` tamamlanmış olmalı. **Şifre repoya yazılmaz**; yalnızca `backend/.env` (yerel, git'e girmez) ve App Service → Ortam değişkenleri.

Aşağıda `<sql>` = SQL sunucu adı (ör. `mercek-sql-<takım>`), `<rg>` = resource group, `<api>` = backend uygulama adı.

## 1. Veritabanını oluştur (5 dk)

Portal → arama: `SQL veritabanları` → **+ Oluştur**
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

Beklenen: 6 tablo için `✓ ... satır` ve son satırda `✓ Kontrol: 2002 hata logu, 700 çağrı; JSON ile aynı`.
Betik tabloları her çalıştırmada silip yeniden oluşturur (`db/schema.sql`); tekrar çalıştırmak güvenlidir.

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

## 4. (Ek puan) Şifresiz bağlantı: Managed Identity

1. `<api>` → **Ayarlar → Kimlik** → Sistem tarafından atanan: **Açık** → Kaydet.
2. `mercekdb` → **Sorgu düzenleyicisi** → **Microsoft Entra kimlik doğrulaması** ile girin ve çalıştırın:
   ```sql
   CREATE USER [<api>] FROM EXTERNAL PROVIDER;
   ALTER ROLE db_datareader ADD MEMBER [<api>];
   ```
3. `<api>` → Ortam değişkenleri → `SQL_USER` ve `SQL_PASSWORD`'u **silin** → Uygula.
   `SQL_USER` boş olunca kod Microsoft Entra ile (Managed Identity) bağlanır.

## Sorun giderme

| Belirti | Çözüm |
|---|---|
| Betik: `Client with IP address ... is not allowed` | SQL sunucusu → **Ağ** → Güvenlik duvarı kuralları → **İstemci IP adresinizi ekleyin** → Kaydet (ev/ofis IP'si değişince tekrar) |
| Betik: `✗ SQL'den okunan veri JSON ile aynı değil` | Yükleme yarım kalmış ya da tablo elle değiştirilmiş; betiği tekrar çalıştırın (tablolar baştan kurulur) |
| Betik: `Login failed for user` | `SQL_USER` / `SQL_PASSWORD` yanlış; parola portaldan sıfırlanabilir (SQL sunucusu → Genel Bakış → Parolayı sıfırla) |
| İlk bağlantı 30–60 sn sürüyor ya da `database ... is not currently available` | Ücretsiz/serverless veritabanı uykudaydı; kod 3 kez dener. Tekrar çalıştırın |
| Günlük akışında `Azure SQL okunamadı; JSON verisine geçildi` | Uygulama çalışır ama JSON'dan okur. Satırın altındaki hatayı okuyun: güvenlik duvarı ("Azure hizmetlerine izin ver"), kullanıcı/parola ya da Managed Identity kullanıcısı |
| `SQL_SERVER tanımlı değil` | `backend\.env` dosyasında `SQL_SERVER` satırı yok |
