# Mercek — Sentetik Veri Üretim Rehberi

> Hangi verinin elle, betikle ya da uygulamayla üretildiği ve hazır betiklerin açıklaması: `mercek-sentetik-veri-kaynaklari.md`. V2 verisi (`data/seed/`) ve V3 betikleri (`tools/`) repoda hazırdır.

`mercek-sentetik-veri-plani.md` **hangi** verinin **neden** üretileceğini, bu doküman **nasıl ve hangi değerlerle** üretileceğini anlatır. Senaryolar: `mercek-demo-senaryo-onerileri.md`.

---

## 0. Genel kurallar

- **Tarih referansı:** Demo günü **17.10.2026**. Betikler `--today 2026-10-17` parametresi alır; "son 30/90 gün" bu tarihe göre hesaplanır. B senaryosunun "son 30 dakika" kayıtları ise `demo_reset.py` ile **demo saatine göre** yazılır.
- **Sabit tarihler:**
  - İSKİ duyurusu 12.09.2026, geçiş 01.10.2026
  - ASKİ duyurusu 05.10.2026, geçiş 01.01.2027
  - Afet tarihi 10.10.2026 (sentetik)
- **Tekrarlanabilirlik:** Tüm rastgele üretim `seed=42`. Senaryo kayıtları rastgele üretimin **üzerine** yazılır; betikler senaryoyla çelişen kayıt üretmez (§0.1 yasak kurallar).
- **Kişisel veri yok:** Gerçek TCKN, telefon, e-posta, IBAN yok. Faker (`tr_TR`) ad soyadları kurgusaldır. IBAN'lar simülasyon banka kodu `00999` ile üretilir (rebuild Faz 4). Telefon `+90 5xx 000 00 xx`, e-posta `@ornek.test`.
- **Copilot büyük veri üretmez;** yalnızca betikleri yazar. Doğal dil metinleri Foundry modeli üretir.

### 0.1 Yasak kurallar (demoyu bozmamak için)

| Kural | Neden |
|---|---|
| 01.10.2026 öncesine ait 13 haneli İSKİ abone numarası yok | C: "1 Ekim'den önce hiç yok" bulgusu |
| Çözüm bilgi bankasında abone numarası uzunluğu / formatı konulu kayıt yok | C: eşleşme %35 kalmalı |
| Taksit hatırlatma konulu geçmiş talep yalnızca D'nin 5 talebi | D: benzer talep listesi sabit kalmalı |
| Taksit erteleme konulu geçmiş talep yalnızca E'nin 3 talebi | E: benzer talep listesi sabit kalmalı |
| Ekran kataloğunda erteleme ekranı yok, `KRDTERTL` kodu boş | E: yeni ekran ve kod önerisi |
| Generator'ın ODMTFATR `VALIDATION_ERROR` kayıtlarında `error.field = subscriber_no` yok (enjeksiyon dışında) | C: 412 sayısı kesin kalmalı |
| Etkilenen 3 ilin adı arayüzde ve sunumda gösterilmez | E: hassasiyet |

---

## 1. Üretim matrisi ve çalışma sırası

