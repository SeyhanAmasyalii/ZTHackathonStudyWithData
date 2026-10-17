# Mercek — Modül 1 Geliştirme Başlangıç Dosyası (Claude Code)

> Bu dosya, Modül 1'i (Akıllı Problem Çözüm ve Çağrı Yönetimi) geliştirecek **yeni Claude Code oturumunun** başlangıç talimatıdır. Hedef repoya `CLAUDE.md` olarak da konabilir.
> Hazırlanma: 16.10.2026 · Kaynak veri: `SeyhanAmasyalii/ZTHackathonStudyWithData` → `datav2/`

---

## 0. İlk iş: oku, sonra başla

Sırayla oku. Çelişki olursa **üstteki kazanır**.

| # | Dosya | Ne için |
|---|---|---|
| 1 | Bu dosya | Kapsam, eski→yeni farkları, fazlar, kabul kriterleri |
| 2 | `datav2/SCHEMA.md` | **Nihai tablo şemaları** (tek doğru kaynak) |
| 3 | `datav2/README.md` | Her JSON'un içeriği ve senaryo notları |
| 4 | `datav2/HANDOFF.md` | Bağlam, senaryolar (A–G), kesin kurallar, yapılacaklar |
| 5 | `datav2/*.stats.json` | Senaryo sayılarının doğrulanmış değerleri |
| 6 | `docs/mercek-uygulama-rehberi.md` §0, §A, §M1 | Ayrıntılı M1 tasarımı (**eski veri adlarıyla yazılmış**, §2'deki sözlükle oku) |
| 7 | `docs/COPILOT_REBUILD_GUIDE.md` Faz 1–4, 7 | Temel uygulama iskeleti, bankacılık ekranları, Joyride |
| 8 | `docs/mercek-azure-kurulum.md`, `docs/mercek-sql-search-esitleme.md` | Azure kurulum ve SQL → AI Search eşitleme |
| 9 | `docs/hackathon-teknik-kilavuz.md` | Puanlama ve kurallar |

**Kullanma:** `data/seed/`, `data/out/`, `tools/`, `tools/output/` eski şemadadır. Yeni kodda veri kaynağı yalnızca `datav2/` JSON'larıdır.

---

## 1. Kapsam: Modül 1

| # | Özellik | Ne yapar | Senaryo | Veri |
|---|---|---|---|---|
| M1.1 | Bağlamlı sorun bildirimi | Ekrandaki "Sorun yaşıyorum" butonu Mercek'i ekran kodu, müşteri no, son `correlation_id` ve hata mesajıyla açar. Sohbette serbest metinden ekran, kurum, abone no, müşteri no çıkarılır. | A, B | screens, institutions, kibana_logs |
| M1.2 | Log inceleme ve örüntü analizi | İşlemin logunu bulur. Hataları kurum, ekran, hata no, numara uzunluğu ve zamana göre gruplar; olağan dışı örüntüyü gösterir. İş kuralını teknik hatadan ayırır. | A, B, C, F | kibana_logs, error_handling_rules |
| M1.3 | Çağrı zenginleştirme, departman ataması, ana kayıt | Çağrıyı yapılandırılmış kayda çevirir, kuralla departmana atar. Aynı sorundaki vakaları ana kayda bağlar. Temsilciye müşteriye söylenecek metni verir. | B, C | incidents, error_handling_rules, screen_departments, incident_categories, closure_codes |
| M1.4 | Çözüm eşleştirme, duyuru/e-posta araması, kod analizi | Hazır çözümlerle eşleştirir (eşik %75). Eşleşme yoksa duyurularda **ve işlenmemiş e-postalarda** arar, ilgili kodu okuyup düzeltme önerir. | B, C | solution_templates, announcements, inbound_emails, screens.files_json |
| M1.5 | "Bana göster" | Mercek'in önerdiği değerlerle ekranı Joyride turuyla doldurur. | A | — |
| M1.6 | Etki ölçümü | Önlenen çağrı, birleştirilen vaka, süre (iş değeri kanıtı). | A, B | prevented_calls, incidents (pilot `enriched_json`) |
| M1.7 | Günlük durum özeti | Sohbette "bugün en çok sorun yaşanan ekran". | F | kibana_logs |

**Kapsam dışı (Modül 2):** talep analizi, efor, takvim, scope_addons (D, E, G'nin talep kısmı). G'nin **proaktif bulgu** kartı (ASKİ) M1.4'te gösterilir.

---

## 2. Eski → yeni sözlük (rehberi okurken uygula)

| Rehberde (eski) | Yeni (datav2) |
|---|---|
| `banking_logs`, ECS alanları, `trace.id` | `kibana_logs`, Kibana alanları, **`correlation_id`** |
| İnternet Şube / Mobil kanal logları | **Yok.** 9 ekran çalışan ekranıdır; loglar yalnızca 1 Şube, 2 Çağrı Merkezi, 5 Servis, 6 İş Birimi kanalından gelir |
| `error_rules` (`error_code`) | **`error_handling_rules`** (`error_number` + `error_code`, `source`, `status`, öneri/onay akışı) |
| servis, `service_id`, `services`, `screen_services` | **departman**, `department_id`, `departments`, `screen_departments` |
| `solutions` (SOL-xxx, title/symptom/steps) | **`solution_templates`** (`solution_text` + `mercek_assigned_*`), kapanış: `closure_codes` |
| `ODMTFATR` (fatura ödeme) | **`ODMTTLMT`** (fatura talimat girişi; abone doğrulama) |
| `institution` (ad) | **`institution_code`** (SU01, GAZ02…) |
| `contacts` | **kaldırıldı** |
| `mercek_events`, `ai_usage` | **`prevented_calls`** (boş başlar); ai_usage yok |
| `requests` | `demands` (M2) |
| `branches` | **`org_units`** (S şube · G genel müdürlük · B bölge) |
| incidents 1.400 (90 gün) | **700** (CAG-1351…2050, 30 gün, her çağrı tek loga bağlı) |
| DUY-0412 İSKİ duyurusu tabloda | **Yok.** İSKİ duyurusu yalnızca e-posta: **EML-0022** (12.09) + **EML-0027** (26.09 hatırlatma), ikisi de işlenmemiş |
| C'de "23 açık İSKİ çağrısı" | **12** İSKİ çağrısı: 10'u SOL-005 "kullanıcı hatası" ile **yanlış** kapatılmış, 2'si açık |
| "B'de 47 istek, bağlı vaka 11→12" | **46** GAZ02 zaman aşımı (son 30 dk); CAG-2051 ve bağlı vakalar **demoda** oluşur |
| announcements `mercek_assigned_*` | önek yok + **`source`** (insan/mercek) |
| `firma: dalan` | **`fineart`** (`app_name`) |

---

## 3. Mimari ve Azure

```
Tarayıcı ─► mercek-web (Next.js 16, App Service) ─► mercek-api (FastAPI, App Service)
                                                     ├─► Azure SQL (mercekdb)       kayıt + tüm hesaplar
                                                     ├─► Azure AI Search            hibrit RAG (SQL'den indexer)
                                                     └─► Azure AI Foundry           chat + embedding
```

| Kaynak | Ad | Mercek'teki işi |
|---|---|---|
| App Service Plan (Linux, B1) | `mercek-plan` | İki uygulamayı barındırır |
| App Service | `mercek-web` | Next.js standalone, `node server.js` |
| App Service | `mercek-api` | FastAPI, `gunicorn -k uvicorn.workers.UvicornWorker`, sağlık: **`/api/health` → 200** |
| Azure SQL Database | `mercek-sql` / `mercekdb` | Katalog, loglar, çağrılar, duyurular, e-postalar; örüntü sorguları |
| Azure AI Search (**Basic**) | `mercek-search` | M1 indeksleri: **`solution_templates`, `announcements`, `inbound_emails`, `kibana_logs`** (4 indeks → Free'nin 3 indeks sınırı aşılır; M2'de `demands` eklenir). `kibana_logs` indeksi yalnızca Warning/Error logları içerir; `correlation_id` bilinmeyen sohbet sorularında ilgili logu bulmak için kullanılır, sayım ve örüntü SQL'de kalır |
| Azure AI Foundry | `mercek-foundry` | Deploy adları: **`chat`**, **`embedding`** |
| Application Insights | (opsiyonel) | İstek süreleri, hata izleme |

**Kimlik:** İdeal Managed Identity + RBAC; yetki yoksa anahtarlar **App Settings**'te. Repoya hiçbir anahtar girmez.

**App Settings (adlar; değerler `<PLACEHOLDER>`):** `SQL_SERVER`, `SQL_DATABASE`, `SEARCH_ENDPOINT`, `AZURE_OPENAI_ENDPOINT`, `CHAT_DEPLOYMENT=chat`, `EMBEDDING_DEPLOYMENT=embedding`, `CORS_ORIGINS`, `DEMO_MODE=true`, `MATCH_THRESHOLD=0.75`, `PATTERN_THRESHOLD_30D=50`. Yedek yolda: `SQL_USER`, `SQL_PASSWORD`, `SEARCH_API_KEY`, `AZURE_OPENAI_API_KEY`.

**Backend katmanları:** `api` (HTTP, Pydantic doğrulama) → `services` (iş mantığı, saf fonksiyonlar) → `repositories` (SQL, Search; parametreli sorgu) → `clients` (LLM). Prompt'lar `prompts/<ad>.md`.

---

## 4. "Hesabı kod yapar, AI açıklar"

| Kod (deterministik, test edilir) | AI (Foundry `chat`) |
|---|---|
| Log bulma, örüntü gruplama, eşikler (≥ %90 baskın, ≥ 5 kat artış, 30 günde ≥ 50) | Serbest metinden varlık çıkarma (`varlik-cikar`) |
| İş kuralı / teknik ayrımı (`error_handling_rules`) | Açıklama + müşteriye söylenecek metin (`log-acikla`) |
| Kredi hesabı (A), departman ataması, ana kayıt anahtarı | Çağrı zenginleştirme (`cagri-zenginlestir`, yalnızca yeni ana kayıtta) |
| Eşleşme skoru ve eşik (%75), duyuru tarih kontrolü | Çözüm uyarlama (`cozum-uyarla`), e-posta sınıflama (`eposta-siniflandir`), kod analizi (`kod-analiz`) |
| KVKK taraması (kişisel veri varsa Foundry'ye gitmez) | — |
| AI çıktısındaki sayıların girdide olduğunun kontrolü | — |

AI'a ham log değil, **kodun ürettiği özet** verilir. Kullanıcı metni ve log içeriği `<veri>…</veri>` içinde gider (prompt injection önlemi). Testlerde `FakeLLMClient`.

---

## 5. Fazlar (sırayla; her fazın sonunda build/lint/test yeşil)

| Faz | İş | Kabul |
|---|---|---|
| **F0** | Monorepo iskeleti (rebuild Faz 1) + `.github/workflows/ci-cd.yml` (lint → test → build → deploy, OIDC ya da publish profile) + `/api/health` | PR'da quality yeşil, main'de deploy + smoke test yeşil, CodeQL dosyası değişmemiş |
| **F1** | `db/schema.sql` (SCHEMA.md'den) + `scripts/load_datav2.py` (JSON → SQL, parametreli toplu yükleme; customers 40.005, loans 33.000, kibana_logs 10.555) + `search_text` hesaplanan kolonlar + change tracking | Satır sayıları README tablosuyla aynı |
| **F2** | AI Search: 4 indeks, SQL indexer + embedding (integrated vectorization ya da push betiği); `kibana_logs` için view `v_kibana_logs_search` (Warning/Error, `log_id` high water mark) | `solution_templates` 37 · `announcements` 18 · `inbound_emails` 34 · `kibana_logs` 2.002 belge |
| **F3** | `clients/llm.py` (`chat_json` şemalı + 1 yeniden deneme, `embed`), `prompts/` dosyaları, KVKK tarama/maskeleme yardımcısı | Birim testleri (FakeLLM) yeşil; KVKK taraması `datav2`'de yalnızca EML-0032'yi bulur |
| **F4** | Temel uygulama (rebuild Faz 2–4): demo kullanıcıları, 9 bankacılık ekranı (ekran kodu çubuğu), `POST /api/logs` → `kibana_logs` | Ekran işlemi SQL'de yeni log satırı üretir |
| **F5** | **M1.1** "Sorun yaşıyorum" + panel + `POST /api/mercek/assist`; serbest metin çıkarımı | A ve B bağlamla açılır |
| **F6** | **M1.2** `services/patterns.py` (`burst`, `breakdown`, `before_after`), `services/loan.py` (A) | §6'daki sayılar birim testinde |
| **F7** | **M1.3** kural eşleme, departman ataması, ana kayıt + bağlı vaka, `prevented_calls`, çağrı API'leri ve Mercek > Çağrılar sekmesi | B'de CAG-2051 + CAG-2051-NN; A'da prevented_calls +1 |
| **F8** | **M1.4** eşleştirme (eşik kodda), duyuru araması, **e-posta araması** (işlenmemiş kurum e-postaları), kod analizi (`files_json` haritası, path traversal korumalı), proaktif bulgu | B ≥ %90 eşleşme (SOL-031), C eşleşme yok → EML-0022 + kod konumu |
| **F9** | **M1.5** Joyride "Bana göster" (KRDTKULL, 330.000 TL / 36 ay) | Tur ekranı doldurur |
| **F10** | **M1.6** etki kartları, **M1.7** günlük özet | Sayılar SQL'den |
| **F11** | `scripts/demo_reset.py` (demo kayıtlarını siler: `log_time > 2026-10-17 09:00`, CAG-2051*, CAG-2052, prevented_calls) + `scripts/validate_scenarios.py` (§6 tablosu) | Doğrulama raporu tamamen yeşil |

---

## 6. Senaryo kabul kriterleri (veriyle doğrulanmış)

Veri sonu: **2026-10-17 09:00 (+03)**. Demo kayıtları bu andan sonra oluşur.

**A — KRDTKULL uygunluk (iş kuralı, çağrı önlenir)**
- Elif (10000004), gelir **38.000**, mevcut kredisi **yok**.
- 400.000 / 3 ay taksit **144.185,92**; 400.000 / 36 ay **22.754,17**; en yüksek tutar ≈ **334.004** → öneri **330.000** / 36 ay (**18.772,19**).
- Kural 1: KRDTKULL · 120218 AFFORDABILITY_EXCEEDED · business · `open_incident=0` → **prevented_calls +1**.
- Geçmişte kural 1 (120218) loglarından **90** çağrı açılmış (Mercek'in önleyebileceği; `incidents.stats.json` → `A_affordability_120218`).

**B — Başkentgaz zaman aşımı (kurum kaynaklı, ana kayıt)**
- 17.10 08:30–09:00: ODMTTLMT · GAZ02 · **110731** INSTITUTION_TIMEOUT · **46** log (şube 601 Kızılay 34, çağrı merkezi 12), 46 farklı müşteri; şube kayıtlarının 8'i `elif`, çağrı merkezi kayıtlarının 3'ü `zeynep` (08:33, 08:43, 08:54).
- 30 günlük olağan: GAZ02'de bugünden önce **hiç** zaman aşımı yok; ayrıca bilinen bakım penceresi (DUY-0398: 02–04) dışında → olağan dışı artış.
- Kural 7 `open_incident=1`, departman FATURA_ODEME → **CAG-2051** (öncelik 2) + bağlı vakalar **CAG-2051-NN** (kapanış MUKERRER_CAGRI / ANA_KAYDA_BAGLANDI).
- Eşleşme **SOL-031** (DIS_KURUM_KAYNAKLI / KURUM_SERVIS_KESINTISI); "benzer geçmiş olay" = SOL-031 ile kapanmış **6** çağrı.

**C — İSKİ 13 hane (kural "çağrı açma" der, Mercek örüntüden aşar)**
- ODMTTLMT · **110412** SUBSCRIBER_NO_INVALID · kural 8 `open_incident=0`.
- 01.10 öncesi **0**; sonrası **412** (İSKİ **400 = %97,1**, hepsi **13 hane**; 12 ASKİ, 5 hane), İSKİ'de **393** farklı müşteri. Günlük ~24; 30 günde ≥ 50 eşiği **03.10**'da aşılmış.
- Mercek örüntü eşiğiyle kuralı aşar → **CAG-2052** açar.
- Hazır çözüm: SOL-005 ("kullanıcı hatası") **yanıltıcı**; aynı şablonla kapatılmış **10** İSKİ çağrısı + **2** açık (pilottaki Mercek de SOL-005 önermiş → örüntü taramasıyla kendini düzeltir).
- Kök neden: ortak kutudaki **EML-0022** (12.09) ve **EML-0027** (26.09), ikisi `yeni` (işlenmemiş).
- Kod: ODMTTLMT abone no kuralı `6–12 hane` (frontend form + backend doğrulama); kalıcı öneri: hane sayısı **PRMTGENL**'de kurum bazlı parametre.
- Proaktif bulgu (G): **EML-0031** ASKİ, 01.01.2027'den itibaren 13 hane.

**F — Günün en sorunlu ekranı:** 17.10'da ODMTTLMT **48** uyarı/hata (B'nin 46'sı dahil); diğer ekranlarda yok.

**Mercek pilotu (M1.6 için):** 15–16.10'da **62** çağrıda `enriched_json` dolu; kapanan **28**'inde öneri aynen kullanılmış ve çözüm süresi yarıya inmiş.

---

## 7. Kesin kurallar

- `.github/workflows/` altındaki **organizasyon CodeQL dosyasına dokunma**; ikinci CodeQL yok; `.github/` ignore edilmez.
- Repoya **secret, API key, şifre, connection string, token yazma**. Örneklerde `<PLACEHOLDER>`.
- **Gerçek kişi/kurum verisi yok**; veride banka adı geçmez (firma: `fineart`). Kurum adları (İSKİ, Başkentgaz…) kullanılabilir.
- **KVKK:** Foundry'ye giden her metin önce taranır (TCKN algoritması, telefon, `@ornek.test` dışı e-posta, IBAN, Luhn kart no, kişi adı listesi, IP/makine adı). Bulgu varsa gönderilmez.
- Değişiklikler **feature branch + PR**; doğrudan main'e push yok. Son pipeline **success** olmalı.
- Güvenli kod: girdi doğrulama, parametreli sorgu, çıktı encoding; bağımlılık sürümleri sabit, bilinen açığı olan paket yok.
- Her iş mantığına birim testi; AI çağrıları mock'lanır.
- **Maliyet:** kısa yanıt; basit işte ucuz model; büyük veri ürettirme, betik yazdır.
- Yanıtlar ve arayüz metinleri Türkçe; kod tanımlayıcıları İngilizce.
- Commit sonu: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (+ oturumun `Claude-Session:` satırı).

---

## 8. Açık işler (ayrıca takip edilir)

- ⏸ `scope_addons` şeması (M2'de gerekir).
- 📎 Maliyet Tahminleme Formu (Excel) — kullanıcı detay verecek.
- §5 büyük güncellemenin M1 dışındaki kısımları (M2 kodu, sunum, ZtHackathonStudy reposu ve proje senkronu).

---

## 9. Yeni oturuma ilk mesaj (kopyala-yapıştır)

> Mercek Modül 1'i geliştireceğiz. `datav2/M1-GELISTIRME-BASLANGIC.md` dosyasını baştan sona, ardından §0'daki okuma listesini sırayla oku. Önce **F0**'dan başla: repo iskeleti, CI/CD workflow ve `/api/health`. Her fazın sonunda build, lint ve test sonuçlarını göster; kabul kriteri karşılanmadan sonraki faza geçme. Karar gereken noktaları numaralı sor. CodeQL dosyasına dokunma, repoya secret yazma.
