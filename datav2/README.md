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