| # | Adım | Komut / betik | Çıktı | Copilot prompt'u |
|---|---|---|---|---|
| 1 | Şema | `data/schema.sql` | Azure SQL tabloları | V1 |
| 2 | Katalog ve elle veriler | `data/seed/catalog.json`, `announcements.json` | JSON | V2 |
| 3 | Log üretimi | `python3 tools/generate_banking_logs.py --count 10000 --days 30 --seed 42 --end 2026-10-17T09:00:00+03:00` | `tools/output/dalan-banking-logs.ndjson` | rebuild Faz 5 |
| 4 | Log senaryo enjeksiyonu | `python3 tools/mercek_data/inject_log_scenarios.py --end 2026-10-17T09:00:00+03:00` | `tools/output/mercek-logs.ndjson` | V3 |
| 5 | Doğal dil metinleri | `python3 tools/mercek_data/generate_texts.py` | `data/seed/texts.json` (commit'lenir) | V4 |
| 6 | Portföy | `python3 tools/mercek_data/generate_portfolio.py` | `data/out/customers.csv`, `loans.csv` | V5 |
| 7 | Temaslar, çağrılar ve çözümler | `python3 tools/mercek_data/generate_incidents.py` | `data/out/contacts.csv`, `incidents.csv`, `solutions.csv` | V6 |
| 8 | Talepler | `python3 tools/mercek_data/generate_requests.py` | `data/out/requests.csv` | V6 |
| 8b | Değerlendirme seti | `python3 tools/mercek_data/generate_requests.py --eval` | `data/seed/eval_cases.json` (commit'lenir) | V6 |
| 9 | Yükleme | `python3 tools/mercek_data/load_all.py --all` (yerelde `--sqlite`) | SQL + AI Search | V7 |
| 10 | Demo sıfırlama | `python3 tools/mercek_data/demo_reset.py --sql [--now …]` | B'nin canlı penceresi | V8 |
| 11 | Doğrulama | `python3 tools/mercek_data/validate_scenarios.py --sql --search [--eval]` | Rapor (§12) | V8 |

Hedef: 1. gün **13:30'a kadar 1–9 bitmiş ve 11 yeşil** olmalı.

---

## 2. SQL şeması (`data/schema.sql`)

`data/schema.sql` elle yazılmaz: `tools/mercek_data/db.py` içindeki tablo tanımlarından üretilir (`load_all.py --write-schema`). Aynı tanımdan yerel testler için SQLite şeması da çıkar. Zaman alanları UTC olarak (`DATETIMEOFFSET(3)`) yazılır. Yabancı anahtar bilinçli olarak yok (toplu yükleme ve demo sıfırlama sırası serbest kalsın); ilişki bütünlüğünü `validate_scenarios.py` kontrol eder.

| Tablo | Alanlar | Not |
|---|---|---|
| `services` | service_id, name, description | 7 servis (§3.3) |
| `screens` | code, name, module, type (T/R), simulated (bit), description, components_json, flow_json, files_json | 5 simüle + 15 yalnızca katalogda (§3.2, §3.8) |
| `screen_services` | screen_code, service_id, role (`ana` / `etkilesimli`) | |
| `error_rules` | screen_code, error_code, error_type (`business` / `technical`), service_id, open_incident (bit), explanation_hint | Servis ataması kuralları (§3.4) |
| `service_calendar` | service_id, date_from, date_to, allocation_pct, note | §3.5 |
| `scope_addons` | addon_id, name, effort_md, main_share, customer_mgmt_share | §3.5.1 |
| `banking_logs` | log_id, ts, level, screen_code, event_action, outcome, error_code, error_type, error_field, customer_number, trace_id, channel, branch_code, employee_id, institution, subscriber_no, subscriber_no_len, amount, message, source (`seed` / `demo` / `live`), raw_json | Faz 5 ECS kayıtlarından düzleştirilmiş; indeks: (screen_code, ts), (trace_id), (customer_number, ts), (institution, ts), (error_code, error_field, ts), (source) |
| `customers` | customer_number, full_name, segment, age, monthly_income, city, district, region_affected (bit), address_changed_at, email, phone, perm_email, perm_sms, perm_phone, in_logs (bit) | |
| `loans` | loan_id, customer_number, product, principal, remaining_principal, monthly_rate, term, installment, paid_installments, next_due_date, status (`normal` / `gecikmede`), delinquent_12m (bit), collection_account | |
| `contacts` | contact_id, created_at, channel (`cagri_merkezi` / `sube`), customer_number, city, region_affected, category, subcategory, note, incident_id | Müşteri temasları (§6) |
| `incidents` | incident_id, created_at, channel (`sube` / `cagri_merkezi` / `dijital`), screen_code, category, subcategory, note, customer_number, subscriber_no, trace_id, city, service_id, master_incident_id, status, solution_id, resolution_minutes, error_code, institution, enriched_json | Bağlı vaka numarası: ana kayıt no + sıra (`CAG-2051-01`); sonraki ana kayıt numarası yalnızca ilk 4 haneden hesaplanır |
| `solutions` | solution_id, title, symptom, root_cause, steps, error_code, service_id | AI Search'e de yüklenir |
| `announcements` | ann_id, institution, published_at, effective_at, title, body | AI Search'e de yüklenir |
| `requests` | request_id, created_at, requester_unit, title, description, type, components_json, screens_json, services_json, effort_md, component_efforts_json, service_efforts_json, decisions, analysis_json, analyst, approved_by, scope_additions, status (`analiz` / `planli` / `tamamlandi`), planned_service_id, planned_from, planned_to | AI Search'e de yüklenir |
| `mercek_events` | event_id, ts, kind (`prevented_call` / `linked_case` / `analysis`), screen_code, incident_id, duration_ms, tokens, detail_json | Ölçümler (M1.6) |

---

## 3. Elle hazırlanan veriler (`data/seed/catalog.json`)

### 3.1 Demo kullanıcıları (fake auth, `users.ts`'e eklenir)

Rebuild Faz 3'teki kullanıcılar korunur; demo karakterleri eklenir. Şifre: `demo123`.

| id | username | Ad | Rol / unvan | Not |
|---|---|---|---|---|
| u-3 | mehmet | Mehmet Yılmaz | (mevcut) | Demoda **banka müşterisi**; müşteri no 10000003 |
| u-2 | ayse | Ayşe Kaya | Analist · Kıdemli İş Analisti | (mevcut) |
| u-4 | elif | Elif Demir | Şube Müşteri Temsilcisi | **Aylık gelir 38.000 TL**, çünkü simülasyonda KRDTKULL formu giriş yapan kullanıcının verisiyle dolar (A) |
| u-5 | zeynep | Zeynep Arslan | Çağrı Merkezi Temsilcisi | |
| u-6 | kerem | Kerem Aydın | Platform Yöneticisi · L2 Destek | |
| u-7 | fatma | Fatma Öztürk | Bölüm Başkanı · Kredi Tahsilatları | |
| u-8 | hakan | Hakan Çelik | Bölüm Başkanı · Bireysel Krediler | |

`Role` tipine "Şube Temsilcisi", "Çağrı Merkezi", "Bölüm Başkanı", "L2 Destek" eklenir.

### 3.2 Ekran kataloğu

| code | name | module | type | simulated | Ana bileşenler (components_json) |
|---|---|---|---|---|---|
| KRTTBASV | Kredi Kartı Başvurusu | KRT | T | 1 | kart seçimi, gelir, limit, kesim günü, onaylar |
| KRDTKULL | Bireysel Kredi Kullandırım | KRD | T | 1 | tutar, vade, ödeme planı (`loanPlan`), uygunluk uyarısı, sözleşme onayı, sonuç |
| ODMTFATR | Fatura Ödeme | ODM | T | 1 | tür/kurum, abone no (6–12 hane), sorgu, fatura listesi, hesap, öde |
| MUSTGUNC | Müşteri Bilgi Güncelleme | MUS | T | 1 | iletişim, adres, gelir, iletişim izinleri |
| HSPTVDSZ | Vadesiz Hesap Açılışı | HSP | T | 1 | müşteri özeti, döviz, şube, onaylar, IBAN |
| KRDRTKSR | Kredi Taksit Sorgulama | KRD | R | 0 | müşteri no ile kredi ve taksit listesi (vade, tutar, durum) |
| HSPRHRKT | Hesap Hareketleri Raporu | HSP | R | 0 | hesap, tarih aralığı, hareket listesi |
| KRTRKRTL | Kart Listesi | KRT | R | 0 | müşterinin kartları ve limitleri |

`components_json` ayrıca **kod dosya haritası** taşır (M1.4 kod analizi için), örnek ODMTFATR:

```json
{"frontend": ["frontend/src/app/(dashboard)/bankacilik/odmtfatr/page.tsx",
              "frontend/src/app/(dashboard)/bankacilik/odmtfatr/bill-payment-form.tsx"],
 "backend":  ["backend/app/api/odm.py"]}
```

### 3.3 Servisler ve ekran–servis ilişkisi

| service_id | Servis | Ana olduğu ekranlar | Etkileşimli olduğu ekranlar |
|---|---|---|---|
| KREDI_KULLANDIRIM | Kredi Kullandırım Servisi | KRDTKULL | — |
| KREDI_TAKIP | Kredi Takip Servisi | KRDRTKSR | — |
| MUSTERI_YONETIM | Müşteri Yönetim Servisi | MUSTGUNC | KRDTKULL, KRDRTKSR, HSPTVDSZ, KRTTBASV |
| FATURA_ODEME | Fatura Ödeme Servisi (kurum entegrasyonu dahil) | ODMTFATR | — |
| HESAP_YONETIM | Hesap Yönetim Servisi | HSPTVDSZ, HSPRHRKT | ODMTFATR |
| KART_BASVURU | Kart Başvuru Servisi | KRTTBASV, KRTRKRTL | — |

### 3.4 Hata–servis kuralları (`error_rules`)

| screen_code | error_code | error_type | service_id | open_incident | Açıklama ipucu |
|---|---|---|---|---|---|
| KRDTKULL | AFFORDABILITY_EXCEEDED | business | KREDI_KULLANDIRIM | 0 | Taksit gelirin %50'sini aşıyor; uygun tutar/vade önerilir |
| KRTTBASV | INSUFFICIENT_INCOME | business | KART_BASVURU | 0 | Kart tipinin gelir şartı |
| ODMTFATR | INSUFFICIENT_BALANCE | business | HESAP_YONETIM | 0 | Bakiye yetersiz |
| ODMTFATR | INSTITUTION_TIMEOUT | business | FATURA_ODEME | 1 | Kurum entegrasyonu zaman aşımı |
| ODMTFATR | VALIDATION_ERROR | business | FATURA_ODEME | 1 | Alan doğrulaması (`error_field`'a bakılır) |
| * | KYC_CHECK_FAILED | business | MUSTERI_YONETIM | 1 | Kimlik doğrulama |
| * | CORE_BANKING_TIMEOUT, SERVICE_UNAVAILABLE, DB_CONNECTION_ERROR | technical | ekranın ana servisi | 1 | Teknik hata |

`open_incident = 0` olan kurallar, A'daki "çağrı açılmadı" davranışının kaynağıdır.

### 3.5 Servis takvimi

| service_id | date_from | date_to | allocation_pct | note |
|---|---|---|---|---|
| KREDI_TAKIP | 2026-10-12 | 2026-11-08 | 100 | Yıl sonu regülasyon işi |
| KREDI_KULLANDIRIM | 2026-10-12 | 2026-10-30 | 50 | Kampanya parametreleri |
| FATURA_ODEME | 2026-10-19 | 2026-10-23 | 40 | Kurum entegrasyon bakımı |

Diğer servisler müsait. Resmî tatil takvimi sentetik veride yok; yalnızca hafta sonları atlanır.

**Takvim kuralı (kod):**
- Servis kapasitesi: **1 a/g / iş günü**, doluluk yüzdesi kadar düşülür.
- Süre (iş günü) = ⌈ana servis payı × 1,2⌉ (%20 entegrasyon ve test tamponu). Etkileşimli servislerin işi bu süre içinde paralel yürür.
- Başlangıç: ana servisin bugünden sonraki ilk boş iş günü.

| Talep | Ana servis payı | Süre | Başlangıç → bitiş |
|---|---|---|---|
| D (ilk) | Kredi Takip 15 | 18 | 09.11 → 02.12 |
| D (SMS eklenince) | Kredi Takip 16 | ⌈19,2⌉ = 20 | 09.11 → 04.12 |
| E · öncelik ver (ilk) | Kredi Takip 8 | ⌈9,6⌉ = 10 | 19.10 → 30.10 |
| E · öncelik ver (SMS eklenince) | Kredi Takip 9 | ⌈10,8⌉ = 11 | 19.10 → 02.11 |
| E · sıraya koy | Kredi Takip 8 | 10 | 09.11 → 20.11 |

Çatışma yan etkileri: "Öncelik ver" seçilirse regülasyon işi 10 iş günü kayar (bitiş 08.11 → 22.11) ve D 23.11'de başlar (bitiş 18.12). "Sıraya koy" seçilirse regülasyon işi etkilenmez, D yine E'den sonra 23.11'de başlar (bitiş 18.12).

### 3.5.1 Kapsam ekleri (`scope_addons`)

Köprü önerilerinin eforu geçmiş taleplerdeki "kanal ekleme" işlerinin medyanıdır ve katalogda sabittir:

| addon_id | Ad | Efor | Servis payları |
|---|---|---|---|
| ADD-SMS | Mevcut bildirime SMS kanalı ekleme | 2 a/g | ana servis 1, Müşteri Yönetim 1 |
| ADD-PROAKTIF-SMS | Hedef gruba tek seferlik proaktif SMS | 2 a/g | ana servis 1, Müşteri Yönetim 1 |

### 3.6 Kurum duyuruları (`data/seed/announcements.json`)

| ann_id | Kurum | Yayın | Geçerlilik | Başlık |
|---|---|---|---|---|
| DUY-0412 | İSKİ | 12.09.2026 | 01.10.2026 | Yeni abonelere 13 haneli abone numarası verilecektir |
| DUY-0419 | ASKİ | 05.10.2026 | 01.01.2027 | Abone numaraları 13 haneye geçiyor |
| DUY-0398 | Başkentgaz | 20.08.2026 | 01.09.2026 | Fatura sorgu servisinde bakım penceresi (gece 02:00–04:00) |
| DUY-0401 | Enerjisa Başkent | 28.08.2026 | 15.09.2026 | Yeni fatura dönem kodu alanı |
| DUY-0405 | İGDAŞ | 02.09.2026 | 02.09.2026 | Ödeme bildirim formatında değişiklik yok, bilgilendirme |
| DUY-0408 | Turkcell | 07.09.2026 | 01.10.2026 | Kurumsal hatlar için ayrı fatura türü |
| DUY-0415 | İZSU | 18.09.2026 | 01.11.2026 | Ödeme kanallarında saat sınırlaması kalkıyor |
| DUY-0417 | Türk Telekom | 26.09.2026 | 26.09.2026 | Sertifika yenilemesi |

Metin (`body`) 3–5 cümle, kurumsal duyuru dili; elle yazılır. İSKİ ve ASKİ metinlerinde "13 hane", "yeni aboneler", "mevcut numaralar değişmez" ifadeleri bulunur.

### 3.7 Etkilenen bölge (E)

- `config.affected_region`: rebuild Faz 5'teki 12 ilden İstanbul dışındaki **3 il** (`region_affected = 1`).
- Arayüzde ve sunumda il adları gösterilmez; Mercek "etkilenen 3 il" der.

### 3.8 Ek katalog verileri (gerçekçilik için)

Katalogun tamamı `data/seed/catalog.json` ve `announcements.json` dosyalarındadır; yukarıdaki tablolar senaryoların dayandığı satırlardır. Gerçekçilik için şunlar da eklidir:

| Veri | Adet | İçerik |
|---|---|---|
| Ek ekranlar (yalnızca katalogda) | 12 | KRTTSIFR Kart Şifre Belirleme · KRTREKST Kart Ekstre · KRDRBASV Kredi Başvuru Durumu · KRDRODPL Ödeme Planı Görüntüleme · ODMRGCMS Fatura Ödeme Geçmişi · ODMTVRGI Vergi ve Harç Ödeme · MUSRBLGI Müşteri Bilgi Sorgulama · MUSTKYCD Kimlik Doğrulama · MUSRILTS İletişim İzinleri Raporu · HSPTVDLI Vadeli Hesap · HSPTHVLE Havale ve EFT · HSPRBKYE Bakiye Sorgulama |
| Ek servis | 1 | ODEME_SISTEMLERI (havale, EFT) |
| Ekran–servis ilişkisi | 30 | Ek ekranlar dahil |
| Hata–servis kuralı | 17 | Ek ekranların doğrulama, bakiye ve kurum kuralları (çoğu `open_incident = 0`) |
| Servis takvimi | 11 satır | Tüm servisler için Ekim–Aralık dolu dönemleri. Kredi Takip 9 Kasım–20 Aralık arası boştur (D ve E bu boşluğa göre planlanır). |
| Kapsam ekleri | 5 | SMS, proaktif SMS, gönderim raporu, rol bazlı yetki, kuralı parametreye taşıma |
| Kurumlar | 15 | Fatura türü, kurum kodu, zaman aşımı süresi |
| Şubeler | 5 | 0101 Kadıköy, 0102 Levent, 0601 Kızılay, 3501 Alsancak, 9999 Dijital Şube |
| Çağrı kategorileri | 6 kategori, 32 alt kategori (2'si yalnızca teknoloji çağrılarında: yetersiz bakiye, başvuru tamamlanamadı) | Çağrı üretimi (V6) ve zenginleştirme bu listeyi kullanır |
| Kurum duyuruları | 20 | 8 duyuruya 12 ilgisiz duyuru eklendi |

**Bu eklerde korunan yasak kurallar:**
- Mevcut bir kredinin ödeme planını değiştiren ya da erteleme başvurusu alan ekran yok. KRDRODPL yalnızca görüntüler; E'de taslak bu ekranı yeniden kullanım kaynağı olarak gösterebilir.
- Bildirim gönderen ayrı bir servis yok; D'de gönderim Kredi Takip ve Müşteri Yönetim üzerinden kalır.
- Kurum listesinde abone numarası uzunluğu alanı yok; C'nin kalıcı önerisi zaten bu alanın eklenmesi.
- İSKİ ve ASKİ dışında hiçbir duyuru abone numarası veya hane sayısından söz etmez. İSKİ'nin ikinci duyurusu (DUY-0406, kesinti duyuruları) aramada DUY-0412'nin altında kalmalıdır; M1.4 kalibrasyonunda kontrol edilir.

---

## 4. İşlem logları

### 4.1 Üretim (rebuild Faz 5, değiştirmeden)

```bash
python3 tools/generate_banking_logs.py --count 10000 --days 30 --seed 42 --end 2026-10-17T09:00:00+03:00
```

Ekran ağırlıkları: ODMTFATR 35, HSPTVDSZ 18, KRTTBASV 16, KRDTKULL 16, MUSTGUNC 15. Seviye dağılımı: info %89, warn %9, error %2. İş reddi ve teknik hata kodları üreticideki gibidir.

### 4.2 Senaryo enjeksiyonu (`inject_log_scenarios.py`)

Girdi Faz 5 çıktısıdır, çıktı `mercek-logs.ndjson`. Kurallar:

1. **Normalizasyon:** Üreticinin ODMTFATR `VALIDATION_ERROR` kayıtlarına `error.field = "amount"` atanır (yasak kural). Her ODMTFATR kaydına `banking.bill.subscriber_no` yoksa kurum türüne uygun 10–12 haneli numara eklenir.
2. **C · İSKİ (412 kayıt):**
   - 01.10.2026 00:00 – 17.10.2026 09:00 arasında, gündüz ağırlıklı dağılımla.
   - **400 kayıt:** `banking.bill.institution = "İSKİ"`, 13 haneli `subscriber_no`, `error.code = VALIDATION_ERROR`, `error.field = subscriber_no`, `log.level = warn`, mesaj `"ODMTFATR Abone numarası 6–12 haneli olmalıdır"`. **187 farklı müşteri** (bir müşteri 1–5 deneme). Kanal: İnternet Şube %55, Mobil %35, Şube %10.
   - **12 kayıt:** Diğer kurumlar, abone no 4–5 hane veya harf içeren (gerçek kullanıcı hatası).
   - 01.10 öncesinde İSKİ'ye ait 13 haneli kayıt **olmaz.**
3. **B · Başkentgaz tarihçesi:** Geçmiş 30 güne dağılmış üretici kayıtları baz seviye olarak kalır (günde 1–2 `INSTITUTION_TIMEOUT`). Demo penceresi (46 kayıt) burada değil, `demo_reset.py`'de yazılır.
4. **Mehmet (u-3, 10000003):** Son 30 günde 3 başarılı ODMTFATR ödemesi (Başkentgaz, abone 4012345678).
5. Çıktı `banking_logs` tablosuna §2'deki sütunlara düzleştirilerek yüklenir (`raw_json` tam kayıt).

### 4.3 Canlı olay logları (uygulama yazar)

Demo sırasında uygulama aşağıdaki olayları `POST /api/logs` ile aynı ECS alanlarıyla yazar:

| Senaryo | Olay | Alanlar |
|---|---|---|
| A | KRDTKULL uygunluk uyarısı gösterildi | `error.code = AFFORDABILITY_EXCEEDED`, `warn`, `banking.loan` (tutar, vade, taksit, gelir, oran), `trace.id`, `employee.id = u-4` |
| B | ODMTFATR Başkentgaz sorgusu (demo modu) | `INSTITUTION_TIMEOUT`, `warn`, kurum, abone no, müşteri no 10000003, kanal İnternet Şube |
| C | ODMTFATR İSKİ 13 haneli sorgu | `VALIDATION_ERROR`, `error.field = subscriber_no` |

---

## 5. Müşteri ve kredi portföyü (`generate_portfolio.py`)

> Betik hazır: `tools/mercek_data/generate_portfolio.py`. Etkilenen iller: Bursa, Antalya, Adana (yalnızca katalogda; arayüzde gösterilmez). Ayrıntı: `mercek-sentetik-veri-kaynaklari.md` §2.4.

**Hacim:** 40.000 müşteri (`10000101` – `10040100`), bunların 26.000'i aktif bireysel ihtiyaç kredili, toplam 33.000 kredi.

**Dağılımlar:** Segment ve il ağırlıkları Faz 5 üreticisiyle aynı. Kredi tutarı 10.000–500.000 (log-normal), vade 3–36 ay, oranlar KRDTKULL ile aynı.

**D için kesin değerler (hedef grup):**
- Aktif kredili **ve** son 12 ayda en az 1 taksiti ≥ 1 gün gecikmiş müşteri: **2.340**.
- İzin dağılımı (hedef grup içinde):

| e-posta | SMS | Müşteri |
|---|---|---|
| ✓ | ✓ | 1.169 |
| ✓ | ✗ | 188 |
| ✗ | ✓ | 726 |
| ✗ | ✗ | 257 |

→ E-posta %58 (1.357), SMS %81 (1.895), en az biri %89 (2.083).

**E için kesin değerler (etkilenen bölge):**
- 3 ilde adresi kayıtlı, aktif kredili müşteri: **4.870**; kredileri **6.215**; bunların **612'si** `gecikmede`.
- Bu müşterilerden **37'sinin** `address_changed_at` değeri 10.10.2026'dan sonra (afet sonrası adres değişikliği).
- Etkilenen bölgedeki müşterilerle D'nin hedef grubu kesişebilir; bu sayıları bozmaz.

**Elif ve Mehmet:** Portföyde değil, kullanıcı kaydından gelir (simülasyon). Mehmet'in Başkentgaz aboneliği log ve çağrılarda geçer.

---

## 6. Müşteri temasları ve teknoloji çağrı kayıtları (`generate_incidents.py`)

> Betik hazır: `tools/mercek_data/generate_incidents.py`. Ayrıntı: `mercek-sentetik-veri-kaynaklari.md` §2.5.

İki ayrı kayıt türü vardır:

| Kayıt | Tablo | Ne | Hacim |
|---|---|---|---|
| **Müşteri teması** | `contacts` | Müşterinin çağrı merkezini araması veya şubeye gelmesi; temsilci not düşer. Çoğu o an çözülür, teknolojiye kayıt açılmaz. | ~8.300 (son 90 gün), `TMS-000001`… |
| **Teknoloji çağrı kaydı** | `incidents` | Teknolojiye açılan destek kaydı; servise atanır, L2 bakar. | 1.400 (son 90 gün), **CAG-0651 … CAG-2050** (daha eskileri arşivde) |

D ve E'nin köprü sayıları **temaslardan**, B ve C'nin kayıtları **çağrılardan** gelir.

**Temas dağılımı:** Bölge dışından günde ~69, etkilenen 3 ilden günde ~16 temas. Kategori: Fatura ödeme %24, Kredi %22, Kart %16, Hesap %14, Müşteri bilgileri %12, Diğer %12. Kanal: çağrı merkezi %75, şube %25. Müşteri ve il portföyden (V5).

**Çağrı dağılımı:** Ekran ve hata koduna göre (iş kuralı retleri için de geçmişte çağrı açılmıştır; Mercek'in önlediği durum budur). Servis hata–servis kuralından atanır. Son 3 gündeki çağrıların bir kısmı açık, gerisi kapalı; kapalıların %60'ında ilgili hata kodunun çözümü bağlıdır.

**Senaryo kayıtları (kesin):**

| Senaryo | Tablo | Kayıtlar |
|---|---|---|
| **B** · geçmiş | incidents | 6 kapalı kurum zaman aşımı çağrısı (Başkentgaz 2, İGDAŞ 2, Enerjisa Başkent 1, CK Boğaziçi 1), `solution_id = SOL-031`, çözüm süresi 45–120 dk. Arka planda açık Başkentgaz çağrısı yoktur |
| **B** · demo | incidents | CAG-2051 ana kayıt ve bağlı 11 vaka: **`demo_reset.py` yazar** (§11) |
| **C** | incidents | 01.10 sonrası 23 açık çağrı: İSKİ, "abone numarası kabul edilmiyor", çözüm yok. Müşteri, abone no ve `trace_id` V3 loglarındaki İSKİ denemelerinden alınır |
| **D** | contacts | Son 90 günde Kredi kategorisinde: **"hatırlatma almadım / tarihi unuttum" 71**, "gecikme faizi itirazı" 64, "taksit tutarı / tarih sorusu" 51 → toplam **186**. Bu üç alt kategoride arka plan kaydı yoktur |
| **E** | contacts | 12.10 sonrası etkilenen 3 ilden **497** temas, **418'i** "erteleme / ödeme güçlüğü" (arayanlar bölgedeki kredili müşteriler). 12.09–11.10 arasında aynı illerden tam **480** temas (günde **16**) → ≈ 6 kat artış. Bölgede erteleme konulu temas yalnızca senaryodan gelir |

`note` alanı temsilcinin yazdığı kısa nottur (V4, `texts.json`).

---

## 7. Çözüm bilgi bankası

- ~40 kayıt (`SOL-001`…). Hata kodu başına 2–5 çözüm, metinler Foundry'den (§9.2).
- **SOL-031 (elle):**
  - **Başlık:** Kurum entegrasyonu zaman aşımı
  - **Belirti:** Fatura sorgu/ödeme `INSTITUTION_TIMEOUT`; aynı kurumda kısa sürede çok sayıda hata
  - **Kök neden:** Kurum tarafı yavaşlığı / bakım
  - **Adımlar:**
    1. Kurum bazında son 30 dk hata sayısını kontrol et.
    2. Kurumun bakım duyurusunu kontrol et.
    3. Zaman aşımı eşiğini geçici artır ve istekleri kuyruğa al.
    4. Kurum entegrasyon sorumlusuyla iletişime geç.
    5. Müşteriye mükerrer ödeme yapmamasını söyle.
- Yasak kural: abone numarası uzunluğu/formatı konulu çözüm yok.

---

## 8. Geçmiş talepler (`generate_requests.py`)

> Betik hazır: `tools/mercek_data/generate_requests.py`. 87 üretilmiş + 8 kesin = 95 talep, TLP-0500…TLP-1037, 2020-06…2026-10. Uygulamadaki TLP-1038…1042 uygulamanın kendi örnek verisidir.

**Hacim:** ~100 talep (`TLP-0500` – `TLP-1042`), son 24 ay. Tip dağılımı: mevcut ekran değişikliği %55, yeni ekran %20, batch işi %15, karma %10. Efor 3–40 a/g (log-normal, medyan ~12). `services_json` ana ve etkileşimli servisleri içerir. Uygulamadaki mevcut `TLP-1038…1042` kayıtları korunur.

**D'nin benzer talepleri (kesin):**

| request_id | Başlık | Tip | Bileşen | Efor | Servis payları (`service_efforts_json`) | Kararlar (`decisions`) |
|---|---|---|---|---|---|---|
| TLP-0871 | Kredi kartı son ödeme tarihi SMS hatırlatması (segment bazlı, otomatik) | batch | otomatik | 14 | Kart Başvuru 12, Müşteri Yönetim 2 | Son ödeme tarihinden 3 gün önce; günde bir çalışır; aynı ekstre için tek gönderim |
| TLP-0915 | Fatura son ödeme tarihi hatırlatma e-postası | batch | otomatik | 11 | Fatura Ödeme 9, Müşteri Yönetim 2 | E-postada tutar yer almaz |
| TLP-0962 | Vadeli hesap vade sonu bildirim işi | batch | otomatik | 9 | Hesap Yönetim 8, Müşteri Yönetim 1 | Yalnızca iletişim izni olan müşteriler |
| TLP-1004 | Kart ekstresini ekrandan müşteriye manuel gönderme | mevcut ekran değişikliği | manuel | 6 | Kart Başvuru 5, Müşteri Yönetim 1 | Şube ve çağrı merkezi temsilcileri gönderebilir; son gönderim satırda görünür |
| TLP-1019 | Hesap hareket dökümünü şube ekranından e-posta ile iletme | mevcut ekran değişikliği | manuel | 8 | Hesap Yönetim 6, Müşteri Yönetim 2 | İzin yoksa buton pasif |

Kontrol (kod): otomatik medyan 11 (9–14), manuel medyan 7 (6–8), toplam 18. Müşteri Yönetim payı oranlarının medyanı 0,167 → 18 × 0,167 = **3**, Kredi Takip = 18 − 3 = **15**.

**E'nin benzer talepleri (kesin):**

| request_id | Başlık | Tip | Efor | Servisler |
|---|---|---|---|---|
| TLP-0588 | Salgın döneminde kredi taksit erteleme ekranı | yeni ekran | 15 | Kredi Takip 8, Kredi Kullandırım 3, Müşteri Yönetim 4 |
| TLP-0712 | Kredi kartı borcu taksitlendirme ekranı | yeni ekran | 13 | Kart Başvuru 9, Müşteri Yönetim 4 |
| TLP-0846 | Kredi vade değişikliği (iç operasyon ekranı) | yeni ekran | 17 | Kredi Takip 13, Kredi Kullandırım 4 |

Kontrol (kod): medyan 15 (13–17). Müşteri Yönetim oran medyanı (0,267; 0,308) = 0,287 → **4**; Kredi Kullandırım (0,200; 0,235) = 0,218 → **3**; Kredi Takip = 15 − 4 − 3 = **8**.

**Planlı talep (E'nin çatışma analizi için):** E demosu D'den sonra oynatılacaksa, D'nin canlıda oluşan talebi (TLP-1043) Kredi Takip takviminde 09.11–04.12 planlı olarak durur. E ayrı oynatılacaksa `demo_reset.py --with-d-plan` bu kaydı ekler.

**Benzerlik değerleri** (%90, %84…) AI Search skorlarından gelir. Demo öncesi bir kez kalibre edilir: D ve E'nin talep metinleriyle arama yapılır, sıralama ve yüzdeler senaryo dokümanıyla karşılaştırılır.

---

### 8.1 Değerlendirme seti (`data/seed/eval_cases.json`)

Mercek model eğitmez (hazır model + arama + kurallar), bu yüzden klasik eğitim/test ayrımı yoktur. Ama eşik ve arama kalitesi demo cümlelerine ezberlenmesin diye **ayrı bir değerlendirme seti** tutulur.

| Grup | Adet | Girdi | Beklenen |
|---|---|---|---|
| `match` · eşleşmesi gereken çağrılar | 10 | Bilinen sorunları anlatan temsilci cümleleri (kurum zaman aşımı, bakiye yetersiz, KYC, ana bankacılık zaman aşımı…) | Doğru `solution_id` ilk sırada, skor ≥ eşik |
| `no_match` · eşleşmemesi gereken çağrılar | 10 | Bilgi bankasında karşılığı olmayan yeni sorunlar (yeni alan formatı, yeni kurum davranışı, ekran görüntüleme sorunu…) | En yüksek skor < eşik |
| `request` · talepler | 10 | İş birimi ağzından yeni talepler (mevcut ekran değişikliği, batch, yeni ekran karışık) | Doğru tip, doğru ekran(lar), doğru ana servis; efor benzer taleplerin aralığında |

**Kurallar:**
- Vakalar AI Search'e ve SQL'e **yüklenmez**; yalnızca sorgu olarak kullanılır.
- Metinler, indekse yüklenen çözüm ve talep metinlerinden **farklı ifadelerle** yazılır (aynı cümle yeniden kullanılmaz).
- Demo senaryolarının (A–F) metinleri ve Copilot prompt'larındaki örnekler bu sette yer almaz.
- Yasak kurallar burada da geçerlidir: abone numarası uzunluğu, taksit hatırlatma ve taksit erteleme konulu vaka yoktur.
- Üretim: V6 betikleri `--eval` ile 30 vakayı üretir. Metinler Foundry ile taslak, son hali elle gözden geçirilir. Beklenen değerler (`expected_solution_id`, `expected_type`, `expected_screens`, `expected_main_service`) elle doldurulur.

**Kullanım:**
1. **Eşik kalibrasyonu** (M1.4-a): Eşik `match` ve `no_match` gruplarına göre seçilir. Demo senaryoları yalnızca son kontrol olarak çalıştırılır.
2. **Doğrulama** (V8): `validate_scenarios.py --eval` doğruluk özetini yazar.
3. **Jüri:** Sunumda ve soru-cevapta "30 vakada …" rakamı kullanılır.

**Hedef:** `match` en az 8/10 doğru ve eşik üstü, `no_match` en fazla 1/10 yanlış eşleşme, `request` en az 8/10 doğru tip ve ana servis.

## 9. Foundry ile doğal dil metinleri (`generate_texts.py`)

> Betik ve prompt dosyaları hazır: `tools/mercek_data/generate_texts.py`, `prompts/gen-*.md`; elle yazılan kesin metinler `data/seed/fixed_texts.json`. Ayrıntı: `mercek-sentetik-veri-kaynaklari.md` §2.3. Aşağıdaki prompt metinleri dosyalardakinin özetidir.

**Ayarlar:**
- Foundry'deki `chat` deploy'u, temperature 0.8, JSON şemalı çıktı, 20'şerli partiler.
- Sonuç `data/seed/texts.json`'a yazılır ve commit'lenir; tekrar üretilmez.
- Üretim sonrası otomatik kontrol: yasak kelimeler, 10+ haneli rakam dizisi, `@` (e-posta deseni hariç), `+90` ve tekrarlar ayıklanır. Atılan metin %20'yi geçerse parti yeniden üretilir.

### 9.1 Prompt `gen-cagri-notu` (temsilci çağrı notları)

```
## system
Bir bankanın şube ve çağrı merkezi temsilcilerinin çağrı kayıtlarına yazdığı kısa notlar için
sentetik test verisi üretiyorsun. Notlar gerçek kişi, kurum çalışanı, telefon, TCKN, IBAN, kart
numarası veya adres İÇERMEZ.
- 10–35 kelime, temsilci dili ("Müşteri ... belirtti", "Müşteri ... soruyor"), üçüncü şahıs.
- Teknik hata kodu yazma; müşterinin anlattığını ve temsilcinin gözlemini yaz.
- Aynı partide tekrar yok; farklı durum ve tonlar kullan.

## user
Kategori: {{category}} · Alt kategori: {{subcategory}}
Ekran (temsilci bilmeyebilir): {{screen_name}} · Kurum (varsa): {{institution}}
Adet: {{count}}
Yasak konular: {{forbidden_topics}}
Çıktı şeması: {"items": [{"note": string}]}
```

Çağırma planı: Her (kategori, alt kategori) için 10–20 not; D'nin üç alt kategorisi ve E'nin "erteleme" alt kategorisi için 30'ar not. C'nin "abone numarası kabul edilmiyor" notları elle yazılan 5 örnekten çoğaltılır.

### 9.2 Prompt `gen-cozum`

```
## system
Bankacılık uygulaması için sentetik çözüm bilgi bankası kaydı üretiyorsun. Kayıtlar L2 destek
ve geliştirme ekipleri içindir: kısa, teknik, uygulanabilir. Sunucu adı, IP, şifre uydurma.
Abone numarası uzunluğu veya formatıyla ilgili kayıt ÜRETME.

## user
Hata kodu: {{error_code}} · Servis: {{service_name}} · Ekran: {{screen_code}}
Farklı kök nedenlere dayanan {{count}} kayıt üret.
Çıktı şeması: {"items": [{"title": string, "symptom": string, "root_cause": string,
                          "steps": [string]}]}
```

### 9.3 Prompt `gen-talep`

```
## system
Bir bankanın iş birimlerinden (bölüm başkanlıkları) teknolojiye gelen sentetik geliştirme
talepleri üretiyorsun. Talepler iş biriminin ağzından, 1–3 cümle, net bir ihtiyaç tarif eder.
Gerçek kişi veya kurum adı kullanma. Şu konularda talep ÜRETME: taksit hatırlatma,
ödeme hatırlatma, taksit erteleme, kredi erteleme.

## user
Modül: {{module}} · İlgili ekran: {{screen_name}} (yoksa "yeni ekran") · Tip: {{type}}
Adet: {{count}}
Çıktı şeması: {"items": [{"title": string (≤ 12 kelime), "description": string}]}
```

---

## 10. Yükleme (`load_all.py`) ✅

Komutlar: `--sqlite` (yerel `data/out/mercek.db`), `--sql` (Azure SQL), `--search` (AI Search), `--all`, `--write-schema`. Tüm SQL yüklemesi tek transaction; hata olursa geri alınır. Loglar `source = 'seed'` ile yazılır.

**Azure SQL:**
1. `schema.sql` uygulanır.
2. `catalog.json` ve `announcements.json` yüklenir.
3. `mercek-logs.ndjson` → `banking_logs` (toplu ekleme, parametreli).
4. CSV'ler: customers, loans, incidents, solutions, requests.

**Azure AI Search indeksleri (SQL'den otomatik eşitlenir; ayrıntı `mercek-sql-search-esitleme.md`):**

| İndeks | Alanlar | Vektör alanı |
|---|---|---|
| `solutions` | id, title, symptom, root_cause, steps, error_code (filtre), service_id (filtre) | `content_vector` |
| `requests` | id, title, description, type (filtre), components, services, effort_md, status (filtre) | `content_vector` |
| `announcements` | id, institution (filtre), published_at, effective_at, title, body | `content_vector` |

Varsayılan olarak AI Search indexer'ı SQL'deki `search_text` kolonunu okur ve embedding'i skillset içinde Foundry'deki `embedding` deploy'una ürettirir (yedek `--search-mode push`: betik 50'şerli partilerle üretir). Türkçe analizör kullanılır (`tr.microsoft`). Vektör metriği cosine (HNSW). Doğrulamada skor, vektör sorgusunun `@search.score` değerinden 0–1 benzerliğe çevrilir (`cos = 2 − 1/score`); eşik (`MATCH_THRESHOLD = 0,75`) bu değerle karşılaştırılır.

---

## 11. Demo sıfırlama (`demo_reset.py`) ✅

Her prova ve gerçek demodan **hemen önce** çalıştırılır:

1. Önceki provalarda canlı oluşan kayıtları siler: `CAG-2051` ve sonrası (yeniden yazılır), `TLP-1043` ve sonrası, seed dışı loglar (`source <> 'seed'`: önceki demo penceresi ve uygulamanın yazdığı canlı loglar). Seed verisine dokunulmaz.
2. **B penceresi:**
   - `now − 30 dk` ile `now − 1 dk` arasına **46** Başkentgaz `INSTITUTION_TIMEOUT` logu yazar. Kanallar: İnternet Şube, Mobil, Şube; farklı müşteriler.
   - **CAG-2051** ana kaydı: `now − 24 dk`, kategori Fatura ödeme, kurum Başkentgaz, `service_id = FATURA_ODEME`.
   - Ana kayda bağlı **11 vaka** `CAG-2051-01` … `-11` (`master_incident_id = CAG-2051`), `now − 22 dk` … `now − 2 dk`; müşteri, abone no ve `trace_id` pencere loglarından. Mehmet'in vakası `CAG-2051-12` olur, C'nin yeni ana kaydı `CAG-2052`.
3. `--with-d-plan` verilirse D'nin talebini (TLP-1043, 20 a/g, Kredi Takip 09.11–04.12) planlı olarak ekler (E'yi tek başına oynatmak için).
4. `mercek_events` sayaçlarını sıfırlar.

Hepsi tek transaction. Pencere seed 7 ile üretilir; her çalıştırmada aynı müşteriler, yalnızca saatler `--now`'a göre kayar. Komut: `python3 tools/mercek_data/demo_reset.py --sql [--now 2026-10-17T13:20:00+03:00] [--with-d-plan]`.

---

## 12. Doğrulama (`validate_scenarios.py`) ✅

Komut: `python3 tools/mercek_data/validate_scenarios.py --sql --search [--now …] [--only B,C] [--eval]`. `--now`, `demo_reset` ile aynı an olmalı. Search satırları `--search` verilmezse atlanır (–). Takvim satırları §3.5 kuralının başvuru uygulamasıyla (`plan()`) hesaplanır; backend takvim servisi aynı sonucu vermelidir. Yerel SQLite ile ölçülen sonuç: 17 ✓ · 0 ✗ · 5 atlandı (Search).

| Senaryo | Kontrol | Beklenen |
|---|---|---|
| Genel | Kayıt sayıları | logs ≈ 10.400, customers 40.000, loans 33.000, contacts ≈ 8.300, incidents 1.400 (CAG-0651…2050), solutions 37, requests 95, announcements 20 |
| Genel | Bütünlük: sahipsiz kredi, ana kayıt, temas çağrısı, çözüm | 0 / 0 / 0 / 0 |
| A | `users` içinde elif geliri | 38.000 |
| A | `loanPlan` Python portu ile 400.000/3 ay ve 36 ay taksit; 36 ayda azami tutar | 144.185,92 · 22.754,17 · ≈ 334.004 |
| B | Son 30 dk Başkentgaz `INSTITUTION_TIMEOUT` (`demo_reset` sonrası) | 46 |
| B | CAG-2051'e bağlı vaka | 11 |
| B | AI Search `solutions`'ta "Başkentgaz fatura ödeme kurumdan yanıt alınamadı" | İlk sonuç SOL-031, skor ≥ eşik |
| C | 01.10 sonrası `error_field = subscriber_no` ve ODMTFATR | 412; İSKİ 400 (%97); İSKİ'de `subscriber_no_len = 13` hepsi; farklı müşteri 187 |
| C | 01.10 öncesi İSKİ 13 hane | 0 |
| C | C çağrıları | 23 |
| C | `solutions`'ta "İSKİ abone numarası 13 hane kabul edilmiyor" | En yüksek skor eşiğin altında (≈ %35) |
| C | `announcements`'ta aynı sorgu | İlk sonuç DUY-0412; ASKİ DUY-0419 da döner |
| D | Son 90 gün Kredi temasları (`contacts`), üç alt kategori | 71 / 64 / 51 = 186 |
| D | Hedef grup ve izinler | 2.340 · e-posta 1.357 · SMS 1.895 · en az biri 2.083 |
| D | `requests` araması (D talep metni) | İlk 5: TLP-0871, 0915, 0962, 1004, 1019 |
| D | Servis payları ve takvim (§3.5) | Kredi Takip 15 / Müşteri Yönetim 3; 09.11 → 02.12; SMS ile 16 / 4, 04.12 |
| E | Etkilenen bölge | 4.870 müşteri · 6.215 kredi · 612 gecikmede · 37 adres değişikliği |
| E | Bölge temasları (`contacts`): 12.10 sonrası / 12.09–11.10 günlük ort. | 497 (418 erteleme) / 16 |
| E | `requests` araması (E talep metni) | İlk 3: TLP-0588, 0712, 0846 |
| E | Servis payları ve takvim (§3.5) | Kredi Takip 8 / Kredi Kullandırım 3 / Müşteri Yönetim 4; öncelik 19.10 → 30.10 (SMS ile 02.11); sıraya koy 09.11 → 20.11 |
| E | Katalogda `KRDTERTL` | yok |
| F | Bugün en çok warn/error alan ekran | ODMTFATR |
| Değerlendirme (`--eval`) | §8.1 setinde doğruluk | match ≥ 8/10 · yanlış eşleşme ≤ 1/10 · talep ≥ 8/10 |
