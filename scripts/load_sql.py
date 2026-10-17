"""datav2 JSON'larını Azure SQL'e yükler: db/schema.sql tabloları yeniden oluşturur, sonra doldurur.

Kullanım (repo kökünden):
    uv run --directory backend python ../scripts/load_sql.py

Bağlantı backend/.env'den okunur: SQL_SERVER, SQL_DATABASE ve (SQL kimlik doğrulaması için)
SQL_USER, SQL_PASSWORD. SQL_USER boşsa Microsoft Entra kullanılır (önce `az login`).
Tüm değerler parametreyle gönderilir; şifre ekrana yazılmaz.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import REPO_ROOT, get_settings  # noqa: E402
from app.repositories import sql  # noqa: E402
from app.repositories.datav2 import TABLES, build_catalog, read_json  # noqa: E402

BATCH_SIZE = 500


def schema_batches() -> list[str]:
    text = (ROOT / "db" / "schema.sql").read_text(encoding="utf-8")
    batches = re.split(r"^\s*GO\s*$", text, flags=re.MULTILINE | re.IGNORECASE)
    return [batch.strip() for batch in batches if batch.strip()]


def main() -> None:
    settings = get_settings()
    if not settings.sql_server:
        sys.exit("SQL_SERVER tanımlı değil: backend/.env dosyasına SQL_SERVER=... ekleyin")
    raw = read_json(REPO_ROOT / "datav2")
    print(f"Bağlanılıyor: {settings.sql_server} / {settings.sql_database}")
    with sql.connect(settings) as connection:
        cursor = connection.cursor()
        for batch in schema_batches():
            cursor.execute(batch)
        connection.commit()
        print("✓ Tablolar oluşturuldu (db/schema.sql)")

        for table in TABLES:
            columns = sql.TABLE_COLUMNS[table]
            rows = [tuple(row.get(column) for column in columns) for row in getattr(raw, table)]
            statement = sql.insert_sql(table)
            for start in range(0, len(rows), BATCH_SIZE):
                cursor.executemany(statement, rows[start : start + BATCH_SIZE])
            connection.commit()
            cursor.execute(f"SELECT COUNT(*) FROM dbo.{table}")
            print(f"✓ {table}: {cursor.fetchone()[0]} satır (JSON: {len(rows)})")

        # Kontrol: SQL'den okunan katalog JSON'dan kurulanla aynı mı?
        from_sql = build_catalog(sql.read_raw(connection))
    from_json = build_catalog(raw)
    if from_sql != from_json:
        sys.exit("✗ SQL'den okunan veri JSON ile aynı değil")
    logs, incidents = len(from_sql.logs), len(from_sql.incidents)
    print(f"✓ Kontrol: {logs} hata logu, {incidents} çağrı; JSON ile aynı")


if __name__ == "__main__":
    main()
