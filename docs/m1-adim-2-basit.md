# M1 · 2. adım — İlgili logu bulma (önce bunu yapın)

> Önceki adım: [`m1-adim-1-basit.md`](m1-adim-1-basit.md) (fiş). Görev listesi: [`m1-adim-2-gorevler.md`](m1-adim-2-gorevler.md).

## 0. Kapsam kararları (16.10)

- Odak: **kullanıcı sorununu yazar → Mercek çözüm önerir.** Demoda kayıt yazılmaz (çağrı açma, önlenen çağrı, canlı log yok).
- Tüm veri **`datav2/*.json`**. AI Search indeksi JSON'dan betikle doldurulur (push).
- Demo saati sabit: **`DEMO_NOW=2026-10-17T09:15+03:00`** (veri 09:00'da biter).
- A senaryosu (KRDTKULL, canlı log) kapsam dışı.

## 1. Ne yapar

1. adımdaki fişi ve oturumdaki kullanıcıyı alır, `kibana_logs` içinden **kullanıcının sorduğu hata logunu** bulur. Kendi logu yoksa aynı konudaki **başkalarının** hatasını bulur (C).

**Örnek** (09:15, kullanıcı Elif):

> "Az önce Başkentgaz talimatında kurumdan yanıt alamadım"

Fiş: bugün · 08:45–09:15 · ODMTTLMT · GAZ02 → filtre `user_name = elif` →

```
mode       own
signature  ODMTTLMT · 110731 INSTITUTION_TIMEOUT · GAZ02
count      8 (Elif bu sabah 8 kez denemiş, 8 farklı müşteri)
log        08:57:46 · müşteri 10018499 · "GAZ02 kurum servisi 8000 ms içinde yanıt vermedi."
```

3. adım bu `signature` ile kuralı, 4. adım örüntüyü bulur.

## 2. Akış

```
fiş + user_name
 │
 ├─ 1. tur · KENDİ LOGU   (AI Search, filtreli)
 │     filtre: müşteri no varsa customer_id, yoksa user_name
 │             + tarih + saat aralığı + (ekran) + (kurum) + Warning/Error
 │     sonuç yoksa: saat aralığını kaldırıp bütün güne bak
 │     ├─ tek hata türü         → mode = own     (en son logu seç)
 │     └─ birden fazla hata türü → mode = choose  (en fazla 3 seçenek kullanıcıya)
 │
 └─ 2. tur · İLGİLİ HATA  (kendi logu yoksa; fişte ekran ya da kurum varsa)
       filtre: kullanıcı YOK · son 7 gün · (ekran) · (kurum) · Warning/Error
       sorgu: fiş.search_text (metin + anlam)
       ├─ sonuç var → mode = related (en çok tekrarlanan hata türü)
       └─ sonuç yok → mode = none    ("Kaydınızı bulamadım, biraz daha ayrıntı verir misiniz?")
```

**Hata türü (`signature`)** = `(screen_id, app_exception_value, institution_code)`. Aynı türdeki loglar tek seçenek sayılır (Elif'in 8 logu = 1 tür).

**Neden AI Search:** 1. turda filtre zaten çok daraltır. Asıl değer 2. turda: "13 haneli abone numarasını kabul etmiyor" cümlesi, kelimeleri aynı olmasa da "Abone numarası 13 hane; ekran 6–12 hane kabul ediyor" logunu anlamca bulur.

## 3. AI Search indeksi `kibana_logs`

**Doldurma:** `scripts/index_kibana_logs.py` (bir kez çalışır; tekrar çalışınca indeksi baştan kurar).
- `datav2/kibana_logs.json` → yalnızca **Warning ve Error** (2.002 kayıt).
- `institution_code` ve `subscriber_no_length` → `message_fields` JSON'undan.
- `search_text` = ekran adı + hata kodu + `exception_message` (yoksa `message`).
- `content_vector` = Foundry `embedding` deploy'u ile `search_text`'in vektörü (16'lı partiler).

| Alan | Tür | Özellik |
|---|---|---|
| `log_id` | string | anahtar |
| `log_time` | DateTimeOffset | filtre, sıralama |
| `log_level` | string | filtre |
| `user_name` | string | filtre |
| `customer_id` | string | filtre |
| `branch_id` | int | filtre |
| `screen_id` | string | filtre |
| `app_exception_value` | int | filtre |
| `error_code` | string | filtre (`message_response.errorCode`) |
| `institution_code` | string | filtre |
| `correlation_id` | string | dönüş |
| `message`, `exception_message` | string | aranabilir, Türkçe analizör (`tr.microsoft`) |
| `search_text` | string | aranabilir, Türkçe analizör |
| `content_vector` | 1536 float | vektör (HNSW, cosine) |

**Sorgu** (backend): hibrit = `search=fiş.search_text` + vektör (backend `embedding` ile sorgunun vektörünü çıkarır) + OData filtre, `top=20`.

```
filter: user_name eq 'elif' and log_level ne 'Information'
        and log_time ge 2026-10-17T08:45:00+03:00 and log_time le 2026-10-17T09:15:00+03:00
        and search.in(screen_id, 'ODMTTLMT') and institution_code eq 'GAZ02'
```

Filtre değerleri kodda **kaçışlanır** (tek tırnak ikilenir) ve yalnızca doğrulanmış fiş alanlarından gelir; kullanıcı metni filtreye girmez.

## 4. Çıktı (`LogMatch`)

| Alan | Açıklama |
|---|---|
| `mode` | `own` · `choose` · `related` · `none` |
| `signature` | `{screen_id, error_number, error_code, institution_code}` (own/related) |
| `log` | seçilen log: `log_time`, `customer_id`, `correlation_id`, `exception_message` (own) |
| `count` | own: kullanıcının o gün bu türdeki log sayısı (saat aralığından bağımsız; Elif = 8) · related: son 7 günde bu türdeki log sayısı (kesin sayılar 4. adımda) |
| `options` | en fazla 3 seçenek: `{signature, last_time, screen_name, exception_message, count}` (choose) |
| `widened` | saat aralığı kaldırıldıysa `true` |

`choose` gelirse arayüz seçenekleri düğme olarak gösterir; kullanıcı seçince aynı uç `selected_signature` ile tekrar çağrılır (AI çağrısı yok).

## 5. Kurallar

- AI bu adımda **çağrılmaz** (yalnızca sorgu vektörü için `embedding`).
- Sonuçlar kodda `log_time`'a göre azalan sıralanır; `DEMO_NOW`'dan sonraki loglar dikkate alınmaz.
- Müşteri no `customer_id` filtresine girer; ekranda müşteri no gösterilebilir (sentetik), ad gösterilmez.
- Search erişilemezse yedek: aynı filtreler bellekteki `kibana_logs.json` üzerinde uygulanır (anlamsal arama olmadan; 2. turda `search_text` kelimeleri `exception_message` içinde aranır).

## 6. Test seti (`DEMO_NOW = 2026-10-17 09:15`; testlerde sahte Search istemcisi bellekteki JSON'a filtre uygular)

| # | Kullanıcı · mesaj | Beklenen |
|---|---|---|
| 1 | elif · "Az önce Başkentgaz talimatında kurumdan yanıt alamadım" | own · 110731 GAZ02 · count 8 · log 08:57:46 |
| 2 | elif · "10007846 müşterisinin talimatı kaydedilmedi" | own · customer 10007846 · log 08:36:24 |
| 3 | elif · "İSKİ 13 haneli abone numarasını kabul etmiyor" | related · ODMTTLMT · 110412 · SU01 |
| 4 | s601u09 · "son iki günde hata aldım" (date_range_days 2) | choose · 3 seçenek (KRDTTAHS 120640, ODMTTLMT 110731 GAZ02, KRDTKULL 120101) |
| 5 | zeynep · "bugün sorun yaşadım" (fişte ekran/kurum yok) | none |
| 6 | elif · "saat 7 gibi Başkentgaz hatası" (07:00 civarında log yok) | own · `widened: true` · 110731 GAZ02 |
| 7 | Search erişilemez | yedek yol, test 1 ile aynı sonuç |

## 7. Dosyalar

| Dosya | İçerik |
|---|---|
| `scripts/index_kibana_logs.py` | indeksi kurar ve JSON'dan doldurur |
| `backend/app/clients/search.py` | AI Search istemcisi + `FakeSearchClient` (bellekte filtre) |
| `backend/app/clients/llm.py` | `embed(texts)` eklenir |
| `backend/app/repositories/logs.py` | filtre kurma (kaçışlama), hibrit sorgu, yedek yol |
| `backend/app/models/logs.py` | `LogMatch`, `Signature` |
| `backend/app/services/log_finder.py` | 1. tur / 2. tur, gruplama, mod kararı |
| `backend/tests/test_log_finder.py` | §6 |
