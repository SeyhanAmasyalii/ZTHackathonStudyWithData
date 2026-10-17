# Mercek — Azure AI Search (portal ile)

> Hedef: Kibana hata türleri Azure AI Search'te (`mercek-loglar`, hibrit arama: kelime + vektör) dursun;
> Mercek kullanıcının tarifinden (ör. "abone numarasını kabul etmiyor") doğru ekranı ve hatayı `hata_ara` aracıyla bulsun.
> Sayım, zaman aralığı ve "yalnızca benim loglarım" filtresi yine `kibana_sorgula`'da (kodda) kalır.
> Önce `docs/AZURE-APP-SERVICE.md` (ve isteğe bağlı `docs/AZURE-SQL.md`) tamamlanmış olmalı. **Anahtar repoya yazılmaz.**

Aşağıda `<search>` = arama hizmeti adı (ör. `mercek-search-<takım>`), `<rg>` = resource group, `<api>` = backend uygulama adı.

## Nasıl çalışır

| Adım | Nerede |
|---|---|
| 2.002 Warning/Error logu → ekran + hata no + hata kodu + kurum bazında **107 hata türü belgesi** (ekran açıklaması, kurum, mesaj, `error_handling_rules` ipucu, 30 günlük sayılar) | `backend/app/services/log_index.py` |
| Her belgenin metni Foundry `text-embedding-3-small` ile vektöre çevrilir, indeks yeniden kurulur | `scripts/build_search_index.py` |
| Sohbette model `hata_ara(description)` çağırır → tarif vektöre çevrilir → hibrit arama (BM25 + vektör, RRF) → en iyi 5 hata türü | `backend/app/services/tools.py` |
| Model bulduğu ekran/hata no ile `kibana_sorgula` ve `cagri_ara`'yı çağırır | prompt `prompts/mercek-chat.md` |

`SEARCH_ENDPOINT` tanımlı değilse `hata_ara` modele hiç sunulmaz; Mercek eskisi gibi çalışır. Arama servisi hata verirse araç
"Hata araması şu an yapılamıyor" döner, sohbet durmaz.

## 1. Foundry'de embedding modeli (5 dk)

1. https://ai.azure.com → proje → **Modeller + uç noktalar** (ya da **Dağıtımlar**) → **+ Model dağıt** → **Temel modeli dağıt**.
2. `text-embedding-3-small` → **Onayla** → Dağıtım adı: `text-embedding-3-small` · Tür: **Global Standart** (yoksa Standart) → **Dağıt**.
3. Uç nokta ve anahtar sohbet modeliyle (`gpt-5.5`) aynıdır. Adı farklı verirseniz `EMBEDDING_DEPLOYMENT` ayarına yazın.

## 2. AI Search hizmeti (5 dk)

