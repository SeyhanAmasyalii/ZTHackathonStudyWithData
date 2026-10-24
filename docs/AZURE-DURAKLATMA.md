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
| `mercekdb` | SQL veritabanı | Sweden Central | **Basic (Temel)** ~5 $/ay, sabit (24.10.2026'da kontrol edildi) | Tut (§2.3) |
| Foundry (`chat`, `text-embedding-3-small`) | AI Foundry | — | Hayır (kullanılan token kadar) | Dokunma. Bu resource group'ta değil; yeri ayrıca kontrol edilecek |

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

### 2.3 SQL veritabanı (isteğe bağlı)
Basic ~5 $/ay; durdurulamaz. Tutmak önerilir. Silinirse veri `scripts/load_sql.py` ile yeniden yüklenir (`docs/AZURE-SQL.md`).

### 2.4 Kontrol (1 hafta sonra)
**MercekAbonelik → Maliyet Yönetimi → Maliyet analizi**: günlük maliyet ~0 olmalı. **Bütçeler**'de aylık bütçe ve %80 e-posta uyarısı kurulu olsun.

## 3. Geri aç

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
veritabanında durur, taşımadan etkilenmez. Foundry kaynağı **rg_mercek**'te değil: yerini bul, istenirse aynı yolla
(**Taşı → Başka bir aboneliğe taşı**) MercekAbonelik'e al; taşınamazsa yeniden kur ve `AZURE_OPENAI_*` ayarlarını güncelle.
