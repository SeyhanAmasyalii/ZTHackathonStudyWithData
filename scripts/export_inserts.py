"""datav2 tablolarının (+ scenarios, app_users) INSERT cümlelerini tek bir .sql dosyasına yazar.

Kullanım (repo kökünden):
    uv run --directory backend python ../scripts/export_inserts.py [--cikti dist/mercek-inserts.sql]
    [--tablo incidents --tablo screens]

- Veritabanına bağlanmaz; veri datav2/ JSON'larından, tipler db/schema.sql'den okunur.
- Önce tablolar oluşturulmalı: db/schema.sql ve db/app_tables.sql (Query editor ya da sqlcmd).
- Her tablo önce DELETE ile boşaltılır, sonra 1000 satırlık INSERT ... VALUES partileri (GO ile).
- app_users: MERGE yerine silmeden ekleme (yoksa ekler); konuşma ve audit kayıtları dışa alınmaz.
Büyük tablolar için hızlı yol yine scripts/load_sql.py'dir.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from datav2_tables import parse_schema, read_tables  # noqa: E402
from setup_app_tables import user_rows  # noqa: E402

ROWS_PER_INSERT = 1000  # T-SQL VALUES sınırı
APP_USERS_TYPES = {
    "user_name": "NVARCHAR(50)",
    "full_name": "NVARCHAR(100)",
    "title": "NVARCHAR(100)",
    "unit": "NVARCHAR(100)",
    "role": "NVARCHAR(20)",
    "can_view_customers": "BIT",
    "sort_order": "INT",
}


def literal(value, sql_type: str) -> str:
    """Python değeri → T-SQL sabiti. Metinler N'...' ve tek tırnak ikilenir."""
    if value is None:
        return "NULL"
    if isinstance(value, dict | list):
        value = json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int | float):
        if sql_type == "BIT":
            return "1" if value else "0"
        return repr(value)
    return "N'" + str(value).replace("'", "''") + "'"


def table_inserts(table: str, rows: list[dict], types: dict[str, str]) -> list[str]:
    columns = [column for column, sql_type in types.items() if "IDENTITY" not in sql_type]
    names = ", ".join(f"[{column}]" for column in columns)
    out = [f"-- dbo.{table}: {len(rows)} satır", f"DELETE FROM dbo.{table};", "GO"]
    for start in range(0, len(rows), ROWS_PER_INSERT):
        chunk = rows[start : start + ROWS_PER_INSERT]
        values = ",\n".join(
            "(" + ", ".join(literal(row.get(c), types[c]) for c in columns) + ")" for row in chunk
        )
        out += [f"INSERT INTO dbo.{table} ({names}) VALUES\n{values};", "GO"]
    return out + [""]


def app_users_inserts() -> list[str]:
    columns = list(APP_USERS_TYPES)
    out = ["-- dbo.app_users: demo kullanıcılar (varsa dokunulmaz)"]
    for row in user_rows():
        values = ", ".join(literal(row[c], APP_USERS_TYPES[c]) for c in columns)
        out.append(
            f"IF NOT EXISTS (SELECT 1 FROM dbo.app_users WHERE user_name = "
            f"{literal(row['user_name'], 'NVARCHAR')})\n"
            f"    INSERT INTO dbo.app_users ({', '.join(columns)}) VALUES ({values});"
        )
    return out + ["GO", ""]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--cikti", default=str(ROOT / "dist" / "mercek-inserts.sql"))
    parser.add_argument("--tablo", action="append", help="yalnızca bu tablo(lar)")
    args = parser.parse_args()

    schema = parse_schema((ROOT / "db" / "schema.sql").read_text(encoding="utf-8"))
    tables = read_tables()
    names = sorted(args.tablo or tables)
    unknown = [name for name in names if name not in tables and name != "app_users"]
    if unknown:
        sys.exit(f"Bilinmeyen tablo: {', '.join(unknown)}")

    lines = [
        "-- Mercek: datav2 verisinin INSERT cümleleri (T-SQL). ÜRETİLMİŞ DOSYA.",
        "-- Üretmek için: uv run --directory backend python ../scripts/export_inserts.py",
        "-- Önce db/schema.sql ve db/app_tables.sql çalıştırılmış olmalı.",
        "SET NOCOUNT ON;",
        "GO",
        "",
    ]
    counts: dict[str, int] = {}
    for name in names:
        if name == "app_users":
            continue
        missing = set().union(*(row.keys() for row in tables[name])) - set(schema.get(name, {}))
        if missing:
            sys.exit(f"db/schema.sql eski ({name}: {sorted(missing)}). Önce: build_schema.py")
        lines += table_inserts(name, tables[name], schema[name])
        counts[name] = len(tables[name])
    if not args.tablo or "app_users" in args.tablo:
        lines += app_users_inserts()
        counts["app_users"] = len(user_rows())

    output = Path(args.cikti)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8-sig")  # BOM: SSMS Türkçe'yi doğru okur
    for name, count in counts.items():
        print(f"  {name:<28} {count:>7}")
    size_mb = output.stat().st_size / 1024 / 1024
    print(f"✓ {output} ({sum(counts.values())} satır, {size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