1. Portal → arama: `AI Search` → **Hizmetler** altında **Yapay Zeka Arama (Foundry IQ)** (Türkçe portalda Azure AI Search'ün adı) → **+ Oluştur**.
   Market altındaki **Azure AI Search** de aynı kaynağı açar; Allfind/Algolia gibi üçüncü taraf ürünleri seçmeyin.
2. Resource group: `<rg>` · Hizmet adı: `<search>` · Konum: Foundry ile aynı (Ücretsiz katman o bölgede yoksa yakın bir bölge, ör. West Europe)
   · Fiyatlandırma katmanı: **Fiyatlandırma katmanını değiştir → Ücretsiz** (3 indeks, 50 MB; bize 1 indeks, ~2 MB yeter).
   Hackathon aboneliğinde takıma verilen katman neyse o.
3. **Gözden geçir + oluştur** → **Oluştur** → **Kaynağa git**.
4. **Genel Bakış → Url** (`https://<search>.search.windows.net`) not edin.
5. **Güvenlik ve ağ → Anahtarlar** (eski portalda Ayarlar → Anahtarlar) → API Erişim denetimi: **Her ikisi** → Kaydet. **Birincil yönetici anahtarı**'nı kopyalayın
   (yalnızca bilgisayarınızdaki `backend\.env`'e yazılır).

## 3. İndeksi doldur (bilgisayarda, 1 dk)

`backend\.env`'e ekleyin (git'e girmez):

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

Beklenen:

```
✓ 107 hata türü (2002 log)
✓ Vektörler hazır (text-embedding-3-small, 1536 boyut)
✓ İndeks 'mercek-loglar': 107 belge
Örnek arama: 'abone numarası kabul edilmiyor'
  ODMTTLMT 110412 SUBSCRIBER_NO_INVALID SU01 · 400 log · Abone numarası 13 hane; ekran 6–12 hane kabul ediyor.
  ...
```

Betik indeksi her seferinde silip yeniden kurar; tekrar çalıştırmak güvenlidir. Portalda kontrol: `<search>` → **Arama yönetimi → Dizinler**
→ `mercek-loglar` → **Belge sayısı 107**; **Arama gezgini**'nde `abone` yazıp **Ara**.

## 4. App Service'e bağla (3 dk)

`<api>` → **Ayarlar → Ortam değişkenleri** → **+ Ekle** → **Uygula**

| Ad | Değer |
|---|---|
| `SEARCH_ENDPOINT` | `https://<search>.search.windows.net` |
| `SEARCH_LOG_INDEX` | `mercek-loglar` |
| `EMBEDDING_DEPLOYMENT` | `text-embedding-3-small` |
| `SEARCH_API_KEY` | **Sorgu anahtarı** (`<search>` → Güvenlik ve ağ → Anahtarlar → **Sorgu anahtarlarını yönet** → Ekle; yalnızca arama yapabilir). 5. adımı yaparsanız bu satırı eklemeyin |

Backend paketini yeniden üretip yükleyin (yeni kod + `azure-identity`, `httpx`):

```cmd
python scripts\package_azure.py --only api
```
Cloud Shell → Karşıya yükle → `az webapp deploy -g <rg> -n <api> --src-path mercek-api.zip --type zip`

Kontrol: Mercek'te Elif → **"abone numarasını sistem kabul etmiyor"** → Günlük akışında
`Araç çağrısı: tur=1 ad=hata_ara ... sonuç=5`, ardından `ad=kibana_sorgula` (ODMTTLMT, 110412). Cevap İSKİ 13 hane sorununu anlatmalı.

## 5. (Ek puan) Anahtarsız: Managed Identity

`<api>`'nin sistem kimliği `docs/AZURE-SQL.md` §4.1'de açıldıysa tekrar açmaya gerek yok.

1. `<search>` → **Erişim denetimi (IAM)** → **+ Ekle → Rol ataması ekle** → Rol: **Search Index Data Reader** → İleri
   → Erişim ata: **Yönetilen kimlik** → **+ Üye seç** → Yönetilen kimlik: **App Service** → `<api>` → Seç → **Gözden geçir + ata**.
2. `<search>` → Anahtarlar → API Erişim denetimi **Her ikisi** (ya da **Rol tabanlı**) olmalı.
3. `<api>` → Ortam değişkenleri → `SEARCH_API_KEY` satırını **silin** → Uygula. Kod anahtar yoksa Entra token'ı kullanır.
4. Rol atamasının etkinleşmesi 5–10 dk sürebilir; bu sürede 403 görülebilir.

## Sorun giderme

| Belirti | Çözüm |
|---|---|
| Oluşturma: `The region '...' is currently out of the resources required to provision new services` | O bölgede kapasite yok (özellikle Ücretsiz katman). Aynı adla başka bölgede tekrar oluşturun (ör. West Europe, North Europe); başarısız dağıtım kaynak bırakmaz. Arama farklı bölgede olabilir, kod etkilenmez |
| Betik: `SEARCH_ENDPOINT tanımlı değil` | `backend\.env`'de `SEARCH_ENDPOINT` yok |
| Betik: `Embedding çağrısı başarısız: NotFoundError` | Foundry'de embedding deploy'u yok ya da adı `EMBEDDING_DEPLOYMENT` ile aynı değil |
| Betik: `Arama servisi 403` | Yönetici anahtarı yanlış/eksik (sorgu anahtarı indeks oluşturamaz) |
| Betik: `Arama servisi 400 ... analyzer` | Hizmet çok eski API'de; portalda katman/bölge doğru mu, URL `https://<search>.search.windows.net` mi |
| Sohbette `hata_ara` hiç çağrılmıyor | `<api>`'de `SEARCH_ENDPOINT` yok (araç sunulmaz) ya da kullanıcı ekran/hata kodunu zaten söyledi (o zaman gerekmez) |
| Günlükte `hata_ara başarısız: Arama servisi 403` | App Service anahtarı yanlış ya da MI rol ataması henüz etkinleşmedi (5. adım) |
| Günlükte `hata_ara başarısız: Arama servisi 404` | İndeks yok: 3. adımı çalıştırın; `SEARCH_LOG_INDEX` adı aynı mı |
