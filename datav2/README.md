# datav2 — Nihai şemalara göre sentetik veri (JSON)

Şema gözden geçirmesinde kesinleşen tablolar için, demo senaryolarını (A–G) kapsayan sentetik veriler. Nihai şema yapıları: [`SCHEMA.md`](SCHEMA.md) · Yeni oturuma devir: [`HANDOFF.md`](HANDOFF.md).

Tablolar tek tek, onaylandıkça eklenir. Bu klasördeki veriler henüz betiklere ve veritabanına bağlanmadı; tüm şemalar netleşince tek seferde işlenecek.

| Dosya | Tablo | Kayıt | Durum |
|---|---|---|---|
| `screens.json` | screens | 9 | ✅ onaylandı |
| `departments.json` | departments | 6 | ✅ onaylandı |
| `screen_departments.json` | screen_departments | 23 | ✅ onaylandı |
| `error_handling_rules.json` | error_handling_rules | 20 (tohum) | ✅ onaylandı · C: kural 8 'çağrı açma' der, Mercek örüntüden (ekran+kurum+hata, 30 günde ≥ 50) aşar |
| `closure_codes.json` | closure_codes | 62 (20 ana + 42 alt) | ✅ onaylandı |
| `org_units.json` | org_units | 19 (5 S + 4 B + 10 G) | ✅ onaylandı · demo birimleri: Elif 601, Zeynep 9009, Kerem 9010, Fatma 9001, Hakan 9002 |
| `institutions.json` | institutions | 16 (15 fatura + VRG01 Gelir İdaresi) | ✅ onaylandı · B: GAZ02 · C: SU01 · G: SU02; abone no uzunluğu bilerek yok |
| `institution_screens.json` | institution_screens | 16 (tüm kurumlar → ODMTTLMT / talimat) | ✅ onaylandı · VRG01: MTV vb. vergi talimatı; usage enum: odeme/sorgu/gecmis/talimat |
| `channels.json` | channels | 6 | ✅ onaylandı · 5 Servis → çağrı açılmaz · 6 İş Birimi (G birimleri, branch_type G) → is_birimi · dijitalde (3, 4) çağrıyı Mercek açar, reporter 9999 |
| `incident_categories.json` | incident_categories | 19 (7 kategori) | ✅ onaylandı · screen_code kolonu eklendi (Diğer: `*`) · "Fatura ödeme" → "Fatura talimatı" · temas ve ekranı olmayan alt kategoriler çıkarıldı |
| `customers.json` | customers | 40.005 (40.000 + 5 demo) | ✅ onaylandı · üretici `generators/customers.py` · sayılar `customers.stats.json` (D 2.340/3.249/%42 · E 4.870/3.973/4.516 · 37 adres değişikliği) |
| `loans.json` | loans | 33.000 | ✅ onaylandı · üretici `generators/loans.py` · collection_account kaldırıldı · demo: Zeynep KRD00006571 gecikmede, Kerem KRD00006218 normal, Elif kredisiz (A) |
| `kibana_logs.json` | kibana_logs | 10.555 (10.000 gündelik + B 46 + C 412 + E 37 + telefon 60) | ✅ onaylandı · üretici `generators/kibana_logs.py` · sayılar `kibana_logs.stats.json` · C: 01.10 öncesi 0, sonrası 412 (%97,1 İSKİ, hepsi 13 hane) |
| `solution_templates.json` | solution_templates | 37 | ✅ onaylandı · SOL-031 = B (kurum kesintisi) · SOL-005 C için yanıltıcı "kullanıcı hatası" şablonu · SOL-027 telefon biçimi (kuralsız) · teknik ve PRMTGENL şablonlarında department_id boş |
