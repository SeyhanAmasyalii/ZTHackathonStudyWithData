"""Azure SQL'den ham datav2 satırlarını okur (mssql-python; ODBC kurulumu gerekmez).

Kimlik: SQL_USER/SQL_PASSWORD verilirse SQL kimlik doğrulaması, verilmezse Microsoft Entra
(yerelde `az login`, App Service'te Managed Identity) kullanılır. Şifre hiçbir yerde loglanmaz.
"""

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from app.config import Settings
from app.repositories.datav2 import TABLES, RawData

logger = logging.getLogger(__name__)

# Tablo → kolonlar (db/schema.sql). Sorgulara yalnızca bu sabit adlar girer, kullanıcı girdisi
# girmez; değerler her zaman parametreyle (?) gönderilir.
TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "screens": ("code", "name", "description"),
    "institutions": ("institution_code", "name", "bill_type"),
    "institution_screens": ("institution_code", "screen_code"),
    "solution_templates": ("solution_template_id", "solution_text", "mercek_assigned_title"),
    "incidents": (
        "incident_id",
        "created_at",
        "status",
        "screen_code",
        "institution_code",
        "kibana_correlation_id",
        "mercek_assigned_error_code",
        "note",
        "resolution_note",
        "closure_code",
        "sub_closure_code",
        "solution_template_id",
        "reporter_user_name",
        "scenario_path",
    ),
    "kibana_logs": (
        "log_id",
        "log_time",
        "log_level",
        "user_name",
        "customer_id",
        "screen_id",
        "app_exception_value",
        "correlation_id",
        "message",
        "exception_message",
        "message_fields",
        "message_response",
    ),
}
# DATETIMEOFFSET kolonları ISO 8601 metin olarak okunur (JSON'daki biçimle aynı).
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
        f"CONVERT(NVARCHAR(40), {column}, 127) AS {column}"
        if column in DATETIME_COLUMNS
        else column
        for column in TABLE_COLUMNS[table]
    )
    return f"SELECT {columns} FROM dbo.{table}"


def insert_sql(table: str) -> str:
    columns = TABLE_COLUMNS[table]
    placeholders = ", ".join("?" for _ in columns)
    return f"INSERT INTO dbo.{table} ({', '.join(columns)}) VALUES ({placeholders})"


def read_raw(connection) -> RawData:
    cursor = connection.cursor()
    tables = {}
    for table in TABLES:
        columns = TABLE_COLUMNS[table]
        cursor.execute(select_sql(table))
        tables[table] = tuple(dict(zip(columns, row, strict=True)) for row in cursor.fetchall())
    return RawData(**tables)
