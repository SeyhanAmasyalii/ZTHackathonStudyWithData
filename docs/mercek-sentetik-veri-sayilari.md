# Mercek — Sentetik Veri Sayıları

Bu doküman, üretilen tüm sentetik verinin adetlerini konu konu listeler. Değerler yerel veritabanındaki (`load_all.py --sqlite`) gerçek üretim çıktısından alınmıştır (seed 42, veri sonu 17.10.2026 09:00).

Nereden geldiği: `mercek-sentetik-veri-kaynaklari.md` · Değerlerin ayrıntısı: `mercek-sentetik-veri-uretimi.md` · Kontrol: `python3 tools/mercek_data/validate_scenarios.py`

---

## 1. Katalog (elle hazırlandı · `data/seed/catalog.json`)

| Veri | Adet |
|---|---|
| Ekran | 20 (5'i simüle, 15'i yalnızca katalogda; KRDTERTL bilerek yok) |
| Servis | 7 |
| Ekran–servis ilişkisi | 30 |
| Hata–servis kuralı | 17 |
| Servis takvimi satırı | 11 |
| Kapsam eki | 5 (ADD-SMS, ADD-PROAKTIF-SMS dahil) |
| Fatura kurumu | 15 |
| Şube | 5 |
| Çağrı kategorisi | 6 kategori, 32 alt kategori (2'si yalnızca teknoloji çağrılarında: yetersiz bakiye, başvuru tamamlanamadı) |
| Demo kullanıcısı | 5 (Elif, Zeynep, Kerem, Fatma, Hakan) |
| Etkilenen il (E) | 3 (arayüzde ve sunumda gösterilmez) |
| Kurum duyurusu (`announcements.json`) | 20 (kritik olanlar DUY-0412 İSKİ ve DUY-0419 ASKİ) |

## 2. Metinler

| Veri | Adet |
|---|---|
| Kesin metinler (`fixed_texts.json`) | SOL-031 · D için 5, E için 3 benzer talep · C için 5 çağrı notu |
| Şablonla üretilen metinler (`texts.json`) | 465 çağrı notu · 36 çözüm · 87 talep · 30 değerlendirme taslağı |

Foundry açılınca `generate_texts.py --force` ile şablon metinlerin yerine model metinleri gelir; adetler değişmez.

## 3. İşlem logları (`banking_logs`)

| Veri | Adet |
|---|---|
| Toplam seed log | **10.415** (16.09 → 17.10 09:00) |
| Senaryo ekleri | 415 = C'de 400 İSKİ + 12 diğer kurum abone no hatası + Mehmet'in 3 ödemesi |
| Ekran dağılımı | ODMTFATR 3.862 · HSPTVDSZ 1.774 · KRTTBASV 1.668 · KRDTKULL 1.619 · MUSTGUNC 1.492 |
| Seviye dağılımı | info 8.881 · warn 1.306 · error 228 |
| Loglardaki müşteri | 784 (hepsi portföyde de var) |
| C (01.10 sonrası abone no hatası) | 412 · İSKİ 400 (%97,1, hepsi 13 hane) · 187 farklı müşteri · 01.10 öncesi İSKİ 13 hane: 0 |
| B demo penceresi (`demo_reset.py`) | 46 log; Mehmet'in canlı isteği 47. olur |

## 4. Müşteri ve kredi portföyü

| Veri | Adet |
|---|---|
| Müşteri | **40.000** (Bireysel 28.059 · Premium 9.923 · Özel Bankacılık 2.018) |
| Kredi | **33.000** (normal 31.438 · gecikmede 1.562) |
| Aktif kredili müşteri | 26.000 |
| D hedef grubu | 2.340 · e-posta izni 1.357 · SMS izni 1.895 · en az biri 2.083 |
| E etkilenen bölge | 4.870 müşteri · 6.215 kredi · 612 gecikmede · 37 adres değişikliği |

## 5. Müşteri temasları (`contacts`)

| Veri | Adet |
|---|---|
| Toplam | **8.322** (çağrı merkezi 6.235 · şube 2.087) |
| Kategori | Kredi 2.344 · Fatura ödeme 1.817 · Kart 1.242 · Hesap 1.067 · Müşteri bilgileri 930 · Diğer 922 |
| D (son 90 gün, Kredi) | 71 hatırlatma + 64 faiz itirazı + 51 taksit sorusu = 186 |
| E (bölge) | 12.10 sonrası 497 (418'i erteleme) · önceki 30 günde günlük 16 |

## 6. Teknoloji çağrıları ve çözümler

| Veri | Adet |
|---|---|
| Çağrı (`incidents`) | **1.400** (CAG-0651…CAG-2050 · kapalı 1.357 · açık 43) |
| Kategori | Fatura ödeme 361 · Kredi 319 · Kart 281 · Hesap 257 · Müşteri bilgileri 182 (alt kategori hata koduyla tutarlı) |
| B geçmişi | SOL-031 ile kapanmış 6 olay |
| C | 23 açık İSKİ çağrısı |
| Demo (`demo_reset.py`) | CAG-2051 + 11 bağlı vaka (CAG-2051-01…-11) |
| Çözüm bilgi bankası (`solutions`) | **37** (SOL-031 dahil) |

## 7. Talepler ve değerlendirme

| Veri | Adet |
|---|---|
| Geçmiş talep (`requests`) | **95** (TLP-0500…1037 · mevcut ekran değişikliği 51 · yeni ekran 19 · batch 12 · karma 13) |
| Kesin benzer talepler | D için 5 (0871, 0915, 0962, 1004, 1019) · E için 3 (0588, 0712, 0846) |
| Demo (`demo_reset.py --with-d-plan`) | TLP-1043 (D'nin planı, 20 a/g, 09.11–04.12) |
| Değerlendirme seti (`eval_cases.json`) | **30** (10 eşleşmeli, 10 eşleşmesiz, 10 talep) · indekse yüklenmez |

## 8. AI Search indeksleri

| İndeks | Belge |
|---|---|
| `solutions` | 37 |
| `requests` | 95 |
| `announcements` | 20 |

## 9. Uygulamanın demo sırasında ürettikleri (betikle üretilmez)

| Veri | Adet |
|---|---|
| Canlı log | A: Elif'in uyarısı · B: Mehmet'in 47. isteği · C: 13 haneli giriş |
| Canlı çağrı | B: CAG-2051-12 (bağlı vaka 11 → 12) · C: yeni ana kayıt CAG-2052 |
| Canlı talep | D: TLP-1043 · E: TLP-1044 |
| Mercek ölçümü (`mercek_events`) | Her analiz, önlenen çağrı ve bağlanan vaka için bir satır |

---

**Toplam:** yaklaşık **93.400 SQL satırı** ve **152 aranabilir belge**.
