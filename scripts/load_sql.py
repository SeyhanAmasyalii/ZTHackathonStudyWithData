"""datav2'nin tüm tablolarını (+ ui/scenarios.ts) Azure SQL'e yükler ve JSON ile karşılaştırır.

Kullanım (repo kökünden):
    uv run --directory backend python ../scripts/load_sql.py

1. db/schema.sql çalıştırılır: tablolar silinip yeniden oluşturulur (şema: scripts/build_schema.py).
2. Her tablo 500 satırlık partiler halinde, tek JSON parametresiyle (OPENJSON) eklenir.
3. Her tablo SQL'den geri okunup JSON ile alan alan karşılaştırılır; sohbet kataloğu da kontrol
   edilir.

Bağlantı backend/.env'den okunur: SQL_SERVER, SQL_DATABASE ve (SQL kimlik doğrulaması için)
SQL_USER, SQL_PASSWORD. SQL_USER boşsa Microsoft Entra kullanılır (önce `az login`).
Şifre ekrana yazılmaz.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from datav2_tables import (  # noqa: E402
    DATA_DIR,
    columns_of,
    parse_schema,
    primary_key,
    read_tables,
    schema_batches,
)

from app.config import get_settings  # noqa: E402
from app.repositories import sql  # noqa: E402
from app.repositories.datav2 import build_catalog, read_json  # noqa: E402

BATCH_SIZE = 500
TEXT_DATETIME = ("DATETIMEOFFSET", "DATETIME2")


def nested_columns(rows: list[dict]) -> set[str]:
    return {key for row in rows for key, value in row.items() if isinstance(value, dict | list)}


def insert_sql(table: str, types: dict[str, str], nested: set[str]) -> str:
    """Bir parti satırı tek JSON parametresiyle ekler. Tablo/kolon adları şemadan gelir."""
    columns = [column for column, sql_type in types.items() if "IDENTITY" not in sql_type]
    names = ", ".join(f"[{column}]" for column in columns)
    with_clause = ", ".join(
        f"[{column}] {types[column]} '$.\"{column}\"'" + (" AS JSON" if column in nested else "")
        for column in columns
    )
    return f"INSERT INTO dbo.{table} ({names}) SELECT {names} FROM OPENJSON(?) WITH ({with_clause})"


def rows_payload(rows: list[dict], columns: list[str]) -> str:
    # ASCII kaçışlı JSON: sürücü metni hangi tipte bağlarsa bağlasın Türkçe karakterler bozulmaz.
    return json.dumps([{column: row.get(column) for column in columns} for row in rows])


def select_sql(table: str, types: dict[str, str]) -> str:
    parts = []
    for column, sql_type in types.items():
        if sql_type.startswith(TEXT_DATETIME):
            parts.append(f"CONVERT(NVARCHAR(40), [{column}], 126)")
        elif sql_type == "DATE":
            parts.append(f"CONVERT(NVARCHAR(10), [{column}], 23)")
        else:
            parts.append(f"[{column}]")
    return f"SELECT {', '.join(parts)} FROM dbo.{table}"


def same(expected, actual, sql_type: str, nested: bool) -> bool:
    if expected is None or actual is None:
        return expected is None and actual is None
    if nested:
        return json.loads(actual) == expected
    if sql_type.startswith(TEXT_DATETIME):
        return datetime.fromisoformat(actual) == datetime.fromisoformat(expected)
    if sql_type == "FLOAT":
        return float(actual) == float(expected)
    return actual == expected


def first_difference(table, rows, sql_rows, types, nested) -> str | None:
    """JSON satırlarını anahtarla (şemadaki birincil anahtar kolonları) SQL satırlarıyla eşler."""
    columns = list(types)
    key_columns = primary_key(rows, columns, types) or columns
    positions = [columns.index(column) for column in key_columns]
    by_key = {tuple(row[p] for p in positions): row for row in sql_rows}
    for row in rows:
        key = tuple(row.get(column) for column in key_columns)
        found = by_key.get(key)
        if found is None:
            return f"{table}: {dict(zip(key_columns, key, strict=True))} SQL'de yok"
        for index, column in enumerate(columns):
            if not same(row.get(column), found[index], types[column], column in nested):
                return f"{table}.{column} {key}: {row.get(column)!r} ≠ {found[index]!r}"
    return None


def main() -> None:
    settings = get_settings()
    if not settings.sql_server:
        sys.exit("SQL_SERVER tanımlı değil: backend/.env dosyasına SQL_SERVER=... ekleyin")
    schema_text = (ROOT / "db" / "schema.sql").read_text(encoding="utf-8")
    schema = parse_schema(schema_text)
    tables = read_tables()
    for table, rows in tables.items():
        missing = set(columns_of(rows)) - set(schema.get(table, {}))
        if missing:
            sys.exit(
                f"db/schema.sql eski ({table}: {sorted(missing)}). "
                "Önce: python scripts/build_schema.py"
            )

    print(f"Bağlanılıyor: {settings.sql_server} / {settings.sql_database}")
    with sql.connect(settings) as connection:
        cursor = connection.cursor()
        for batch in schema_batches(schema_text):
            cursor.execute(batch)
        connection.commit()
        print(f"✓ {len(schema)} tablo oluşturuldu (db/schema.sql)")

        for table in sorted(schema):
            types = schema[table]
            rows = tables.get(table, [])
            nested = nested_columns(rows)
            if rows:
                statement = insert_sql(table, types, nested)
                columns = [c for c, t in types.items() if "IDENTITY" not in t]
                for start in range(0, len(rows), BATCH_SIZE):
                    payload = rows_payload(rows[start : start + BATCH_SIZE], columns)
                    cursor.execute(statement, [payload])
                connection.commit()
            cursor.execute(select_sql(table, types))
            sql_rows = cursor.fetchall()
            if len(sql_rows) != len(rows):
                sys.exit(f"✗ {table}: SQL {len(sql_rows)} satır, JSON {len(rows)}")
            difference = first_difference(table, rows, sql_rows, types, nested)
            if difference:
                sys.exit(f"✗ {difference}")
            print(f"✓ {table}: {len(rows)} satır, içerik JSON ile aynı")

        # Sohbetin okuduğu katalog (backend) SQL'den de aynı kuruluyor mu?
        from_sql = build_catalog(sql.read_raw(connection))
    if from_sql != build_catalog(read_json(DATA_DIR)):
        sys.exit("✗ Sohbet kataloğu SQL'den farklı kuruldu")
    logs, incidents = len(from_sql.logs), len(from_sql.incidents)
    print(f"✓ Kontrol: {len(schema)} tablo; sohbet kataloğu {logs} hata logu, {incidents} çağrı")


HINTS = {
    "is not allowed to access the server": (
        "Bu bilgisayarın IP adresi SQL güvenlik duvarında yok (ev/ofis IP'si değişmiş olabilir).\n"
        "Portal → SQL sunucusu → Güvenlik → Ağ İletişimi → + İstemci IPv4 adresinizi ekleyin →"
        " Kaydet. Sonra 1–2 dk bekleyip tekrar çalıştırın."
    ),
    "Login failed": "SQL_USER / SQL_PASSWORD yanlış (backend/.env).",
}


def run() -> None:
    try:
        main()
    except Exception as exc:  # sürücü hataları: kısa, anlaşılır mesaj
        message = str(exc)
        hint = next((text for key, text in HINTS.items() if key in message), None)
        if hint is None:
            raise
        ip = re.search(r"IP address '([^']+)'", message)
        sys.exit(f"✗ SQL'e bağlanılamadı{f' (IP: {ip.group(1)})' if ip else ''}.\n{hint}")


if __name__ == "__main__":
    run()
