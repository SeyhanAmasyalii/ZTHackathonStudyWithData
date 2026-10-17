# Mercek — Azure AI Search (portal ile)

> Hedef: Kibana hata türleri Azure AI Search'te (`mercek-loglar`, hibrit arama: kelime + vektör) dursun ve
> **veriyi Azure SQL'den kendisi, 5 dakikada bir alsın**. Mercek kullanıcının tarifinden (ör. "abone numarasını kabul etmiyor")
> doğru ekranı ve hatayı `hata_ara` aracıyla bulsun. Sayım, zaman aralığı ve "yalnızca benim loglarım" yine `kibana_sorgula`'da (kodda).
> Ön koşul: `docs/AZURE-APP-SERVICE.md` ve `docs/AZURE-SQL.md` (veri SQL'de yüklü). **Anahtar/parola repoya yazılmaz.**

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
✓ SQL görünümü dbo.v_hata_turleri: 107 hata türü
✓ AI Search: veri kaynağı, indeks 'mercek-loglar', embedding becerisi, indexer (5 dakikada bir)
✓ Indexer çalıştı: 107 belge işlendi · indekste 107 belge
Örnek arama: 'abone numarası kabul edilmiyor'
  ODMTTLMT 110412 SUBSCRIBER_NO_INVALID SU01 · 400 log · Abone numarası 13 hane; ekran 6–12 hane kabul ediyor.
```

Bundan sonra **betiği tekrar çalıştırmak gerekmez**: indexer 5 dakikada bir SQL'e bakar, yalnızca değişen hata türlerini alır.
`scripts\load_sql.py` ile veri yeniden yüklenirse görünüm de yenilenir; indexer sonraki çalışmasında değişiklikleri alır.

Portalda kontrol: `<search>` → **Arama yönetimi → Dizin oluşturucular** → `mercek-loglar-indexer` → **Yürütme geçmişi** (5 dk'da bir satır);
**Dizinler** → `mercek-loglar` → belge sayısı **107**; **Arama gezgini**'nde `abone` → Ara.

### Ücretsiz SQL ile zamanlama (prova)
Indexer 5 dakikada bir sorgu attığı için **ücretsiz (serverless) SQL veritabanı uykuya geçemez** ve aylık ücretsiz kota
(100.000 vCore-saniye) birkaç günde biter; dolunca veritabanı ay sonuna kadar durur (Mercek JSON'a düşer). Bu yüzden provadan sonra:

- Zamanlamayı kapatmak için: `uv run --directory backend python ..\scripts\build_search_index.py --zamanlamasiz`
  (indeks yine kurulur ve bir kez dolar; sonra kendiliğinden çalışmaz) **ya da** portalda `mercek-loglar-indexer` → **Zamanlama** → **Bir kez**.
- Demodan önce zamanlamayı açmak için betiği `--zamanlamasiz` olmadan tekrar çalıştırın.
- Hackathon ortamındaki SQL ücretli bir katmandaysa bu sorun yoktur; 5 dk açık kalabilir.

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

1. `<search>` → **Erişim denetimi (IAM)** → **+ Ekle → Rol ataması ekle** → Rol: **Search Index Data Reader** → İleri
   → Erişim ata: **Yönetilen kimlik** → **+ Üye seç** → Yönetilen kimlik: **App Service** → `<api>` → Seç → **Gözden geçir + ata**.
2. `<search>` → Anahtarlar → API Erişim denetimi **Her ikisi** (ya da **Rol tabanlı**) olmalı.
3. `<api>` → Ortam değişkenleri → `SEARCH_API_KEY` satırını **silin** → Uygula. Kod anahtar yoksa Entra token'ı kullanır.
4. Rol atamasının etkinleşmesi 5–10 dk sürebilir; bu sürede `hata_ara` 403 alabilir (sohbet yine çalışır).

**AI Search → SQL ve Foundry** (indexer, beceri, vektörleştirici) şimdilik SQL kullanıcısı ve Foundry anahtarıyla, AI Search içinde saklanır.
Bunları da kimliğe çevirmek AI Search'ün sistem kimliğini gerektirir (Ücretsiz katmanda bulunmayabilir); ücretli katmanda ayrı adım.

## Sorun giderme

| Belirti | Çözüm |
|---|---|
| Oluşturma: `The region '...' is currently out of the resources required to provision new services` | O bölgede kapasite yok (özellikle Ücretsiz katman). Aynı adla açık bir bölgede tekrar oluşturun; başarısız dağıtım kaynak bırakmaz. Arama farklı bölgede olabilir, kod etkilenmez |
| Betik: `backend/.env'de eksik: ...` | Adı geçen ayarı `.env`'e ekleyin |
| Betik: `Indexer için SQL_USER ve SQL_PASSWORD gerekli` | Indexer SQL'e SQL kullanıcısıyla bağlanır; `.env`'de bu iki satır olmalı (App Service'te olmaları gerekmez) |
| Betik: `SQL'e bağlanılamadı ... IP` | SQL güvenlik duvarına IP'nizi ekleyin (`docs/AZURE-SQL.md`) |
| Betik: `Arama servisi 403` | Yönetici anahtarı yanlış/eksik (sorgu anahtarı indeks/indexer oluşturamaz) |
| Betik: `✗ Indexer: transientFailure/persistentFailure ... Cannot open server` | AI Search SQL'e ulaşamıyor: SQL sunucusu → Ağ İletişimi → **Azure hizmetlerinin erişmesine izin ver** işaretli mi |
| Betik: `✗ Indexer: ... Login failed` | `.env`'deki SQL kullanıcısı/parolası yanlış |
| Betik: `✗ Indexer: ... embedding` / `DeploymentNotFound` / `401` | Foundry'de embedding deploy'u yok, adı `EMBEDDING_DEPLOYMENT` ile aynı değil ya da `AZURE_OPENAI_API_KEY` yanlış |
| Betik: `✗ Indexer 300 sn içinde bitmedi` | Ücretsiz SQL uykudan uyanıyor olabilir; portalda indexer **Yürütme geçmişi**'ne bakın, gerekirse betiği tekrar çalıştırın |
| Sohbette `hata_ara` hiç çağrılmıyor | `<api>`'de `SEARCH_ENDPOINT` yok (araç sunulmaz) ya da kullanıcı ekran/hata kodunu zaten söyledi (o zaman gerekmez) |
| Günlükte `hata_ara başarısız: Arama servisi 403` | App Service anahtarı yanlış ya da MI rol ataması henüz etkinleşmedi (5. adım) |
| Günlükte `hata_ara başarısız: Arama servisi 404` | İndeks yok: 3. adımı çalıştırın; `SEARCH_LOG_INDEX` adı aynı mı |
| Ay ortasında Mercek "JSON verisine geçildi" diyor | Ücretsiz SQL kotası dolmuş olabilir (indexer zamanlaması açık kaldı); §3 "Ücretsiz SQL ile zamanlama" |
