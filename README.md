# Mercek — Doküman Rehberi (Buradan Başlayın)

**Takım:** AI Overflow · **Proje:** Mercek · **Slogan:** "Soruna odaklanır, çözümü netleştirir."
**Hackathon:** Ziraat Teknoloji Yapay Zeka Hackathonu, 16–17 Ekim 2026, Tema 2

Bu doküman, hackathon boyunca kullanacağımız tüm dokümanları (hepsi bu repoda, `docs/` ve `presentation/` altında) **hangi sırayla, ne zaman ve ne için** açacağımızı anlatır. Hepsini baştan sona okumak gerekmiyor; aşağıdaki sırayı izleyin.

![Mercek doküman haritası](docs/img/mercek-dokuman-haritasi.png)

---

## Sentetik veri: ne var, kaç adet, nerede

Tüm veri sentetiktir (gerçek müşteri verisi yok); seed 42, veri sonu 17.10.2026 09:00. Ayrıntılı dağılımlar: [`docs/mercek-sentetik-veri-sayilari.md`](docs/mercek-sentetik-veri-sayilari.md).

| Veri | Adet | Dosya |
|---|---|---|
| Ekran · servis · ekran–servis ilişkisi | 20 · 7 · 30 | [`data/seed/catalog.json`](data/seed/catalog.json) |
| Hata–servis kuralı · servis takvimi · kapsam eki | 17 · 11 · 5 | `catalog.json` |
| Fatura kurumu · şube · çağrı kategorisi | 15 · 5 · 6 (30 alt kategori) | `catalog.json` |
| Demo kullanıcısı · etkilenen il (E) | 5 · 3 | `catalog.json` |
| Kurum duyurusu | 20 | [`data/seed/announcements.json`](data/seed/announcements.json) |
| Kesin senaryo metinleri | 1 çözüm · 8 talep · 5 çağrı notu | [`data/seed/fixed_texts.json`](data/seed/fixed_texts.json) |
| Üretilmiş metinler | 465 not · 36 çözüm · 87 talep · 30 taslak | [`data/seed/texts.json`](data/seed/texts.json) |
| Ham işlem logu | 10.000 | [`tools/output/dalan-banking-logs.ndjson`](tools/output) |
| Senaryolu işlem logu (ham + 415 senaryo kaydı) | **10.415** | [`tools/output/mercek-logs.ndjson`](tools/output) |
| B demo penceresi (Başkentgaz zaman aşımı) | 46 | `tools/output/mercek-demo-window.ndjson` |
| Müşteri | **40.000** | [`data/out/customers.csv`](data/out) |
| Kredi | **33.000** (26.000 müşteride) | `data/out/loans.csv` |
| Müşteri teması | **8.322** | `data/out/contacts.csv` |
| Teknoloji çağrısı (CAG-0651…2050) | **1.400** | `data/out/incidents.csv` |
| Çözüm bilgi bankası | 37 | `data/out/solutions.csv` |
| Geçmiş talep (TLP-0500…1037) | 95 | `data/out/requests.csv` |
| Değerlendirme seti | 30 (10 / 10 / 10) | [`data/seed/eval_cases.json`](data/seed/eval_cases.json) |
| Hepsi yüklü veritabanı (15 tablo) | ≈93.400 satır | `data/out/mercek.db` (SQLite) |
| AI Search indeksleri (SQL'den otomatik eşitlenir) | 37 · 95 · 20 belge | `load_all.py --search` · [eşitleme](docs/mercek-sql-search-esitleme.md) |

**Senaryo rakamları:** A Elif geliri 38.000 · B 46 (+Mehmet = 47) log, CAG-2051 + 11 bağlı vaka · C 412 hata, İSKİ 400, 187 müşteri, 23 çağrı · D hedef 2.340, temas 71 / 64 / 51 · E 4.870 müşteri, 6.215 kredi, 612 gecikmede, 497 temas (418 erteleme). Kontrol: `python3 tools/mercek_data/validate_scenarios.py --sqlite data/out/mercek.db --now 2026-10-17T09:00:00+03:00`.

---

## 1. Dokümanlar bir bakışta

| # | Doküman | Ne anlatır | Kim için |
|---|---|---|---|
| 1 | [`docs/hackathon-teknik-kilavuz.md`](docs/hackathon-teknik-kilavuz.md) | Resmi kılavuzun özeti: ortam ve hesaplar, AstreAI puanlaması (%30), jüri kriterleri (%70), sunum kuralları, teslim kontrol listesi | Herkes |
| 2 | [`docs/mercek-kapsam.md`](docs/mercek-kapsam.md) | Mercek nedir, hedef kullanıcılar, iki modül (M1.1–M1.7, M2.1–M2.6) ve senaryo eşlemesi, MoSCoW, sunum ve demo yaklaşımı, teknik kararlar, zaman planı | Herkes |
| 3 | [`docs/mercek-demo-senaryo-onerileri.md`](docs/mercek-demo-senaryo-onerileri.md) | **Altı senaryo (A–F):** önce yönetici özetleri, sonra her senaryonun akışı, rakamları ve kanıtladığı özellikler; demo kurgusu ve iş değeri | Herkes |
| 4 | [`docs/mercek-is-plani.md`](docs/mercek-is-plani.md) | Mimari, **19 maddelik sorumluluk listesi**, görev dökümü (A, V, M1, M2, Q) ve kabul kriterleri, zaman × odak, **sunum akışı ve 12:00 canlı demo kararı**, iş değeri, soru-cevap | Herkes |
| 5 | [`docs/COPILOT_REBUILD_GUIDE.md`](docs/COPILOT_REBUILD_GUIDE.md) | Temel uygulamanın faz faz kurulumu: Next.js 16 + FastAPI, dashboard, sahte giriş, 5 işlem ekranı, log üretici, Joyride | Geliştiriciler |
| 6 | [`docs/mercek-uygulama-rehberi.md`](docs/mercek-uygulama-rehberi.md) | Her görevin **nasıl** yapılacağı: Azure servisleri ve puan bağlantısı, iki App Service, kimlik doğrulama yedek yolları, Mercek akışları | Geliştiriciler |
| 7 | [`docs/mercek-copilot-promptlari.md`](docs/mercek-copilot-promptlari.md) | Her görev için Copilot'a yapıştırılacak hazır prompt, model sınıfı (ucuz/orta), ortak sözleşmeler (`contracts.md`) | Geliştiriciler |
| 8 | [`.github/copilot-instructions.md`](.github/copilot-instructions.md) | Copilot'un her istekte otomatik okuduğu kısa kural dosyası (güvenlik, CodeQL yasağı, teknoloji, test, maliyet) | Copilot |
| 9 | [`docs/mercek-sentetik-veri-plani.md`](docs/mercek-sentetik-veri-plani.md) | Hangi veriler, ne kadar, neden; her senaryonun veride taşıması gerekenler | Veri sorumluları, analist |
| 10 | [`docs/mercek-sentetik-veri-uretimi.md`](docs/mercek-sentetik-veri-uretimi.md) | Verinin **nasıl ve hangi değerlerle** üretileceği: şema, kataloglar, senaryo rakamları, yasak kurallar, betikler, Foundry prompt'ları, demo sıfırlama, doğrulama tablosu | Veri sorumluları |
| 11 | [`presentation/Mercek_AI_Overflow_Sunum.pptx`](presentation/Mercek_AI_Overflow_Sunum.pptx) ([PDF](presentation/Mercek_AI_Overflow_Sunum.pdf)) | Ziraat Teknoloji sunum şablonuyla 11 slaytlık sunum: altı senaryo tek slaytta, canlı demo dört sahne, konuşmacı notları, taslak ekranlar | Sunum sorumlusu, herkes |
| 12 | [`presentation/build_deck.py`](presentation/build_deck.py), [`presentation/sablon/`](presentation/sablon), [`presentation/mockups/`](presentation/mockups) | Sunumu şablondan yeniden üreten betik, kurum şablonu, taslak ekranların HTML kaynağı | Sunum sorumlusu |
| 13 | [`docs/mercek-takim-anlatim-cumleleri.md`](docs/mercek-takim-anlatim-cumleleri.md) | Her dokümanın ana fikri tek cümlede ve akılda kalacak rakamlar | Toplantıyı yöneten, herkes |
| 14 | [`docs/mercek-sentetik-veri-kaynaklari.md`](docs/mercek-sentetik-veri-kaynaklari.md) | Her verinin kaynağı: **elle** yazılanlar, **betikle** üretilenler (betik açıklamalarıyla), **uygulamanın** ürettikleri; durum ve çalıştırma sırası | Veri sorumluları, geliştiriciler |
| 14b | [`docs/mercek-sql-search-esitleme.md`](docs/mercek-sql-search-esitleme.md) | Azure SQL → AI Search otomatik eşitleme: temel bilgiler, kurulum ve yetki adımları, demo akışı, sorun giderme | Veri ve Search sorumluları |
| 15 | [`data/seed/`](data/seed), [`tools/`](tools) | Hazır veri ve betikler: V2 katalog ve duyurular, V3 log üretici ve senaryo enjeksiyonu (testleriyle) | Veri sorumluları |

**Dokümanlar arası ilişki**

```
kılavuz (kurallar)
   └─ kapsam (ne yapıyoruz)
        └─ demo senaryoları (neyi kanıtlayacağız)
             └─ iş planı (kim, ne zaman, sunum)
                  ├─ rebuild rehberi (temel uygulama)
                  ├─ uygulama rehberi (nasıl) ──► Copilot prompt'ları (Copilot'a ne yazılır)
                  ├─ veri planı (hangi veri)  ──► veri üretim rehberi (hangi değerlerle) ──► veri kaynakları (elle / betik / uygulama)
                  └─ sunum taslağı (jüriye nasıl anlatılır)
```

Görev kodları (A1, V3, M1.2-b, Q9 …) ve sorumluluk numaraları ([1]–[19]) tüm dokümanlarda aynıdır. Bir görevi bir dokümanda bulduğunuzda diğerlerinde aynı kodla arayın.

---

## 2. 1. gün — 16 Ekim Cuma

| Saat | Ne yapılacak | Doküman |
|---|---|---|
| 08:00–10:30 | Kayıt ve açılış (kod yok). Anlatım cümleleriyle kısa takım toplantısı; senaryoları ve kapsamı birlikte geçin. VDI, Azure Portal ve `_ziraathc` GitHub girişlerini deneyin | Anlatım cümleleri, Senaryolar, Kılavuz |
| 10:30–10:45 | **Sorumluluk seçimi** (herkes 3–4 madde; 1, 4, 17, 18 boş kalamaz). Azure'da rol ataması ve uygulama kaydı yetkisi var mı? Yoksa yedek yol | İş planı §2, Uygulama rehberi §0.3 |
| 10:45–13:30 | **Altyapı:** rebuild Faz 1 + A1-ek, `docs/contracts.md`, CI/CD, Azure kaynakları, rebuild Faz 2–4. **Veri:** V1–V8 | Prompt'lar §1, A, V · Rebuild rehberi · Veri üretim rehberi |
| 13:30 | **Kontrol:** pipeline yeşil, iki App Service ayakta, `/api/health` 200, Foundry yanıt veriyor, `validate_scenarios.py` yeşil | Veri üretim rehberi §12 |
| 14:30–19:00 | **A ve B** uçtan uca (M1.1–M1.3, M1.4-a/b), M2.1, M2.4 | İş planı §3 · Uygulama rehberi · Prompt'lar |
| 20:00–gece | **D ve C** uçtan uca (M2.2, M2.5, M2.6, M1.4-c/d), senaryo testleri | Aynı + İş planı Q2 |

## 3. 2. gün — 17 Ekim Cumartesi

| Saat | Ne yapılacak | Doküman |
|---|---|---|
| 09:30–12:00 | Should ve Could: Joyride ve "Bana göster", ölçüm sayaçları, E (kapasite çatışması), F. Her senaryo için ekran görüntüsü ve kısa video | İş planı §3, Q7 · Prompt'lar |
| **12:00** | **Kod dondurma** ve **canlı demo kararı**: hangi senaryolar canlı, hangileri görüntü/video | İş planı §5.3 · Uygulama rehberi Q6, Q9 |
| **13:00–14:00** | **Teknik değerlendirme (AstreAI)**: bu saatten önce her şey main'de ve yeşil | Kılavuz |
| 12:00–14:45 | Sunumu tamamlama (takım bilgileri, gerçek ekran görüntüleri, senaryo slaytındaki CANLI/KAYIT etiketleri, bağlantılar) ve iki prova | Sunum notları · İş planı §5 |
| 15:00–17:20 | Sunum (5 dakika) | Sunum konuşmacı notları |

**Gün boyunca:** Her 2 saatte bir 5 dakikalık durum kontrolü ve Copilot harcama takibi (hedef < 20 $). İş planı Q5, uygulama rehberi §0.4.

### Copilot ile çalışırken

1. Görevin kodunu bulun (ör. M1.2-b).
2. **Uygulama rehberi**nden ne yapılacağını okuyun.
3. **Prompt kütüphanesi**nden aynı kodlu prompt'u kopyalayın, `<...>` yerlerini doldurun. Temel uygulama fazlarında rebuild rehberindeki prompt'u kullanın.
4. Belirtilen model sınıfını seçin, yeni bir Chat oturumu açın.
5. Diff'i okuyun, testleri çalıştırın, PR açın; PR'ı başka biri onaylasın.

---

## 4. Sunum öncesi son kontrol (2. gün 14:30)

- [ ] Kapak ve takım slaytı dolu (ad, birim, rol)
- [ ] Senaryo slaytında CANLI / KAYIT etiketleri 12:00 kararına göre güncel
- [ ] Taslak görseller gerçek ekran görüntüleriyle değişti ("TASLAK GÖRSEL" etiketi kalmadı)
- [ ] Mimari slaytında yalnızca gerçekten çalışan Azure servisleri var
- [ ] "Tamamlanan" listesi gerçek durumu gösteriyor
- [ ] Ekler slaytında repo, web uygulaması ve video bağlantıları var
- [ ] Hiçbir görselde şifre, anahtar, connection string, e-posta görünmüyor
- [ ] `demo_reset.py --now` çalıştırıldı; tarayıcı sekmeleri (Elif, Mehmet, Zeynep/Kerem, Fatma) açık
- [ ] Senaryo videoları sunum bilgisayarında yerel olarak var

---

## 5. Hangi dosyalar takım reposuna kopyalanacak?

| Dosya | Hedef konum |
|---|---|
| [`docs/hackathon-teknik-kilavuz.md`](docs/hackathon-teknik-kilavuz.md) | `docs/` |
| [`docs/COPILOT_REBUILD_GUIDE.md`](docs/COPILOT_REBUILD_GUIDE.md) | `docs/` |
| [`.github/copilot-instructions.md`](.github/copilot-instructions.md) | `.github/` (dosya adı değişmeden) |
| Prompt kütüphanesi §1 "Ortak sözleşmeler" | `docs/contracts.md` |
| Veri üretim rehberi §3 tabloları | `data/seed/catalog.json`, `announcements.json` (V2 prompt'uyla) |
| Veri üretim rehberi §9 prompt'ları | `prompts/gen-*.md` (V4 prompt'uyla) |

Kapsam, senaryolar, iş planı, uygulama rehberi ve prompt kütüphanesi **ürün reposuna konmaz**; takımın çalışma dokümanıdır. Sunum dosyası teslim için ayrıca yüklenir.

---

## 6. Hackathon sonrası

| Ne | Doküman |
|---|---|
| Takım retrospektifi: kapsam, sorumluluk modeli, Copilot kullanımı, maliyet | İş planı, Kapsam |
| Jüri ve AstreAI geri bildirimlerinin not edilmesi; "canlıya geçiş" maddelerinin güncellenmesi | Sunum 10. slayt, İş planı soru-cevap |
| Azure kaynaklarının organizasyon talimatına göre kapatılması / bırakılması | Kılavuz |
