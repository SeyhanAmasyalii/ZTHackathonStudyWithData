"""datav2 verisinden db/schema.sql üretir. Veri (kolon/tablo) değişince çalıştırın.

Kullanım (repo kökünden):  python scripts/build_schema.py
"""

from pathlib import Path

from datav2_tables import build_schema, read_tables

SCHEMA = Path(__file__).resolve().parents[1] / "db" / "schema.sql"


def main() -> None:
    tables = read_tables()
    SCHEMA.write_text(build_schema(tables), encoding="utf-8", newline="\n")
    print(f"✓ {SCHEMA.relative_to(SCHEMA.parents[1])}: {len(tables)} tablo")


if __name__ == "__main__":
    main()
