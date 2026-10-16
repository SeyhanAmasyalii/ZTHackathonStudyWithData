# tools/output — Üretilmiş loglar (commit'lenmiş)

| Dosya | İçerik | Üreten |
|---|---|---|
| `dalan-banking-logs.ndjson` | 10.000 ham işlem logu (ECS) | `generate_banking_logs.py --seed 42 --end 2026-10-17T09:00:00+03:00` |
| `dalan-banking-logs-template.json` | Elasticsearch index template | `generate_banking_logs.py --write-template` |
| `mercek-logs.ndjson` | 10.415 log: ham loglar + senaryo kayıtları (C: 412 abone no hatası, Mehmet'in 3 ödemesi) | `inject_log_scenarios.py` |
| `mercek-demo-window.ndjson` | B'nin 46 Başkentgaz zaman aşımı logu (17.10 09:00'a göre örnek) | `inject_log_scenarios.py --demo-window-now` |
