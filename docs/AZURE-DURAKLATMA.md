# Mercek — Azure maliyetini durdurma ve geri açma

> Proje çalışmıyorken Azure faturasını sıfıra yaklaştırmak ve sonra aynı ortamı geri kurmak için.
> Kaynaklar 24.10.2026'da kendi aboneliğine taşındı: abonelik **MercekAbonelik**, resource group **rg_mercek**.
> **Repoya hiçbir anahtar, parola ya da bağlantı dizesi yazılmaz.** Not alınacak gizli değerler yalnızca kendi bilgisayarındaki `backend\.env`'de durur.

## 0. Hangi kaynak boşta para yazar?

| Kaynak | Tür | Bölge | Boşta ücret | Karar |
|---|---|---|---|---|
| `mercek-plan` | App Service planı | Sweden Central | **Free F1 = 0 $** (24.10.2026'da kontrol edildi). B1'e çıkılırsa ~13 $/ay; uygulamayı "Durdur"mak ücreti kesmez | **Dokunma** (B1'e çıkıldıysa §2.1) |
| `mercek-api-seyhan`, `mercek-web-seyhan` | App Service | Sweden Central | Hayır (ücreti plan yazar) | Dokunma |
| `mercek-search-seyhan` | AI Search | Norway East | **Ücretsiz katman = 0 $** (24.10.2026'da kontrol edildi). Ücretli katmanda Basic ~75 $/ay; durdurulamaz | **Dokunma** (ücretli katmana geçilirse §2.2) |
| `mercek-sql-seyhan` | SQL server | Sweden Central | Hayır | Dokunma |
| `mercekdb` | SQL veritabanı | Sweden Central | **Basic (Temel)** ~5 $/ay, sabit; durdurulamaz | **Sil** (§2.3), dönüşte yeniden kur (§3.0) |
| `seyhanamasyali-7898-resource` (+ proje `seyhanamasyali-7898`) | AI Foundry | Sweden Central | Hayır (kullanılan token kadar) | **Eski abonelikte bırakıldı** (§4.1) |
| `mercek-appinsights` + `DefaultWorkspace-78d24885-…` | Application Insights + Log Analytics | Sweden Central | Neredeyse yok (aylık 5 GB'a kadar ücretsiz) | rg_mercek'e taşınır (§4) |

Kontrol: kaynak → **Genel Bakış → Fiyatlandırma katmanı** (App Service planında **Fiyatlandırma planı**).

## 1. Durdurmadan önce not al (5 dk)

Aşağıdaki tabloyu **kendi notuna** doldur (gizli olmayan bilgiler; anahtar değerlerini yazma):

| Ne | Nerede bakılır | Değer |
|---|---|---|
| Plan katmanı | `mercek-plan` → Genel Bakış → Fiyatlandırma planı | ör. B1 |
| Always On açık mı (api, web) | Uygulama → Ayarlar → Yapılandırma → Genel ayarlar | Açık / Kapalı |
| Sistem durumu denetimi yolu | Uygulama → İzleme → Sistem durumu denetimi | api: `/api/health`, web: `/giris` |
| Search katmanı | `mercek-search-seyhan` → Genel Bakış → Fiyatlandırma katmanı | Ücretsiz / Basic / … |
| Search bölgesi | aynı ekran → Konum | Norway East |
| Search API erişim denetimi | Search → Ayarlar → Anahtarlar | Her ikisi / Rol tabanlı / API anahtarı |
| Search indeksleri ve belge sayıları | Search → Arama yönetimi → Dizinler | `mercek-loglar` 107 · `mercek-cozumler` 37 |
| api'deki Search ayarları | `mercek-api-seyhan` → Ayarlar → Ortam değişkenleri | `SEARCH_ENDPOINT`, `SEARCH_LOG_INDEX`, `SEARCH_SOLUTION_INDEX` (değerleri gizli değil); `SEARCH_API_KEY` **var mı yok mu** (değerini yazma) |
| api'nin Search rolü (Managed Identity kullanılıyorsa) | Search → Erişim denetimi (IAM) → Rol atamaları | `Search Index Data Reader` → `mercek-api-seyhan` |
| SQL katmanı | `mercekdb` → Genel Bakış → Fiyatlandırma katmanı | Basic / Ücretsiz |

Ayrıca bilgisayarındaki `backend\.env` dosyasının yerinde olduğundan emin ol (`SQL_*`, `AZURE_OPENAI_*`, `EMBEDDING_DEPLOYMENT`). Geri kurulumda betik bu ayarları kullanır.

## 2. Durdur

### 2.1 App Service planını Free F1'e düşür (2 dk, uygulamalar silinmez)
1. `mercek-api-seyhan` ve `mercek-web-seyhan` → **Ayarlar → Yapılandırma → Genel ayarlar** → **Always On: Kapalı** → Kaydet.
   **İzleme → Sistem durumu denetimi** → Devre dışı → Kaydet. (F1 bu ikisini desteklemez; açık kalırsa düşürme hata verebilir.)
2. `mercek-plan` → **Ayarlar → Ölçeği artır (App Service planı)** → **Ücretsiz F1** → **Seç**.
3. Kontrol: Genel Bakış → Fiyatlandırma planı **F1**. Uygulamalar F1'de de açılır (ilk istek 20–60 sn sürebilir, günlük CPU kotası 60 dk).

### 2.2 AI Search'ü sil (yalnızca katmanı **Ücretsiz değilse**)
Ücretsiz katman para yazmaz, silme. Ücretliyse:
1. §1'deki tabloyu doldurduğundan emin ol.
2. `mercek-search-seyhan` → **Genel Bakış → Sil** → adı yaz → **Sil**.
3. İndeks, indexer, veri kaynağı ve beceri tanımları kodda durur (`backend/app/services/log_index.py`, `solution_index.py`); geri kurulumda betik yeniden oluşturur. Silme geri alınamaz.

Silinmediyse ve SQL **ücretsiz teklifteyse**: 5 dk'lık indexer SQL'i uyanık tutup kotayı bitirir. Search → **Dizin oluşturucular** → her indexer → **Zamanlama: Bir kez** → Kaydet.

### 2.3 SQL veritabanını sil (5 dk)
Basic ~5 $/ay ve durdurulamaz. datav2 verisi betikle yeniden yüklenir; **kaybolan** yalnızca Mercek'in kendi yazdığı
kayıtlardır (`dbo.app_*`: erişim kaydı, konuşma geçmişi; `db/app_tables.sql`). Bunlar gerekliyse silmeden önce
veritabanı → **Dışarı aktar** ile `.bacpac` al (bir depolama hesabı ister).

1. **Search indexer'larını durdur** (isteğe bağlı; yoksa 5 dk'da bir hata kaydı düşer, ücret yazmaz): `mercek-search-seyhan` →
   **Arama yönetimi → Dizin oluşturucular** → her indexer → **Zamanlama: Bir kez** → Kaydet.
2. `mercekdb` → **Genel Bakış → Sil** → veritabanı adını yaz → **Sil**.
   **SQL sunucusunu (`mercek-sql-seyhan`) silme:** ücret yazmaz; Entra admin, güvenlik duvarı ve sunucu adı korunur.
3. Fikir değişirse: silinen veritabanı saklama süresi boyunca (Basic: 7 gün) sunucu → **Veri yönetimi → Silinen veritabanları**'ndan geri yüklenebilir.

Veritabanı yokken uygulama SQL'e bağlanamaz; Mercek JSON verisine geçer.

### 2.4 Kontrol (1 hafta sonra)
**MercekAbonelik → Maliyet Yönetimi → Maliyet analizi**: günlük maliyet ~0 olmalı. **Bütçeler**'de aylık bütçe ve %80 e-posta uyarısı kurulu olsun.

## 3. Geri aç

### 3.0 SQL veritabanı (silindiyse, 15 dk)
1. `mercek-sql-seyhan` → **+ Veritabanı oluştur** → ad **`mercekdb`** (aynı ad → `SQL_DATABASE` değişmez) → `docs/AZURE-SQL.md` §1:
   - Sürekli açık indexer isteniyorsa **Basic** (~5 $/ay, §1.1);
   - Ara sıra çalışma için **Ücretsiz Azure SQL Veritabanı teklifi** (0 $; kota bitince ay sonuna kadar duraklar). Bu durumda indexer'lar **Bir kez** zamanlamasında kalsın (`--zamanlamasiz`).
2. Veriyi yükle (repo kökünde, `backend\.env` hazır):
   ```cmd
   git pull
   uv run --directory backend python ..\scripts\load_sql.py
   uv run --directory backend python ..\scripts\setup_app_tables.py
   ```
3. Managed Identity kullanılıyorsa api kullanıcısını yeniden aç: `docs/AZURE-SQL.md` §4.2 ve §5.2 (`CREATE USER [mercek-api-seyhan] FROM EXTERNAL PROVIDER` …).
4. Search'ü yeniden bağla (görünümleri kurar, indexer'ları çalıştırır): §3.3'teki komut (ücretsiz teklifte `--zamanlamasiz` ekle).
5. Kontrol: `https://<api>/api/health` → 200; Mercek'te bir soru sor, Günlük akışında SQL hatası olmamalı.

### 3.1 App Service planı (3 dk)
1. `mercek-plan` → **Ölçeği artır** → §1'de not ettiğin katman (ör. **Basic B1**) → **Seç**.
2. api ve web → **Always On: Açık** · **Sistem durumu denetimi**: api `/api/health`, web `/giris` (`docs/AZURE-APP-SERVICE.md`).
3. Kontrol: `https://<api>/api/health` → `{"status":"ok"}`.

### 3.2 AI Search (silindiyse, 15 dk)
1. **Yeniden oluştur:** `docs/AZURE-AI-SEARCH.md` §2. Resource group **rg_mercek**, ad **`mercek-search-seyhan`** (aynı ad → `SEARCH_ENDPOINT` değişmez; ad hemen alınamazsa birkaç dakika bekle ya da yeni ad verip §3.2.4'te endpoint'i de güncelle), bölge **Norway East** (doluysa açık bir yakın bölge), katman §1'deki.
2. **Anahtarlar → API erişim denetimi:** §1'deki değer (öneri **Her ikisi**). Yeni **birincil yönetici anahtarı**'nı `backend\.env` → `SEARCH_API_KEY`'e yaz (eski anahtar artık geçersiz).
3. **İndeksleri kur** (repo kökünde):
   ```cmd
   git pull
   uv run --directory backend python ..\scripts\build_search_index.py --indeks hepsi
   ```
   Beklenen: `mercek-loglar` 107 belge, `mercek-cozumler` 37 belge (`docs/AZURE-AI-SEARCH.md` §3, §6.1).
4. **api'yi bağla** (`mercek-api-seyhan` → Ortam değişkenleri):
   - Anahtarla: `SEARCH_API_KEY` = yeni **sorgu anahtarı** (Search → Anahtarlar → Sorgu anahtarlarını yönet → Ekle).
   - Managed Identity ile: Search → **Erişim denetimi (IAM)** → **Search Index Data Reader** → Yönetilen kimlik → App Service → `mercek-api-seyhan` (`docs/AZURE-AI-SEARCH.md` §5). Rol, silinen servisle birlikte gitmiştir; mutlaka yeniden ver.
   - `SEARCH_ENDPOINT`, `SEARCH_LOG_INDEX`, `SEARCH_SOLUTION_INDEX` aynı adla kurduysan değişmez.
5. Kontrol: Mercek'te "abone numarasını sistem kabul etmiyor" → Günlük akışında `ad=hata_ara ... sonuç=5`.

### 3.3 Indexer zamanlaması kapatıldıysa
```cmd
uv run --directory backend python ..\scripts\build_search_index.py --indeks hepsi
```
(`--zamanlamasiz` olmadan; 5 dk zamanlaması geri gelir.)

## 4. Abonelik taşıma sonrası (bir kez)

Taşımada **IAM rol atamaları taşınmaz**. Taşınan kaynaklarda Erişim denetimi (IAM) → Rol atamaları'na bak; eksikse yeniden ver
(ör. Search'te `Search Index Data Reader` → `mercek-api-seyhan`). SQL içindeki kullanıcılar (`CREATE USER … FROM EXTERNAL PROVIDER`)
veritabanında durur, taşımadan etkilenmez.

`mercek-appinsights` ve bağlı olduğu `DefaultWorkspace-78d24885-…` (Log Analytics) **Azure subscription 1 / DefaultResourceGroup-WEU**'dan
**MercekAbonelik / rg_mercek**'e taşınır. Aynı gruptaki `DefaultWorkspace-b25c9223-…-WEU` ve `TutoringCenterManagerapi` başka projeye aittir; taşınmaz.

### 4.1 Foundry eski abonelikte kaldı (karar: 24.10.2026)
`seyhanamasyali-7898-resource` (endpoint `https://seyhanamasyali-7898-resource.openai.azure.com`) **Azure subscription 1 /
DefaultResourceGroup-WEU**'da duruyor. Taşıma doğrulaması reddetti: MercekAbonelik'te model kotası yok
(`TargetMoveSubscriptionNotEligible`: `AIServices.GlobalStandard.claude-haiku-5-5` 50 gerekli / 0 kalan,
`OpenAI.GlobalStandard.gpt-5.5` 500 gerekli / 0 kalan). Token başına ücretlendiği için kullanılmazken 0 $; kullanılırsa
fatura **Azure subscription 1**'e yazar. Uygulama ayarları (`AZURE_OPENAI_*`) değişmedi.

Projeye dönüldüğünde iki yol:
1. **Kota iste, sonra taşı:** ai.azure.com → Yönetim merkezi → **Kota** → abonelik **MercekAbonelik**, bölge **Sweden Central** →
   `gpt-5.5`, `claude-haiku-5-5` ve embedding modeli için en az mevcut deploy kapasitesi kadar kota iste. Onay gelince
   DefaultResourceGroup-WEU → **Taşı → Başka bir aboneliğe taşı** → Foundry kaynağı ve projesi → hedef **rg_mercek**.
   Ad, endpoint ve anahtar değişmez.
2. **Yeni Foundry kur:** MercekAbonelik'te yeni Foundry + deploy'lar (`docs/AZURE-AI-SEARCH.md` §1, `docs/FOUNDRY-AGENT.md`).
   Yeni endpoint/anahtar: App Service ortam değişkenleri ve `backend\.env`; ardından `build_search_index.py --indeks hepsi`
   (embedding becerisi ve vektörleştirici yeni adresi alır) ve agent kurulumu (`scripts/setup_agent.py`). Eski Foundry en son silinir.
