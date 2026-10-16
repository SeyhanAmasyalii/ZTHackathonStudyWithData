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
