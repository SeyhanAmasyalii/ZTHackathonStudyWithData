"""department_calendar.json üreticisi.

Kaynak: demands.py'nin yazdığı `_calendar_rows.json` (takvim talepleri TLP-1021…1031). Her satır bir talebe
bağlıdır; talep dışı satır ve `note` kolonu yoktur. Kapasite günde 1 a/g; aynı gün toplam %100 → dolu.
Doğrulanan takvim sonuçları: D 09.11→02.12 / 09.11→04.12 · E 19.10→30.10 / 19.10→02.11 / 09.11→20.11 ·
G (FATURA_ODEME, ~4 a/g) 19.10→23.10.

Çalıştırma (repo kökünden, demands.py'den sonra):  python datav2/generators/department_calendar.py
"""

from __future__ import annotations

import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[1]


def main() -> None:
    rows = json.loads((DATA / "generators" / "_calendar_rows.json").read_text(encoding="utf-8"))
    records = [{"calendar_id": f"CAL-{n:04d}", **row} for n, row in enumerate(rows, start=1)]
    records = [{k: r[k] for k in ("calendar_id", "department_id", "demand_id", "date_from", "date_to", "allocation_pct")}
               for r in records]
    (DATA / "department_calendar.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n",
                                                   encoding="utf-8")
    for r in records:
        print(r["calendar_id"], r["demand_id"], r["department_id"].ljust(18), r["date_from"], r["date_to"], r["allocation_pct"])


if __name__ == "__main__":
    main()
