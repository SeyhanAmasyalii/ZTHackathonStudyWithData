# Mercek — Azure AI Search (portal ile)

> Hedef: Kibana hata türleri Azure AI Search'te (`mercek-loglar`, hibrit arama: kelime + vektör) dursun ve
> **veriyi Azure SQL'den kendisi, 5 dakikada bir alsın**. Mercek kullanıcının tarifinden (ör. "abone numarasını kabul etmiyor")
> doğru ekranı ve hatayı `hata_ara` aracıyla bulsun. Sayım, zaman aralığı ve "yalnızca benim loglarım" yine `kibana_sorgula`'da (kodda).
> Ön koşul: `docs/AZURE-APP-SERVICE.md` ve `docs/AZURE-SQL.md` (veri SQL'de yüklü; 5 dk zamanlama için SQL **Basic**, §1.1). **Anahtar/parola repoya yazılmaz.**

Aşağıda `<search>` = arama hizmeti adı (ör. `mercek-search-<takım>`), `<rg>` = resource group, `<api>` = backend uygulama adı.

## Nasıl çalışır

```
Azure SQL (mercekdb)                        Azure AI Search (<search>)
dbo.kibana_logs  ──►  dbo.v_hata_turleri ──► veri kaynağı ──► indexer (5 dk) ──► beceri: Foundry embedding ──► indeks mercek-loglar
(10.555 log)          (2.002 hata → 107 tür;   (yalnızca hwm'i                     (metin → vektör)              (kelime + vektör)
                       hwm = en yeni row_ver)   artan türler)                                                          ▲
                                                                                         Mercek: hata_ara(tarif) ───────┘
```

| Parça | Nerede |
|---|---|
| Görünüm `dbo.v_hata_turleri`: Warning/Error logları ekran + hata no + hata kodu + kurum bazında toplar (107 satır); ekran açıklaması, kurum, mesaj, `error_handling_rules` ipucu, sayılar; `hwm` = türün en yeni logunun `row_ver`'i | `db/search_views.sql` |
| Değişiklik takibi: `kibana_logs.row_ver` (ROWVERSION). Yeni log gelince o türün `hwm`'i artar; indexer yalnızca o türü yeniden işler | `db/search_views.sql` |
| Veri kaynağı, indeks, embedding becerisi, indexer tanımları | `backend/app/services/log_index.py` |
| Kurulum (bir kez) | `scripts/build_search_index.py` |
| Sohbette arama: tarif → AI Search (metni Foundry vektörleştiricisiyle kendisi vektöre çevirir) → hibrit arama (BM25 + vektör, RRF) → en iyi 5 tür | `backend/app/services/tools.py` (`hata_ara`) |

`SEARCH_ENDPOINT` tanımlı değilse `hata_ara` modele hiç sunulmaz; Mercek eskisi gibi çalışır. Arama hata verirse araç
"Hata araması şu an yapılamıyor" döner, sohbet durmaz. Indexer en sık **5 dakikada bir** çalışabilir (AI Search sınırı).

## 1. Foundry'de embedding modeli (5 dk)

Metni anlam araması için sayılara (vektöre) çeviren model; hem indexer hem sorgu tarafı (AI Search) kullanır.

1. https://ai.azure.com → proje → **Modeller + uç noktalar** (ya da **Dağıtımlar**) → **+ Model dağıt** → **Temel modeli dağıt**.
2. `text-embedding-3-small` → **Onayla** → Dağıtım adı: `text-embedding-3-small` · Tür: **Global Standart** (yoksa Standart) → **Dağıt**.
3. Uç nokta ve anahtar sohbet modeliyle (`gpt-5.5`) aynıdır. Adı farklı verirseniz `EMBEDDING_DEPLOYMENT` ayarına yazın.

## 2. AI Search hizmeti (5 dk)

1. Portal → arama: `AI Search` → **Hizmetler** altında **Yapay Zeka Arama (Foundry IQ)** (Türkçe portalda Azure AI Search'ün adı) → **+ Oluştur**.
   Market altındaki **Azure AI Search** de aynı kaynağı açar; Allfind/Algolia gibi üçüncü taraf ürünleri seçmeyin.
2. Resource group: `<rg>` · Hizmet adı: `<search>` · Konum: Foundry'ye yakın, **açık** bir bölge
   (gri olanlar "yüksek talep nedeniyle devre dışı"; ör. Sweden Central/West Europe doluysa Norway East, Germany North)
   · Fiyatlandırma katmanı: **Fiyatlandırma Katmanını Değiştir → Ücretsiz** (varsayılan **Standart ücretlidir**, mutlaka değiştirin).
   Hackathon aboneliğinde takıma verilen katman neyse o.
3. **Gözden geçir + oluştur**: Fiyatlandırma **Ücretsiz**, tahmini maliyet **$0,00** → **Oluştur** → **Kaynağa git**.
4. **Genel Bakış → URL** (`https://<search>.search.windows.net`) not edin.
5. **Güvenlik ve ağ → Anahtarlar** (eski portalda Ayarlar → Anahtarlar) → API Erişim denetimi: **Her ikisi** → Kaydet.
   **Birincil yönetici anahtarı**'nı kopyalayın (yalnızca bilgisayarınızdaki `backend\.env`'e yazılır).

## 3. Kurulum: AI Search'ü SQL'e bağla (bilgisayarda, 2 dk, bir kez)

`backend\.env`'de SQL ayarları (`docs/AZURE-SQL.md` §2: `SQL_SERVER`, `SQL_DATABASE`, `SQL_USER`, `SQL_PASSWORD`) olmalı.
Indexer SQL'e bu kullanıcıyla bağlanır; bağlantı bilgisi betik tarafından **AI Search'e kaydedilir**, repoya yazılmaz. Ekleyin:

```
SEARCH_ENDPOINT=https://<search>.search.windows.net
SEARCH_API_KEY=<birincil yönetici anahtarı>
SEARCH_LOG_INDEX=mercek-loglar
EMBEDDING_DEPLOYMENT=text-embedding-3-small
```

Repo kökünde (CMD):

```cmd
cd /d <repo-klasörü>
git pull
uv run --directory backend python ..\scripts\build_search_index.py
```

Beklenen (1–3 dk):

```
✓ SQL görünümleri: dbo.v_hata_turleri 107 hata türü · dbo.v_cozum_sablonlari 37 hazır çözüm
✓ AI Search: veri kaynağı, indeks 'mercek-loglar', embedding becerisi, indexer (5 dakikada bir)
✓ Indexer çalıştı: 107 belge işlendi · indekste 107 belge
Örnek arama: 'abone numarası kabul edilmiyor'
  ODMTTLMT 110412 SUBSCRIBER_NO_INVALID SU01 · 400 log · Abone numarası 13 hane; ekran 6–12 hane kabul ediyor.
```

Bundan sonra **betiği tekrar çalıştırmak gerekmez**: indexer 5 dakikada bir SQL'e bakar, yalnızca değişen hata türlerini alır.
`scripts\load_sql.py` ile veri yeniden yüklenirse görünüm de yenilenir; indexer sonraki çalışmasında değişiklikleri alır.

Portalda kontrol: `<search>` → **Arama yönetimi → Dizin oluşturucular** → `mercek-loglar-indexer` → **Yürütme geçmişi** (5 dk'da bir satır);
**Dizinler** → `mercek-loglar` → belge sayısı **107**; **Arama gezgini**'nde `abone` → Ara.

### SQL katmanı ve zamanlama
Indexer 5 dakikada bir SQL'e bağlandığı için **SQL veritabanı uykuya geçemez**:

| SQL katmanı | 5 dk zamanlama | Maliyet |
|---|---|---|
| **Basic (5 DTU)** — önerilen | Sürekli açık kalabilir | ~5 $/ay, sabit (`docs/AZURE-SQL.md` §1.1) |
| Ücretsiz (serverless) | Yalnızca test/demo günlerinde (aylık kota ~2 günde biter, dolunca veritabanı ay sonuna kadar durur) | 0 $ |
| Hackathon ortamının SQL'i (takıma verilen, ücretli) | Sürekli açık kalabilir | Takımın değil |

Ücretsiz SQL kullanıyorsanız provadan sonra zamanlamayı kapatın:
`uv run --directory backend python ..\scripts\build_search_index.py --zamanlamasiz` (indeks yine kurulur ve bir kez dolar)
**ya da** portalda `mercek-loglar-indexer` → **Zamanlama** → **Bir kez**. Demodan önce betiği `--zamanlamasiz` olmadan tekrar çalıştırın.

## 4. App Service'e bağla (3 dk)

`<api>` → **Ayarlar → Ortam değişkenleri** → **+ Ekle** → **Uygula**

| Ad | Değer |
|---|---|
| `SEARCH_ENDPOINT` | `https://<search>.search.windows.net` |
| `SEARCH_LOG_INDEX` | `mercek-loglar` |
| `SEARCH_API_KEY` | **Sorgu anahtarı** (`<search>` → Güvenlik ve ağ → Anahtarlar → **Sorgu anahtarlarını yönet** → Ekle; yalnızca arama yapabilir). 5. adımı yaparsanız bu satırı eklemeyin |

Backend embedding modelini çağırmaz (sorgu metnini AI Search vektöre çevirir); `EMBEDDING_DEPLOYMENT` App Service'te gerekmez.

Backend paketini yeniden üretip yükleyin (yeni kod + `azure-identity`, `httpx`):

```cmd
python scripts\package_azure.py --only api
```
Cloud Shell → Karşıya yükle → `az webapp deploy -g <rg> -n <api> --src-path mercek-api.zip --type zip`

Kontrol: Mercek'te Elif → **"abone numarasını sistem kabul etmiyor"** → Günlük akışında (F5)
`Araç çağrısı: tur=1 ad=hata_ara ... sonuç=5`, ardından `ad=kibana_sorgula` (ODMTTLMT, 110412). Cevap İSKİ 13 hane sorununu anlatmalı.

## 5. (Ek puan) Anahtarsız: Managed Identity

**Backend → AI Search** (sorgu): `<api>`'nin sistem kimliği `docs/AZURE-SQL.md` §4.1'de açıldıysa tekrar açmaya gerek yok.

1. `<search>` → **Erişim denetimi (IAM)** → **+ Ekle → Rol ataması ekle** → Rol: **Search Index Data Reader** (Türkçe portalda **Arama Dizini Veri Okuyucusu**; aramaya `Arama` yazın, "Yönetilen Uygulama…" rolünü seçmeyin) → İleri
   → Erişim ata: **Yönetilen kimlik** → **+ Üye seç** → Yönetilen kimlik: **App Service** → `<api>` → Seç → **Gözden geçir + ata**.
2. `<search>` → **Ayarlar → Anahtarlar** (bazı portallarda Güvenlik ve ağ → Anahtarlar) → API Erişim denetimi **Her ikisi** (ya da **Rol tabanlı**) olmalı
   (yalnızca "API anahtarı" seçiliyse rol atamaları dikkate alınmaz).
3. Rol atamasının etkinleşmesi için **5–10 dk bekleyin**, sonra **API uygulamasını** açın (AI Search değil): `<api>` → Ortam değişkenleri → `SEARCH_API_KEY` satırını **silin** → Uygula.
   Kod anahtar yoksa Entra token'ı (App Service'te Managed Identity) kullanır. Silinen sorgu anahtarını `<search>` → Anahtarlar →
   Sorgu anahtarlarını yönet'ten de silebilirsiniz.
4. Kontrol: Mercek'te "abone numarasını sistem kabul etmiyor" → Günlük akışında (F5) `ad=hata_ara ... sonuç=5` ve
   `DefaultAzureCredential acquired a token from ManagedIdentityCredential`. `sonuç=Hata araması şu an yapılamıyor` ve üstünde
   `hata_ara başarısız: Arama servisi 403` görürseniz rol ataması henüz etkinleşmemiştir (birkaç dakika sonra tekrar deneyin) ya da 1–2. adım eksiktir.

**AI Search → SQL ve Foundry** (indexer, beceri, vektörleştirici) şimdilik SQL kullanıcısı ve Foundry anahtarıyla, AI Search içinde saklanır.
Bunları da kimliğe çevirmek AI Search'ün sistem kimliğini gerektirir (Ücretsiz katmanda bulunmayabilir); ücretli katmanda ayrı adım.

## 6. Hazır çözümler: `benzer_cozum_ara` (indeks `mercek-cozumler`, 5 dk)

**Ne yapar:** kullanıcının sorununu 37 hazır çözüm şablonuyla (SOL-xxx) anlamca eşleştirir. Her şablon belgesine o şablonla
**kapatılmış çağrıların notları** eklenir ("Kullanıcıların yazdıkları: adres bölümü kaydedilemiyor | …"): kullanıcı sorunu kendi
kelimeleriyle anlatsa da eşleşir. Müşteri numarası ve kişi bilgisi indekse girmez (görünüm yalnızca not metnini alır).

**Eşleşme yüzdesini kod hesaplar** (`backend/app/services/solution_index.py`): AI Search vektör puanı cosine benzerliğine çevrilir,
0,40 → %0 ve 0,72 → %100 aralığına ölçeklenir, model hata kodunu da verdiyse ve şablonun hata kodu aynıysa +25 puan.
Ölçüm (prova): doğru şablon 0,65–0,67 benzerlik, yakın ama yanlış 0,58–0,63, ilgisiz ~0,25. Birbirine yakın şablonları
(ör. üç "zaman aşımı" şablonu) metin tek başına ayıramaz; hata kodu ayırır (SOL-031 `INSTITUTION_TIMEOUT`, SOL-032 `CORE_BANKING_TIMEOUT`).
**%75** ve üstü eşleşmedir; altı "hazır çözüm yok" sayılır, model bunu çözüm gibi sunmaz.

Akış `hata_ara` ile aynı: SQL görünümü `dbo.v_cozum_sablonlari` → veri kaynağı (yüksek su işareti: şablon ya da ona bağlı bir çağrı
değişince) → indexer 5 dk'da bir → Foundry embedding → indeks. Free katmanda bu 2. indekstir (sınır 3).

### 6.1 Kur (bilgisayarda, repo kökünde, 1–2 dk)
`backend\.env` §3'teki gibi (yönetici anahtarıyla). Ek ayar gerekmez; indeks adı varsayılan `mercek-cozumler`.
```cmd
git pull
uv run --directory backend python ..\scripts\build_search_index.py --indeks cozumler
```
Beklenen:
```
✓ SQL görünümleri: dbo.v_hata_turleri 107 hata türü · dbo.v_cozum_sablonlari 37 hazır çözüm
✓ AI Search: veri kaynağı, indeks 'mercek-cozumler', embedding becerisi, indexer (5 dakikada bir)
✓ Indexer çalıştı: 37 belge işlendi · indekste 37 belge
Arama: 'müşteri adres bilgisini kaydedemiyorum' (eşik %75)
  ✓ SOL-026 %NN (benzerlik 0.xxx) ...
```
Hackathon ortamında iki indeksi birden kurmak için: `--indeks hepsi`.

### 6.2 Eşiği dene (isteğe bağlı, kurulum yapmaz)
```cmd
uv run --directory backend python ..\scripts\build_search_index.py --dene "adres değişikliği yapamıyorum, alan hatası veriyor"
uv run --directory backend python ..\scripts\build_search_index.py --dene "Input string was not in a correct format"
```
İlki SOL-026'yı ✓ ile (≥ %75), ikincisi ✓'siz (hazır çözüm yok) göstermeli. `--dene` hata kodu vermez; sohbette model
hata kodunu da verdiğinde (ör. INSTITUTION_TIMEOUT) aynı kodlu şablon +25 puan alır. Olmazsa çıktıyı paylaşın:
`SIMILARITY_FLOOR` / `SIMILARITY_CEIL` (solution_index.py) ölçülen benzerliklere göre ayarlanır.

### 6.3 App Service'e bağla
`<api>` → **Ortam değişkenleri** → **+ Ekle**: `SEARCH_SOLUTION_INDEX` = `mercek-cozumler` → **Uygula**.
Bu ayar yoksa araç modele sunulmaz (indeks kurulmadan önce açılmasın diye).
Managed Identity (§5) kullanıyorsanız ek rol gerekmez: **Search Index Data Reader** hizmetteki tüm indeksleri kapsar.
Backend paketini yeniden üretip yükleyin (`docs/AZURE-APP-SERVICE.md`; yalnızca API: `python scripts\package_azure.py --only api`).

### 6.4 Kontrol
- Zeynep → **"Müşteri adres değişikliği yapamıyorum, alan hatası veriyor"** → Günlük akışında `ad=benzer_cozum_ara` (ya da `cagri_ara`
  yeterliyse çağrılmayabilir); cevapta **SOL-026** ve eşleşme yüzdesi.
- Kerem → **"Müşteri güncelleme ekranında 'Input string was not in a correct format' hatası"** → `benzer_cozum_ara` çağrılır,
  **hazır çözüm bulunmadığını** söyler (eşik altı), ekibe iletmeyi önerir.

## Sorun giderme

| Belirti | Çözüm |
|---|---|
| Oluşturma: `The region '...' is currently out of the resources required to provision new services` | O bölgede kapasite yok (özellikle Ücretsiz katman). Aynı adla açık bir bölgede tekrar oluşturun; başarısız dağıtım kaynak bırakmaz. Arama farklı bölgede olabilir, kod etkilenmez |
| Betik: `backend/.env'de eksik: ...` | Adı geçen ayarı `.env`'e ekleyin |
| Betik: `Indexer için SQL_USER ve SQL_PASSWORD gerekli` | Indexer SQL'e SQL kullanıcısıyla bağlanır; `.env`'de bu iki satır olmalı (App Service'te olmaları gerekmez) |
| Betik: `SQL'e bağlanılamadı ... IP` | SQL güvenlik duvarına IP'nizi ekleyin (`docs/AZURE-SQL.md`) |
| Betik: `Arama servisi 403` | Yönetici anahtarı yanlış/eksik (sorgu anahtarı indeks/indexer oluşturamaz) |
| Betik: `✗ Indexer: transientFailure/persistentFailure ... Cannot open server` | AI Search SQL'e ulaşamıyor: SQL sunucusu → Ağ İletişimi → **Azure hizmetlerinin erişmesine izin ver** işaretli mi |
| Betik: `Arama servisi 400 ... Login failed for user` (veri kaynağı oluşturulurken) ya da `✗ Indexer: ... Login failed` | AI Search SQL'e `.env`'deki kullanıcıyla bağlanamadı: parola yanlış ya da eski betik sürümü (ADO.NET biçimi düzeltildi; `git pull` yapıp tekrar çalıştırın) |
| Betik: `✗ Indexer: ... embedding` / `DeploymentNotFound` / `401` | Foundry'de embedding deploy'u yok, adı `EMBEDDING_DEPLOYMENT` ile aynı değil ya da `AZURE_OPENAI_API_KEY` yanlış |
| Betik: `✗ Indexer 300 sn içinde bitmedi` | Ücretsiz SQL uykudan uyanıyor olabilir; portalda indexer **Yürütme geçmişi**'ne bakın, gerekirse betiği tekrar çalıştırın |
| Sohbette `hata_ara` hiç çağrılmıyor | `<api>`'de `SEARCH_ENDPOINT` yok (araç sunulmaz) ya da kullanıcı ekran/hata kodunu zaten söyledi (o zaman gerekmez) |
| Günlükte `hata_ara başarısız: Arama servisi 403` | App Service anahtarı yanlış ya da MI rol ataması henüz etkinleşmedi (5. adım) |
| Günlükte `benzer_cozum_ara başarısız: Arama servisi 404` | `mercek-cozumler` indeksi yok: §6.1'i çalıştırın; `SEARCH_SOLUTION_INDEX` adı aynı mı |
| `--dene`'de doğru şablon ✓ almıyor / ilgisiz şablon ✓ alıyor | Eşik ölçeği ayarı: çıktıdaki benzerlik değerlerini paylaşın (§6.2) |
| Günlükte `hata_ara başarısız: Arama servisi 404` | İndeks yok: 3. adımı çalıştırın; `SEARCH_LOG_INDEX` adı aynı mı |
| Ay ortasında Mercek "JSON verisine geçildi" diyor | Ücretsiz SQL kotası dolmuş olabilir (indexer zamanlaması açık kaldı); SQL'i Basic'e alın ya da zamanlamayı kapatın (§3 "SQL katmanı ve zamanlama") |
