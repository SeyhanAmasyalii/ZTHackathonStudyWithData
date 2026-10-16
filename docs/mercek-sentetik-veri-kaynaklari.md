# Mercek — Sentetik Veri Kaynakları: Elle, Betikle, Uygulamayla

Bu doküman, Mercek'in kullandığı her sentetik verinin **nereden geldiğini** üç gruba ayırır: elle yazılanlar, betikle üretilenler ve uygulamanın çalışırken ürettikleri. Her betik ve uygulama parçası için ne yaptığı, girdisi, çıktısı ve çalıştırma komutu yazılıdır.

Değerlerin ayrıntısı: `mercek-sentetik-veri-uretimi.md`. Neden bu veri: `mercek-sentetik-veri-plani.md`. Adetler: `mercek-sentetik-veri-sayilari.md`.

**Durum işaretleri:** ✅ hazır (repoda) · 🔧 hackathonda Copilot ile yazılacak

---

## Özet

| # | Veri | Kaynak | Dosya / betik | Durum | Adım |
|---|---|---|---|---|---|
| 1 | Katalog: ekranlar, servisler, kurallar, takvim, kapsam ekleri, kurumlar, şubeler, çağrı kategorileri | Elle | `data/seed/catalog.json` | ✅ | V2 |
| 2 | Kurum duyuruları (20) | Elle | `data/seed/announcements.json` | ✅ | V2 |
| 3 | Demo kullanıcıları | Elle | `catalog.json` → `users.ts` | ✅ (veri) · 🔧 (`users.ts`) | V2, A6 |
| 4 | Kesin senaryo metinleri (SOL-031, D'nin 5 ve E'nin 3 benzer talebi, C'nin 5 çağrı notu) | Elle | `data/seed/fixed_texts.json` | ✅ | V4, V6 |
| 5 | Değerlendirme seti (30 vaka) | Betik + elle gözden geçirme | `data/seed/eval_cases.json` | ✅ üretildi · gözden geçirme 🔧 | V6 |
| 6 | İşlem logları (~10.000) | Betik | `tools/generate_banking_logs.py` | ✅ | V3 |
| 7 | Senaryo log kayıtları (+415) | Betik | `tools/mercek_data/inject_log_scenarios.py` | ✅ | V3 |
| 8 | Doğal dil metinleri (~620) | Betik + Foundry | `tools/mercek_data/generate_texts.py`, `prompts/gen-*.md` | ✅ betik · şablon çıktısı hazır; Foundry çıktısı 🔧 | V4 |
| 9 | Müşteri ve kredi portföyü (40.000 / 33.000) | Betik | `tools/mercek_data/generate_portfolio.py` | ✅ | V5 |
| 10 | Müşteri temasları, çağrılar ve çözümler (~8.300 / 1.400 / 37) | Betik | `tools/mercek_data/generate_incidents.py` | ✅ | V6 |
| 11 | Geçmiş talepler (95) ve değerlendirme seti (30) | Betik | `tools/mercek_data/generate_requests.py` | ✅ (değerlendirme seti elle gözden geçirilecek) | V6 |
| 12 | Yükleme (SQL + AI Search) ve şema | Betik | `tools/mercek_data/load_all.py`, `db.py`, `search.py` → `data/schema.sql` | ✅ (Azure bağlantısı hackathonda denenecek) | V1, V7 |
| 13 | B'nin demo penceresi (46 log + CAG-2051 + 11 vaka) | Betik | `tools/mercek_data/demo_reset.py` | ✅ | V8 |
| 14 | Doğrulama (§12 tablosu + değerlendirme seti) | Betik | `tools/mercek_data/validate_scenarios.py` | ✅ | V8 |
| 15 | Canlı olay logları (A, B, C) | Uygulama | `/api/logs`, `/api/odm/bills/query` | 🔧 | M1.1-b |
| 16 | Canlı çağrı kayıtları (ana kayıt, bağlı vaka, yeni çağrı) | Uygulama | `/api/mercek/assist` | 🔧 | M1.3 |
| 17 | Canlı talep kayıtları (TLP-1043, TLP-1044) | Uygulama | `/api/requests/*` | 🔧 | M2.5-d |
| 18 | Mercek ölçümleri (önlenen çağrı, bağlı vaka, süre, token) | Uygulama | `mercek_events` | 🔧 | M1.6 |

---

## 1. Elle yazılanlar

Elle yazılan veri, demodaki cevapların doğrudan dayandığı kesin bilgidir. Rastgele üretilseydi senaryo tutmazdı.

### 1.1 Katalog (`data/seed/catalog.json`) ✅

| Bölüm | Adet | Senaryodaki rolü |
|---|---|---|
| `screens` | 20 (5 simüle, 15 yalnızca katalogda) | Bağlam, ekran kodu çakışma kontrolü (E: `KRDTERTL` boş), değişecek ekran (D: `KRDRTKSR`), kod dosya haritası (C) |
| `services` | 7 | Servis bazlı etki analizi |
| `screen_services` | 30 | Ana ve etkileşimli servis (D, E) |
| `error_rules` | 17 | Çağrı açılır mı, hangi servise gider (A: açılmaz; B, C: Fatura Ödeme) |
| `service_calendar` | 11 | Takvim ve kapasite çatışması (D: 9 Kasım; E: iki seçenek) |
| `scope_addons` | 5 | Köprü önerilerinin eforu (+2 a/g) |
| `institutions` | 15 | Fatura kurumları, metinden kurum çıkarma ve normalize etme |
| `branches` | 5 | Şube kodları |
| `incident_categories` | 6 kategori, 32 alt kategori | Çağrı üretimi ve zenginleştirme (yetersiz bakiye ve başvuru tamamlanamadı yalnızca teknoloji çağrılarında) |
| `demo_users` | 5 | Elif, Zeynep, Kerem, Fatma, Hakan |
| `affected_region` | 3 il | E (il adları V5'te seçilir, arayüzde gösterilmez) |

### 1.2 Kurum duyuruları (`data/seed/announcements.json`) ✅

20 duyuru, her biri 3–5 cümle. Senaryo için kritik olanlar DUY-0412 (İSKİ, 13 hane, 1 Ekim) ve DUY-0419 (ASKİ, 13 hane, 1 Ocak 2027); diğer 18'i ilgisizdir ve Mercek'in doğru duyuruyu ayıklayabildiğini gösterir.

### 1.3 Demo kullanıcıları 🔧

Veri `catalog.json → demo_users`'ta hazır. Uygulamaya eklenmesi A6-ek prompt'uyla `frontend/src/lib/auth/users.ts` içine yapılır. Ayşe (u-2) ve Mehmet (u-3) rebuild rehberinden gelir.

### 1.4 Kesin senaryo metinleri (`data/seed/fixed_texts.json`) ✅

Senaryonun kesin parçaları modele bırakılmaz; metinleri elle yazılmıştır. Betikler (V4 ve V6) bunları aynen kullanır:
- **C'nin 5 çağrı notu** ("abone numarası kabul edilmiyor"): V4 bunları şablonla 15'e çoğaltır
- **SOL-031** (kurum entegrasyonu zaman aşımı çözümü, B'nin %93 eşleştiği kayıt): §7
- **D'nin 5 benzer talebi** (TLP-0871, 0915, 0962, 1004, 1019) servis payları ve kararlarıyla: §8
- **E'nin 3 benzer talebi** (TLP-0588, 0712, 0846): §8

### 1.5 Değerlendirme setinin beklenen değerleri 🔧

30 vakanın metinleri Foundry ile taslak olarak üretilir; `expected_*` alanları ve son metinler elle gözden geçirilir (§8.1).

---

## 2. Betikle üretilenler

Ortak kurallar:
- Python, `seed=42`; aynı komut her seferinde aynı veriyi üretir.
- Tarih referansı: veri **17.10.2026 09:00 (TR)**'de biter (`--end 2026-10-17T09:00:00+03:00`).
- Kişisel veri yok: e-posta `@ornek.test`, IP'ler dokümantasyon blokları (`192.0.2.x`, `198.51.100.x`, `203.0.113.x`), IBAN'lar simülasyon banka kodu `00999`.
- Çıktılar `tools/output/` ve `data/out/` altına yazılır (git'e girmez). Commit'lenenler: `data/seed/*.json`.

### 2.1 `tools/generate_banking_logs.py` ✅ (V3 · rebuild Faz 5)

**Ne yapar:** Beş bankacılık ekranı için Kibana (ECS) uyumlu işlem logu üretir. Senaryodan bağımsız, gerçekçi bir "normal 30 gün" sağlar.

**Nasıl çalışır:**
1. 800 kişilik müşteri havuzu kurar: Türkçe ad soyad, segment (Bireysel / Premium / Özel Bankacılık) ve segmente göre log-normal gelir, yaş, meslek, 12 il. Müşteri numaraları portföy aralığından (10000101–10040100) seçilir. Bazı müşteriler çok aktiftir (Pareto).
2. Zaman damgalarını son 30 güne dağıtır: Türkiye saatine göre gece düşük, gündüz yüksek; hafta sonu %40 az. UTC'ye çevirerek yazar.
3. Her kayıt için ekran (ODMTFATR %35 …), müşteri ve kanal (Mobil %55 …) seçer. %25'i ekran görüntüleme, %75'i işlemdir.
4. İşlemlerin %3'ü teknik hata (`CORE_BANKING_TIMEOUT`, `SERVICE_UNAVAILABLE`, `DB_CONNECTION_ERROR`), %12'si iş kuralı reddidir.
5. **İş kuralları tutarlıdır**, rastgele değildir:
   - KRTTBASV: kart gelir şartı ve `min(talep, gelir × 3, tavan)` onay limiti; `INSUFFICIENT_INCOME` yalnızca gelir şartı gerçekten karşılanmadığında.
   - KRDTKULL: `loanPlan` formülüyle taksit; `AFFORDABILITY_EXCEEDED` yalnızca taksit > gelir × 0,5 olduğunda, başarılı kullandırımlarda hiçbir zaman.
   - ODMTFATR: kurum ve müşteriye kalıcı 6–12 haneli abone numarası.
   - HSPTVDSZ: geçerli IBAN (mod-97).
6. Tutarlar mesajlarda Türkçe biçimdedir (`13.500 TRY`, `747,71 TRY`).

**Girdi:** yok. **Çıktı:** `tools/output/dalan-banking-logs.ndjson` (10.000 satır). `--format bulk` ile Elasticsearch `_bulk` dosyası, `--write-template` ile index template.

**Komut:**
```bash
python3 tools/generate_banking_logs.py --count 10000 --days 30 --seed 42 --end 2026-10-17T09:00:00+03:00
```

**Ölçülen sonuç (seed 42):** info %88,8 · warn %8,9 · error %2,3; tüm IBAN'lar geçerli; kural ihlali yok.

### 2.2 `tools/mercek_data/inject_log_scenarios.py` ✅ (V3)

**Ne yapar:** Üreticinin çıktısını okur, senaryoların log tarafını üstüne ekler. Üreticiye dokunmaz.

**Nasıl çalışır:**
1. **Temizlik:** Üreticinin ODMTFATR `VALIDATION_ERROR` kayıtlarını `error.field = amount` ("Fatura tutarı doğrulanamadı") yapar. Böylece abone numarası hataları yalnızca senaryodan gelir. Her fatura kaydına `subscriber_no_len` ekler. Üretici 13 haneli İSKİ numarası üretmişse durur (yasak kural).
2. **C · İSKİ:** Havuzdan 187 müşteri seçer; her birine 13 haneli bir abone numarası verir. 1 Ekim–17 Ekim arasına gündüz ağırlıklı, müşteri başına 1–5 deneme olacak şekilde **400 kayıt** yazar (ilk denemeden sonraki denemeler 3 gün içinde). Kanal: İnternet Şube %55, Mobil %35, Şube %10.
3. **C · gerçek kullanıcı hataları:** Diğer kurumlarda 4–5 haneli ya da harf içeren numaralarla **12 kayıt** (%97'yi tamamlayan %3).
4. **Mehmet:** 27, 18 ve 6 gün önce Başkentgaz'a (abone 4012345678) 3 başarılı ödeme.
5. **B · demo penceresi:** `build_demo_window(now, havuz)` fonksiyonu `now − 30 dk … now − 1 dk` arasına 46 Başkentgaz `INSTITUTION_TIMEOUT` kaydı üretir. Bu kayıtlar dosyaya yazılmaz; `demo_reset.py` her provadan önce demo saatine göre SQL'e yazar. Yerelde denemek için `--demo-window-now`.
6. Kayıtları zamana göre sıralar, yazar ve kontrol eder. Bir değer tutmazsa hata verir.

**Girdi:** `tools/output/dalan-banking-logs.ndjson`. **Çıktı:** `tools/output/mercek-logs.ndjson` (10.415 satır).

**Komut:**
```bash
python3 tools/mercek_data/inject_log_scenarios.py --end 2026-10-17T09:00:00+03:00
# yerel deneme: B'nin demo penceresini de ayrı dosyaya yaz
python3 tools/mercek_data/inject_log_scenarios.py --demo-window-now 2026-10-17T15:10:00+03:00
```

**Ölçülen sonuç:** 1 Ekim sonrası abone no hatası 412 · İSKİ 400 (%97,1) · hepsi 13 hane · 187 farklı müşteri · 1 Ekim öncesi 13 hane 0 · Mehmet 3 ödeme · demo penceresi 46.

**Testler:** `python3 -m pytest tools/mercek_data/tests -q` (9 test: belirlenimcilik, hacim ve sıra, seviye dağılımı, iş kuralı tutarlılığı, IBAN, Türkçe tutar biçimi, C rakamları, enjeksiyon dışı abone hatası olmaması, Mehmet, demo penceresi).

### 2.3 `tools/mercek_data/generate_texts.py` ✅ (V4)

**Ne yapar:** Çağrı notları, çözüm kayıtları ve geçmiş talep metinlerini üretir; değerlendirme seti için taslak çıkarır. Arama (AI Search) bu metinlerle çalıştığı için çeşitli olmaları gerekir.

**İki mod:**
- **Foundry (varsayılan):** `prompts/gen-cagri-notu.md`, `gen-cozum.md`, `gen-talep.md` prompt'larıyla Foundry'deki `chat` modeline 20'şerli partilerle istek atar (sıcaklık 0,8, JSON çıktı). Yalnızca standart kütüphane kullanır. Anahtar `AZURE_OPENAI_API_KEY`'den, yoksa `azure-identity` ile Entra token'ından gelir. 429 ve 5xx hatalarında 3 kez tekrar dener.
- **Şablon (`--template`):** İnternet ve Azure gerektirmez; ifade bankalarından deterministik metin üretir. Foundry hazır değilken V5–V6'nın beklememesi ve testler için. Gerçek metinler Foundry hazır olunca `--force` ile üzerine yazılır.

**Nasıl çalışır:**
1. Plan: katalogdaki 30 çağrı alt kategorisi (her birine 15 not; D'nin üç ve E'nin bir alt kategorisine 30), 9 hata kodu (toplam 36 çözüm; SOL-031 elle) ve 87 talep (modül × ekran × tip dağılımıyla).
2. Her partiyi filtreler: yasak konular (çözümlerde abone numarası ve hane; taleplerde hatırlatma ve erteleme), kişisel veri desenleri (10+ haneli rakam, `@`, `+90`, IBAN), tekrar ve %80'den fazla kelime örtüşmesi. Atılan oran %20'yi geçerse partiyi bir kez daha ister.
3. C'nin "abone numarası kabul edilmiyor" notları `fixed_texts.json`'daki 5 elle yazılmış nottan başlar; kalan 10'u şablonla tamamlanır (modele bırakılmaz).
4. Sonucu `data/seed/texts.json`'a yazar (commit'lenir). Tekrar çalıştırmada hazır olan konuları atlar; aynı metinler için tekrar ödeme yapılmaz.

**Girdi:** `catalog.json`, `fixed_texts.json`, `prompts/gen-*.md`. **Çıktı:** `data/seed/texts.json`.

**Komut:**
```bash
python3 tools/mercek_data/generate_texts.py --dry-run          # plan ve mevcut durum
python3 tools/mercek_data/generate_texts.py --template --force # çevrimdışı (hazır çıktı bu modda)
export AZURE_OPENAI_ENDPOINT=<…> AZURE_OPENAI_API_KEY=<…> CHAT_DEPLOYMENT=chat
python3 tools/mercek_data/generate_texts.py --force            # Foundry ile gerçek metinler
```

**Ölçülen sonuç (şablon modu):** 465 çağrı notu · 36 çözüm (+ SOL-031) · 87 talep (+ 8 elle) · 30 değerlendirme taslağı; yasak konu ve kişisel veri 0.

**Testler:** 7 test (hacimler, elle yazılmış notların korunması, yasak konu ve kişisel veri yokluğu, belirlenimcilik, filtre, sahte Foundry istemcisiyle parti/filtre/devam etme akışı, prompt yükleyici).

### 2.4 `tools/mercek_data/generate_portfolio.py` ✅ (V5)

**Ne yapar:** 40.000 müşteri ve 33.000 krediden oluşan sentetik portföyü üretir. D ve E'nin büyüklük rakamları (hedef grup, izinler, etkilenen bölge) buradan sorgulanır.

**Nasıl çalışır:** Önce senaryo kümeleri tam sayıda kurulur, kalan veri dağılımla üretilir.
1. **Log müşterileri:** V3 çıktısındaki müşteriler (seed 42'de 784 kişi) aynı numara, ad, il ve segmentle portföye alınır; logda geliri görünüyorsa o gelir kullanılır. Böylece bir log satırından portföye gidildiğinde bilgiler tutarlıdır.
2. **Diğer müşteriler:** 10000101–10040100 aralığının geri kalanı, üreticiyle aynı ad, il, segment ve gelir dağılımıyla üretilir. E-posta `ad.soyad.NNNN@ornek.test`, telefon `+90 5xx 000 xx xx`.
3. **E · etkilenen bölge:** İstanbul, Ankara ve İzmir dışındaki en büyük üç il (Bursa, Antalya, Adana) `region_affected = 1` olur ve `catalog.json → affected_region.provinces` alanına yazılır. **İl adları arayüzde ve sunumda gösterilmez.** Bölgede tam **4.870** müşteriye kredi verilir, bu müşterilere toplam **6.215** kredi dağıtılır (müşteri başına en çok 3), bunların tam **612**'si şu an gecikmededir. Bölgedeki kredili müşterilerden **37**'sinin adres değişiklik tarihi 11–16 Ekim'dir; başka hiçbir müşterinin adresi afet tarihinden sonra değişmemiştir.
4. **Toplam:** Bölge dışında 21.130 kredili müşteri ve 26.785 kredi; böylece toplam **26.000** kredili müşteri ve **33.000** kredi. Bölge dışında yaklaşık 950 kredi şu an gecikmededir.
5. **D · hedef grup:** Şu an gecikmede kredisi olan herkes ve kalan kredili müşterilerden rastgele seçilenlerle tam **2.340** müşteri "son 12 ayda gecikme yaptı" olarak işaretlenir.
6. **D · izinler:** Hedef grupta e-posta ve SMS izinleri birebir dağıtılır: 1.169 ikisi de · 188 yalnız e-posta · 726 yalnız SMS · 257 hiçbiri (e-posta %58, SMS %81, en az biri %89). Diğer müşterilerde e-posta yaklaşık %64, SMS %82.
7. **Kredi kuralları KRDTKULL ile aynı:** tutar 5.000–500.000 TL, vade 3–36 ay, faiz vadeye göre %3,09 / %3,29 / %3,49, taksit tek başına gelirin yarısını aşmaz. Kalan anapara ödenen taksit sayısına göre hesaplanır; gecikmedeki kredilerin sıradaki taksit tarihi geçmiştedir. Tahsilat hesabı simülasyon IBAN'ıdır.
8. Tüm kesin değerleri kontrol eder; biri tutmazsa dosya yazmadan durur.

**Girdi:** `tools/output/mercek-logs.ndjson` (V3), `data/seed/catalog.json`. **Çıktı:** `data/out/customers.csv` (40.000), `data/out/loans.csv` (33.000); katalogda etkilenen iller.

**Komut:**
```bash
python3 tools/mercek_data/generate_portfolio.py
```

**Ölçülen sonuç:** 40.000 müşteri · 26.000 kredili · 33.000 kredi · D 2.340 (1.169 / 188 / 726 / 257) · E 4.870 / 6.215 / 612 / 37 · log müşterilerinin hepsi portföyde. Süre yaklaşık 3 saniye.

**Testler:** 6 test (senaryo rakamları, log müşterileriyle tutarlılık, bölge ve adres değişikliği, kredi kuralları, kişisel veri yokluğu, belirlenimcilik).

### 2.5 `tools/mercek_data/generate_incidents.py` ✅ (V6)

**Ne yapar:** İki ayrı kayıt türünü ve çözüm bilgi bankasını üretir.
- **Müşteri temasları (`contacts`):** Müşterinin çağrı merkezini araması ya da şubeye gelmesi; temsilcinin notu. Çoğu o an çözülür. D ve E'nin köprü sayıları buradan sayılır.
- **Teknoloji çağrı kayıtları (`incidents`):** Teknolojiye açılan destek kaydı (CAG-xxxx). B'nin geçmiş olayları ve C'nin açık çağrıları buradadır.
- **Çözümler (`solutions`):** V4'teki 36 çözüme SOL-001'den numara verir (SOL-031 elle yazılmış kayda ayrılmıştır).

**Nasıl çalışır:**
1. **Arka plan temasları:** Son 90 günde bölge dışından günde 69, etkilenen illerden günde 16 temas. Kategori dağılımı katalogdan, müşteri ve il portföyden, not V4'ten. D'nin üç alt kategorisi ve C'nin alt kategorisi arka planda hiç kullanılmaz; bölgede erteleme konusu da kullanılmaz. Böylece senaryo sayıları kesin kalır.
2. **D:** Kredi kategorisinde 71 / 64 / 51 temas (bölge dışı müşterilerden, son 90 güne dağılmış).
3. **E:** 12.09–11.10 arasında bölgeden tam 480 temas (günde 16); 12.10 sonrası bölgedeki kredili müşterilerden 497 temas, 418'i "erteleme / ödeme güçlüğü".
4. **Çağrılar:** B'nin 6 geçmiş olayı (SOL-031, 45–120 dk) ve C'nin 23 açık İSKİ çağrısı kesin; C'nin müşteri, abone no ve `trace_id` değerleri V3 loglarındaki İSKİ denemelerinden alınır, böylece log ile çağrı birbirini doğrular. Kalan çağrılar ekran ve hata kodu karışımıyla üretilir; servis hata–servis kuralından atanır. Arka planda açık Başkentgaz çağrısı yoktur (açık olan tek Başkentgaz kaydı demodaki CAG-2051).
5. Kayıtlar zamana göre sıralanır, numaralanır (TMS-000001…, CAG-0651…CAG-2050) ve kontrol edilir.

**Girdi:** `catalog.json`, `texts.json`, `fixed_texts.json`, `data/out/customers.csv` ve `loans.csv` (V5), `tools/output/mercek-logs.ndjson` (V3). **Çıktı:** `data/out/contacts.csv`, `incidents.csv`, `solutions.csv`.

**Komut:** `python3 tools/mercek_data/generate_incidents.py`

**Ölçülen sonuç:** 8.322 temas · 1.400 çağrı (CAG-0651…CAG-2050) · 37 çözüm · D 71 / 64 / 51 = 186 · E 497 (418) / günlük 16 · B 6 · C 23. Süre yaklaşık 1 saniye.

### 2.6 `tools/mercek_data/generate_requests.py` ✅ (V6)

**Ne yapar:** Geçmiş talepleri (`requests`) ve `--eval` ile değerlendirme setini (`eval_cases.json`) üretir.

**Nasıl çalışır:**
1. V4'teki 87 talep metnine (hatırlatma ve erteleme konulu olanlar yeniden elenir) TLP-0500…TLP-1037 aralığından numara verir; numarası büyüdükçe tarihi yenidir (2020-06 → 2026-10).
2. Her talebe ekranı, tipi, talep eden birimi, efor (3–40 a/g, ortanca ~12), bileşen ve servis payları (ana servis ekran–servis ilişkisinden, etkileşimli servis %10–30) ve durum (tamamlandı) ekler.
3. Elle yazılmış 8 kesin talep (D'nin 5'i, E'nin 3'ü) kendi numaralarıyla ve üretim rehberi §8'deki efor, servis payı ve kararlarla birebir eklenir. Mercek'in 18 a/g ve 15 a/g tahminleri bunlardan hesaplanır.
4. **`--eval`:** 10 eşleşmeli vaka (rastgele 10 çözüm, başlığı farklı bir cümle kalıbına yerleştirilerek; beklenen çözüm no'suyla), 10 eşleşmesiz vaka (V4 taslakları) ve 10 talep vakası (beklenen tip, ekran ve ana servisle). Her vaka indeksteki çözüm ve talep metinleriyle karşılaştırılır; kelimelerin %80'i ortaksa betik durur. Vakalar `"reviewed": false` ile yazılır, elle gözden geçirilip `true` yapılır.

**Girdi:** `catalog.json`, `texts.json`, `fixed_texts.json`; `--eval` için `data/out/solutions.csv`. **Çıktı:** `data/out/requests.csv` (95), `data/seed/eval_cases.json` (30, commit'lenir).

**Komut:** `python3 tools/mercek_data/generate_requests.py --eval`

**Testler (V6, 7 test):** senaryo rakamları; C çağrılarının loglarla eşleşmesi; B geçmişi ve açık Başkentgaz kaydı olmaması; servis atamaları; çözüm numaraları ve yasak konular; talep numaraları, tarih sırası, kesin talepler ve yasak konular; değerlendirme setinin grupları ve sızıntı kontrolü.

### 2.7 `tools/mercek_data/load_all.py` + `db.py` + `search.py` ✅ (V1, V7)

**Ne yapar:** Şemayı kurar, tüm veriyi veritabanına yükler; `--search` ile 3 AI Search indeksini oluşturup embedding'leriyle doldurur.

**Nasıl çalışır:**
1. **Şema (`db.py`):** 15 tablonun tanımı tek yerde durur. Aynı tanımdan Azure SQL (T-SQL) ve SQLite DDL'i üretilir; `data/schema.sql` bu tanımdan yazılır (`--write-schema`), elle düzenlenmez. JSON alanlarında `ISJSON` kontrolü, zaman alanları UTC (`DATETIMEOFFSET(3)`). Yabancı anahtar yok; bütünlüğü doğrulama betiği kontrol eder.
2. **Yükleme sırası:** şema → katalog (6 tablo) → duyurular → müşteri/kredi → loglar (ECS kaydı düzleştirilir, tam kayıt `raw_json`'da, `source = 'seed'`) → temas → çözüm → çağrı → talep. Tek transaction; hata olursa hiçbir şey yazılmaz.
3. **Toplu yazma:** parametreli `INSERT`, 1.000'lik paketler; Azure SQL'de `fast_executemany`.
4. **Bağlantı:** `SQL_SERVER`, `SQL_DATABASE`; `SQL_USER` + `SQL_PASSWORD` varsa SQL kimlik doğrulama, yoksa Entra (`ActiveDirectoryDefault`, Managed Identity dahil). Şifre koda ve loga yazılmaz.
5. **AI Search (`search.py`) · otomatik eşitleme:** `solutions` (37), `requests` (95), `announcements` (20). Varsayılan mod **indexer**: AI Search bu 3 tabloyu SQL'den kendisi okur (değişiklik takibi, 5 dakikada bir ya da `--sync` ile hemen), embedding'i skillset içinde Foundry'ye kendisi ürettirir. Aranacak metin SQL'de hesaplanan `search_text` kolonudur. Yedek mod `--search-mode push`: betik embedding'i üretip belgeleri yükler. Türkçe analizör, `content_vector` (boyut `EMBEDDING_DIM`, HNSW, cosine). Ayrıntı ve yetki adımları: [`mercek-sql-search-esitleme.md`](mercek-sql-search-esitleme.md).

**Komutlar:** `load_all.py --sqlite` (yerel) · `--sql` · `--search` (indexer) · `--search --search-mode push` · `--sync` · `--all` · `--write-schema`

**Ölçülen sonuç (SQLite):** 15 tablo, 10.415 log, 40.000 müşteri, 33.000 kredi, 8.322 temas, 1.400 çağrı, 37 çözüm, 95 talep, 20 duyuru. Süre yaklaşık 2 saniye.

### 2.8 `tools/mercek_data/demo_reset.py` ✅ (V8)

**Ne yapar:** Her prova ve sunumdan hemen önce demo verisini temiz ve tekrarlanabilir bir başlangıca getirir.

**Nasıl çalışır (tek transaction):**
1. Siler: `CAG-2051` ve sonrası, `TLP-1043` ve sonrası, seed dışı loglar (önceki demo penceresi ve uygulamanın yazdığı canlı loglar), `mercek_events`. Seed verisine dokunmaz.
2. B penceresi: `build_demo_window` ile `now − 30 dk … now − 1 dk` arasına 46 Başkentgaz zaman aşımı logu (seed 7: her seferinde aynı müşteriler). **CAG-2051** (`now − 24 dk`) ve bağlı **11 vaka** `CAG-2051-01 … -11` (`now − 22 … − 2 dk`); müşteri, abone no ve `trace_id` pencere loglarından alınır, yani çağrı ile log birbirini doğrular.
3. `--with-d-plan`: D'nin talebi TLP-1043 planlı olarak eklenir (20 a/g, Kredi Takip, 09.11 – 04.12). E'yi tek başına oynatmak için.

**Numara kuralı:** Bağlı vaka numarası ana kayıt no + sıra. Böylece Mehmet'in vakası `CAG-2051-12`, C'de açılacak yeni ana kayıt `CAG-2052` olur.

**Komut:** `demo_reset.py --sql [--now 2026-10-17T13:20:00+03:00] [--with-d-plan]` (yerelde `--sqlite`). `--now` verilmezse şu an.

### 2.9 `tools/mercek_data/validate_scenarios.py` ✅ (V8)

**Ne yapar:** Üretim rehberi §12 tablosundaki her satırı sorgular; beklenen ve bulunan değeri yan yana yazar (✓ / ✗ / – atlandı). En az bir ✗ varsa çıkış kodu 1.

**Kapsam:** kayıt sayıları ve bütünlük; A (Elif'in geliri, `loanPlan` taksitleri ve azami tutar); B (son 30 dk 46 log, 11 bağlı vaka, SOL-031 aramada ve skor ≥ eşik); C (412 / 400 / 13 hane / 187, öncesinde 0, 23 çağrı, skor < eşik, DUY-0412 ve DUY-0419); D (71 / 64 / 51, hedef grup ve izinler, ilk 5 benzer talep, takvim); E (bölge sayıları, temas artışı, ilk 3 benzer talep, takvim seçenekleri, `KRDTERTL` yok); F (bugünün en sorunlu ekranı).

**Takvim:** §3.5 kuralının başvuru uygulaması (`plan()`): süre ⌈pay × 1,2⌉, hafta sonu atlanır, öncelik verilirse takvime bakılmaz. Backend'in takvim servisi aynı tarihleri vermelidir.

**`--eval`:** değerlendirme setinde match ≥ 8/10, yanlış eşleşme ≤ 1/10; talep grubu backend API'siyle ölçülür. Gözden geçirilmemiş vaka varsa "!" ile uyarır.

**Komut:** `validate_scenarios.py --sql --search [--now …] [--only B,C] [--eval]`. `--now`, `demo_reset` ile aynı an olmalı.

**Ölçülen sonuç (SQLite):** 17 ✓ · 0 ✗ · 5 atlandı (Search satırları; Azure'da çalışacak).

**Testler (V7/V8, 14 test):** şema dosyasının tanımla aynı olması, T-SQL biçimi, zaman normalizasyonu; SQLite'ta yükle → sıfırla → doğrula (17 ✓) ve sıfırlamanın tekrarlanabilirliği; bağlı vakaların pencere loglarından gelmesi ve numaraları; takvim kuralı; sahte Azure SQL bağlantısıyla 1.000'lik paketler ve hata durumunda geri alma; sahte Search ve embedding ile indeks tanımı, 50'lik partiler, boyut kontrolü, skor dönüşümü ve değerlendirme sayımı.

---

## 3. Uygulamanın ürettikleri

Bu veriler demo sırasında uygulama çalışırken oluşur. Böylece "anlık log kontrolü" ve "çağrı kaydı" gerçektir: jüri SQL'e bakarsa az önce oluşan satırı görür. Uygulama, betiklerle aynı alan adlarını (ECS) kullanır.

### 3.1 Canlı olay logları (M1.1-b)

**Uygulama parçası:** Next.js bankacılık ekranları + FastAPI `POST /api/logs` ve `POST /api/odm/bills/query`.

| Senaryo | Tetikleyen | Ne yazılır |
|---|---|---|
| A | Elif KRDTKULL'de 400.000 TL / 3 ay girer, uygunluk uyarısı ilk kez görünür | `AFFORDABILITY_EXCEEDED`, warn; `banking.loan` (tutar, vade, oran, taksit, gelir, oran); `employee.id = u-4`; `trace.id` panel bağlamına verilir |
| B | Mehmet ODMTFATR'de Başkentgaz için Sorgula'ya basar | `DEMO_MODE=true` iken backend 504 döner ve `INSTITUTION_TIMEOUT` yazar: kurum, abone no 4012345678, müşteri 10000003, kanal İnternet Şube. Son 30 dakikanın **47. isteği** olur |
| C | Ekranda 13 haneli İSKİ numarası girilir | Frontend doğrulaması (`^\d{6,12}$`) reddeder ve `VALIDATION_ERROR`, `error.field = subscriber_no`, `subscriber_no_len = 13` yazar |

**Nasıl çalışır:** Ekran sonucu oluştuğunda istemci `POST /api/logs`'a ECS alt kümesi gönderir. Backend alanları doğrular (izinli ekran kodları, uzunluk sınırları), sunucu saatini ve gerekirse `trace.id`'yi ekler, `banking_logs`'a parametreli sorguyla yazar. Log yazılamazsa ekran akışı bozulmaz.

### 3.2 Canlı çağrı kayıtları (M1.3)

**Uygulama parçası:** `POST /api/mercek/assist` → `services/incidents.py`.

| Senaryo | Ne oluşur |
|---|---|
| A | Çağrı açılmaz; `mercek_events`'e `prevented_call` |
| B | Mehmet'in vakası (Zeynep'in mesajıyla) CAG-2051'e bağlı yeni satır olur (`CAG-2051-12`): müşteri no, abone no, `trace.id`, kanal çağrı merkezi. Bağlı vaka 11 → 12. `linked_case` olayı |
| C | Yeni ana kayıt **CAG-2052** açılır (Fatura Ödeme Servisi), yapay zekâ ile zenginleştirilir; 23 açık İSKİ çağrısı "ilişkili çağrılar" olarak bağlanır |

### 3.3 Canlı talep kayıtları (M2.5-d)

**Uygulama parçası:** `POST /api/requests/analyze`, `/answers`, `/scope`, `/plan-option`.

| Senaryo | Ne oluşur |
|---|---|
| D | Fatma'nın talebi **TLP-1043**: analiz, cevaplar, 18 → 20 a/g, plan 9 Kasım → 4 Aralık, "veriden eklenen kapsam: SMS", onaylayan Fatma, analist Ayşe; durum `planli` |
| E | Hakan'ın talebi **TLP-1044**: yeni ekran KRDTERTL, seçilen seçenek, 17 a/g, plan 19 Ekim → 2 Kasım; D'nin planı 18 Aralık'a kayar |

### 3.4 Mercek ölçümleri (M1.6)

**Uygulama parçası:** `mercek_events` tablosu ve `GET /api/mercek/metrics`. Her analizde süre ve token; her önlenen çağrı ve bağlanan vakada bir satır. Genel Bakış ve Mercek sayfasındaki sayaçlar buradan okur. `demo_reset.py` sıfırlar.

---

## 4. Çalıştırma sırası (hackathon)

```
V2  data/seed/*.json                    ✅ hazır; takım reposuna kopyala, V2 prompt'uyla dosya yollarını doğrula
V3  generate_banking_logs.py            ✅
    inject_log_scenarios.py             ✅  → tools/output/mercek-logs.ndjson
V4  generate_texts.py                   ✅  şablon çıktısı hazır; Foundry hazır olunca --force ile gerçek metinler
V5  generate_portfolio.py               ✅  → data/out/customers.csv, loans.csv
V6  generate_incidents.py               ✅  → contacts.csv, incidents.csv, solutions.csv
    generate_requests.py --eval         ✅  → requests.csv, data/seed/eval_cases.json (gözden geçir)
V7  load_all.py --all                   ✅  (yerelde --sqlite) → SQL + 3 indeks
V8  demo_reset.py --sql                 ✅  (her prova ve sunumdan önce)
    validate_scenarios.py --sql --search [--eval]  ✅  → hepsi ✓ olmalı (--now, demo_reset ile aynı)
```
