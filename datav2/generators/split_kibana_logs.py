"""kibana_logs.json'u her biri 4 milyon karakterin altında kalan parçalara böler.

Çıktı: datav2/kibana_logs_partNN.json (her parça geçerli bir JSON dizisi, log_id sırasıyla).
Çalıştırma (repo kökünden, kibana_logs.py'den sonra):  python datav2/generators/split_kibana_logs.py
"""

from __future__ import annotations

import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[1]
LIMIT = 4_000_000
MARGIN = 10_000


def record_length(record: dict) -> int:
    text = json.dumps(record, ensure_ascii=False, indent=2)
    return len(text) + 2 * (text.count("\n") + 1) + 2  # dizi içi ek girinti + ",\n"


def main() -> None:
    records = json.loads((DATA / "kibana_logs.json").read_text(encoding="utf-8"))
    parts: list[list[dict]] = []
    current: list[dict] = []
    size = 4
    for record in records:
        length = record_length(record)
        if current and size + length > LIMIT - MARGIN:
            parts.append(current)
            current, size = [], 4
        current.append(record)
        size += length
    parts.append(current)

    for old in DATA.glob("kibana_logs_part*.json"):
        old.unlink()
    for n, part in enumerate(parts, start=1):
        text = json.dumps(part, ensure_ascii=False, indent=2) + "\n"
        assert len(text) < LIMIT, (n, len(text))
        (DATA / f"kibana_logs_part{n:02d}.json").write_text(text, encoding="utf-8")
        print(f"kibana_logs_part{n:02d}.json", len(part), part[0]["log_id"], part[-1]["log_id"], len(text))


if __name__ == "__main__":
    main()
