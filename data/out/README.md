# data/out — Üretilmiş veri (commit'lenmiş)

Bu klasördeki dosyalar betiklerle üretilmiştir (seed 42, veri sonu 2026-10-17 09:00 +03:00) ve hazır olsun diye repoya eklenmiştir. Yeniden üretmek birebir aynı sonucu verir (`tools/README.md`).

| Dosya | İçerik | Üreten |
|---|---|---|
| `customers.csv` | 40.000 müşteri | `generate_portfolio.py` |
| `loans.csv` | 33.000 kredi | `generate_portfolio.py` |
| `contacts.csv` | 8.322 müşteri teması | `generate_incidents.py` |
| `incidents.csv` | 1.400 teknoloji çağrısı (CAG-0651…2050) | `generate_incidents.py` |
| `solutions.csv` | 37 çözüm | `generate_incidents.py` |
| `requests.csv` | 95 geçmiş talep | `generate_requests.py` |
| `mercek.db` | Tümünün yüklendiği SQLite veritabanı (`load_all.py --sqlite`) + `demo_reset.py --now 2026-10-17T09:00:00+03:00 --with-d-plan` uygulanmış hali | `load_all.py`, `demo_reset.py` |

`mercek.db` içindeki B penceresi (46 log, CAG-2051, 11 bağlı vaka) 17.10 09:00'a göredir; demo öncesi `demo_reset.py` yeniden çalıştırılır. Kişisel veri gerçek değildir (e-postalar `@ornek.test`, IP'ler belgeleme aralığında).
