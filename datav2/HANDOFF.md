# Mercek — Yeni Oturuma Devir Notu (16.10.2026 18:15)

Bu not, uzayan oturumdan yeni bir Claude oturumuna geçiş içindir. Yeni oturumda **önce bu dosyayı ve `datav2/SCHEMA.md`'yi oku**, sonra §4'teki sıradan devam et.

## 1. Bağlam
- **Etkinlik:** Ziraat Teknoloji YZ Hackathonu (16–17 Ekim 2026). Takım AI Overflow, proje **Mercek**. Puan: AstreAI %30 (Repo 35, GHAS 15, CI/CD 15, Azure 15, LLM maliyeti 20), jüri %70.
- **Mimari:** Next.js 16 + FastAPI (iki App Service), Azure SQL (kayıt ve hesap), Azure AI Search (hibrit RAG; SQL'den indexer ile otomatik eşitleme), Foundry (`chat`, `embedding`).
- **İlke:** "Hesabı kod yapar, AI açıklar." AI önerir, insan onaylar. Mercek'in türettiği alanlar `mercek_assigned_*`.
- **Yanıt dili Türkçe.** Kod tanımlayıcıları İngilizce.

## 2. Repolar
| Repo | İçerik |
|---|---|
| `SeyhanAmasyalii/ZtHackathonStudyWithData` (dal `main`) | Kod, veri, üretilmiş çıktılar, **`datav2/`** (yeni JSON veriler, SCHEMA.md, bu dosya) |
| `SeyhanAmasyalii/ZtHackathonStudy` | Yalnızca bilgi dokümanları (kod/veri yok) |
| `SeyhanAmasyalii/ZtHackathonStudyOnlyDoc` | Eski tam kopya (529345d), güncellenmiyor |
| Claude projesi "ZT Hackhton" | `claude/*.md` dokümanları |

Commit mesajları şu satırlarla biter:
```
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```
(+ yeni oturumun `Claude-Session:` satırı)

## 3. Çalışma biçimi (kullanıcının istekleri)
- **Mevcut koda ve üretilmiş veriye dokunma** (`tools/`, `data/seed`, `data/out`, `tools/output`). Her şey en sonda tek seferde güncellenecek (§5).
- JSON sentetik veri **tablo tablo** üretilir; her tabloyu sun → kullanıcı **"ok"** demeden sonrakine geçme. Onaylanan dosya `datav2/<tablo>.json` olarak kaydedilir, `datav2/README.md` tablosuna satır eklenir, commit + push.
- Veriler demo senaryolarını (A–G) kapsamalı ve tutarlı olmalı (aşağıda §6).
- Şema/tablo tanıtım biçimi (kullanıcı Teams'e kopyalıyor):
  ```
  **tablo** — *Not: ...*
  - **kolon**
    - **Açıklama:** ...
    - **Örnek değer:** ...
  ```
- Kısa ve odaklı yanıt; karar gereken noktaları numaralı sor (kullanıcı "1. uygun 2. ok" diye yanıtlar).

## 4. Kaldığımız yer ve sıradaki adımlar
**Biten JSON'lar (`datav2/`):** screens (9) · departments (6) · screen_departments (23) · error_handling_rules (20) · closure_codes (62).

**Sıradaki (sırayla):**
1. **org_units** — 5 şube + G tipi 90xx genel müdürlük birimleri + birkaç B bölge (SCHEMA.md).
2. **institutions** — 16 kurum (catalog.json'daki 15 + Gelir İdaresi VRG01).
3. **institution_screens** — fatura kurumları → ODMTTLMT. Gelir İdaresi için hangi ekran (9 ekranda vergi ekranı yok) kullanıcıya sorulacak.
4. **channels** — 5 kanal.
5. **incident_categories** — 9 yeni ekrana göre gözden geçir; yalnızca temas alt kategorilerini çıkar.
6. **scope_addons** — önce şemayı kullanıcıyla gözden geçir (departman uyumu).
7. Ana tablolar: customers → loans → kibana_logs → solution_templates → incidents → inbound_emails → announcements → demands → department_calendar → prevented_calls (prevented_calls demoda dolar; boş/örnek). Büyük tablolarda (40.000 müşteri, 33.000 kredi, ~10.000 log) tam JSON yerine **üretici betik + örnek JSON + sayılar** önerilip kullanıcıya sorulmalı.

**Bekleyen hatırlatmalar:**
- 🔔 **KVKK (tablo belirlemesi bitince kullanıcıya hatırlat):** Foundry'ye göndermeden önce maskeleme yardımcısı + tüm metin alanlarında otomatik KVKK taraması (TCKN algoritması, telefon, `@ornek.test` dışı e-posta, IBAN, Luhn kart no, kişi adı listesi, IP/makine adı) → validate'te "✓ KVKK taraması · 0 bulgu" + birim testi.
- 📎 **Maliyet Tahminleme Formu (Excel)** sisteme eklenecek; kullanıcı detayı sonra verecek. Dosya eski oturumun eklerindeydi — **yeni oturumda kullanıcıdan tekrar eklemesini iste** (repoya konmadı).

## 5. En sondaki büyük güncelleme (#9, tek seferde)
Tüm JSON'lar bitince: `datav2` → `data/seed` ve üreticiler; kod (db.py, schema.sql, generate_*, load_all, demo_reset, validate_scenarios, search.py), testler, veri yeniden üretimi, senaryo doğrulaması; dokümanlar, prompt'lar, sunum; iki repo + proje senkronu. İçerik:
- error_rules → **error_handling_rules** (öğrenen kurallar, error_number, onay akışı; backend `GET /api/rules/proposals`, `POST /api/rules/{id}/approve`; C için örüntü eşiği 30 günde ≥ 50).
- servis → **departman** her yerde (`services`→`departments`, `service_id`→`department_id`, `demo_users.department`→`unit`). Değişmeyen: App Service, SERVICE_UNAVAILABLE.
- customers (birth_date; region_affected/address_changed_at/in_logs kalkar; 37 adres değişikliği MUSTGUNC loguna).
- banking_logs → **kibana_logs** (SCHEMA.md kolonları); incidents yeni kolonları.
- `dalan` → **fineart**.
- solutions → **solution_templates** + closure_codes; incidents'a kapanış kolonları.
- institution → **institution_code**; Gelir İdaresi.
- **inbound_emails → announcements → etki analizi → talep önerisi** (C ve G yeni akış; AI Search'e inbound_emails indeksi).
- Katalog tabloları (org_units, institutions, institution_screens, channels, incident_categories).
- requests → **demands** (API `/api/demands/*`, indeks `demands`).
- service_calendar → **department_calendar** (talebe bağlı; 11 satır planlı talep olur).
- **contacts kaldırılır**; D ve E kanıtı loans/customers'tan.
- mercek_events → **prevented_calls**; ai_usage yok.
- Geçmiş taleplerdeki eski ekran referansları 9 ekrana dağıtılır; B ve C ODMTFATR → **ODMTTLMT**; D butonu **KRDTTAHS**.

## 6. Demo senaryoları (güncel)
- **A:** KRDTKULL uygunluk (taksit > gelirin %50'si) → iş kuralı, çağrı önlenir (prevented_calls).
- **B:** Başkentgaz (GAZ02) zaman aşımı, **ODMTTLMT** abone doğrulamada (110731 INSTITUTION_TIMEOUT technical) → CAG-2051 ana kayıt + bağlı vakalar CAG-2051-NN (Mükerrer Çağrı); SOL-031.
- **C:** İSKİ 13 haneli abone no, ODMTTLMT (110412 SUBSCRIBER_NO_INVALID, kural çağrı açma der) → Mercek örüntüden aşar (01.10 sonrası 412 hata, %97 İSKİ, hepsi 13 hane, öncesinde 0) → CAG-2052. Kök neden: İSKİ duyurusu (12.09) ortak kutuya gelmiş, işlenmemiş. Kalıcı çözüm: hane sayısı PRMTGENL'de parametre.
- **D:** KRDTTAHS'a hatırlatma butonu (Kredi Takip ana, Müşteri Yönetim etkileşimli) → TLP-1043, ADD-SMS önerisi (%42 e-postasız), 18→20 a/g, takvim 09.11→04.12. Kanıt: 12 ayda 2.340 müşteri / 3.249 kredi gecikme; bugün 1.562 gecikmede.
- **E:** Erteleme ekranı (KRDTERTL katalogda yok) → TLP-1044, bölgede 4.870 kredili müşteri, 3.973 SMS izinli (en az bir kanal 4.516) → ADD-PROAKTIF-SMS; kapasite çatışması TLP-1021. Gerçek afet/il/tarih gösterilmez.
- **F:** Günün en sorunlu ekranı.
- **G:** ASKİ Ocak 2027 duyurusu (DUY-0419) → hata olmadan proaktif talep TLP-1045 (origin mercek, status oneri, ~4 a/g, FATURA_ODEME 09.11→20.11).
- Demo kullanıcıları: Elif (şube), Zeynep (çağrı merkezi), Kerem (L2/kural onayı), Fatma (analist/talep), Hakan.

## 7. Kesin kurallar
- Organizasyonun **CodeQL workflow dosyasına dokunma**; ikinci CodeQL yok; `.github/` dışlanmaz.
- Repoya **secret / API key / şifre / connection string yazma**; örneklerde `<PLACEHOLDER>`.
- **Gerçek müşteri/kişisel veri yok**; kullanıcının paylaştığı ekran görüntülerindeki IP, makine adı, kişi adı, olay numaraları veriye alınmaz. Gerçek kurum adı ("Ziraat Teknoloji" vb.) veride kullanılmaz.
- Kılavuz PDF'i (VDI şifresi içerir) repoya eklenmez. Hesap: `_ziraathc`.
- "Eyüp Dalan" demo karakteri olarak kullanılmaz.
- Değişiklikler takım reposunda feature branch + PR ile.

## 8. Yeni oturum için başlangıç mesajı (kopyala-yapıştır)
> ZtHackathonStudyWithData reposundaki `datav2/HANDOFF.md` ve `datav2/SCHEMA.md` dosyalarını oku. Mercek projesinde JSON sentetik veri üretimine kaldığın yerden devam et: sıradaki tablo **org_units**. Her tabloyu benim biçimimle sun, "ok" demeden sonrakine geçme; onaylananı `datav2/`'ye kaydet ve push et. Mevcut koda ve eski veriye dokunma.
