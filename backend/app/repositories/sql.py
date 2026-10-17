"""Azure SQL'den ham datav2 satırlarını okur (mssql-python; ODBC kurulumu gerekmez).

Kimlik: SQL_USER/SQL_PASSWORD verilirse SQL kimlik doğrulaması, verilmezse Microsoft Entra
(yerelde `az login`, App Service'te Managed Identity) kullanılır. Şifre hiçbir yerde loglanmaz.
"""

import json
import logging
import time
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from typing import Any

from app.config import Settings
from app.repositories.datav2 import TABLES, RawData

logger = logging.getLogger(__name__)

# Tablo → kolon: SQL tipi (db/schema.sql ile aynı; testte karşılaştırılır). Sorgulara yalnızca bu
# sabit adlar girer, kullanıcı girdisi girmez; değerler her zaman parametreyle (?) gönderilir.
TABLE_COLUMNS: dict[str, dict[str, str]] = {
    "screens": {
        "code": "NVARCHAR(20)",
        "name": "NVARCHAR(200)",
        "description": "NVARCHAR(MAX)",
    },
    "institutions": {
        "institution_code": "NVARCHAR(20)",
        "name": "NVARCHAR(200)",
        "bill_type": "NVARCHAR(50)",
    },
    "institution_screens": {
        "institution_code": "NVARCHAR(20)",
        "screen_code": "NVARCHAR(20)",
    },
    "solution_templates": {
        "solution_template_id": "NVARCHAR(20)",
        "solution_text": "NVARCHAR(MAX)",
        "mercek_assigned_title": "NVARCHAR(300)",
    },
    "incidents": {
        "incident_id": "NVARCHAR(20)",
        "created_at": "DATETIMEOFFSET(3)",
        "status": "NVARCHAR(20)",
        "screen_code": "NVARCHAR(20)",
        "institution_code": "NVARCHAR(20)",
        "kibana_correlation_id": "NVARCHAR(64)",
        "mercek_assigned_error_code": "NVARCHAR(100)",
        "note": "NVARCHAR(MAX)",
        "resolution_note": "NVARCHAR(MAX)",
        "closure_code": "NVARCHAR(50)",
        "sub_closure_code": "NVARCHAR(50)",
        "solution_template_id": "NVARCHAR(20)",
        "reporter_user_name": "NVARCHAR(50)",
        "scenario_path": "NVARCHAR(400)",
    },
    "kibana_logs": {
        "log_id": "BIGINT",
        "log_time": "DATETIMEOFFSET(3)",
        "log_level": "NVARCHAR(20)",
        "user_name": "NVARCHAR(50)",
        "customer_id": "NVARCHAR(20)",
        "screen_id": "NVARCHAR(20)",
        "app_exception_value": "INT",
        "correlation_id": "NVARCHAR(64)",
        "message": "NVARCHAR(MAX)",
        "exception_message": "NVARCHAR(MAX)",
        "message_fields": "NVARCHAR(MAX)",
        "message_response": "NVARCHAR(MAX)",
    },
}
# DATETIMEOFFSET kolonları ISO 8601 metin olarak okunur (126: yerel saat + ofset, JSON'daki gibi).
DATETIME_COLUMNS = {"created_at", "log_time"}

CONNECT_ATTEMPTS = 3
RETRY_SECONDS = 10


def _quote(value: str) -> str:
    """Bağlantı dizesi değeri; ; { } ya da boşluk içeriyorsa süslü paranteze alınır."""
    if any(char in value for char in ";{}") or value != value.strip():
        return "{" + value.replace("}", "}}") + "}"
    return value


def connection_string(settings: Settings) -> str:
    server = settings.sql_server.strip().removeprefix("tcp:")
    if "," not in server:
        server = f"{server},1433"
    parts = {
        "Server": f"tcp:{server}",
        "Database": settings.sql_database,
        "Encrypt": "yes",
        "TrustServerCertificate": "no",
    }
    if settings.sql_user:
        parts["Uid"] = settings.sql_user
        parts["Pwd"] = settings.sql_password
    else:
        parts["Authentication"] = "ActiveDirectoryDefault"
    return ";".join(f"{key}={_quote(value)}" for key, value in parts.items())


@contextmanager
def connect(settings: Settings) -> Iterator[Any]:
    """Bağlanır; Free/serverless veritabanı uykudaysa uyanması için birkaç kez dener."""
    # Sürücü burada yüklenir: sistem kütüphanesi eksikse uygulama yine açılır (JSON'a düşer).
    import mssql_python

    for attempt in range(1, CONNECT_ATTEMPTS + 1):
        try:
            connection = mssql_python.connect(connection_string(settings))
            break
        except mssql_python.Error as exc:
            if attempt == CONNECT_ATTEMPTS:
                raise
            logger.warning(
                "SQL bağlantısı kurulamadı (deneme %d/%d): %s",
                attempt,
                CONNECT_ATTEMPTS,
                str(exc)[:300],
            )
            time.sleep(RETRY_SECONDS)
    try:
        yield connection
    finally:
        connection.close()


def select_sql(table: str) -> str:
    columns = ", ".join(
        f"CONVERT(NVARCHAR(40), {column}, 126) AS {column}"
        if column in DATETIME_COLUMNS
        else column
        for column in TABLE_COLUMNS[table]
    )
    return f"SELECT {columns} FROM dbo.{table}"


def insert_sql(table: str) -> str:
    """Bir parti satırı tek JSON parametresiyle ekler (OPENJSON).

    JSON ASCII kaçışlı gönderilir (bkz. rows_payload); böylece sürücü metni hangi tipte bağlarsa
    bağlasın Türkçe karakterler bozulmaz ve her parti tek istekte gider.
    """
    columns = TABLE_COLUMNS[table]
    names = ", ".join(columns)
    schema = ", ".join(f"{column} {sql_type} '$.{column}'" for column, sql_type in columns.items())
    return f"INSERT INTO dbo.{table} ({names}) SELECT {names} FROM OPENJSON(?) WITH ({schema})"


def rows_payload(table: str, rows: Iterable[dict]) -> str:
    columns = TABLE_COLUMNS[table]
    return json.dumps([{column: row.get(column) for column in columns} for row in rows])


def read_raw(connection) -> RawData:
    cursor = connection.cursor()
    tables = {}
    for table in TABLES:
        columns = tuple(TABLE_COLUMNS[table])
        cursor.execute(select_sql(table))
        tables[table] = tuple(dict(zip(columns, row, strict=True)) for row in cursor.fetchall())
    return RawData(**tables)
