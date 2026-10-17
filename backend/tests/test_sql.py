import sys

from app.config import REPO_ROOT, Settings
from app.repositories import catalog as catalog_module
from app.repositories import sql
from app.repositories.datav2 import TABLES, build_catalog, json_catalog, read_json

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from datav2_tables import parse_schema  # noqa: E402


class FakeCursor:
    """SELECT sorgularına JSON satırlarını tablo kolon sırasıyla döner."""

    def __init__(self, raw):
        self.raw = raw
        self.rows = []
        self.executed = []

    def execute(self, statement):
        self.executed.append(statement)
        table = statement.rsplit("dbo.", 1)[1]
        columns = sql.TABLE_COLUMNS[table]
        rows = getattr(self.raw, table)
        self.rows = [tuple(row.get(column) for column in columns) for row in rows]

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, raw):
        self.cursor_ = FakeCursor(raw)

    def cursor(self):
        return self.cursor_


def test_connection_string_sql_auth_quotes_password():
    settings = Settings(
        sql_server="mercek-sql.database.windows.net",
        sql_user="mercekadmin",
        sql_password="a;b}c",
    )
    text = sql.connection_string(settings)
    assert "Server=tcp:mercek-sql.database.windows.net,1433" in text
    assert "Database=mercekdb" in text
    assert "Encrypt=yes" in text
    assert "Pwd={a;b}}c}" in text
    assert "Authentication" not in text


def test_connection_string_without_user_uses_entra():
    settings = Settings(sql_server="tcp:mercek-sql.database.windows.net,1433")
    text = sql.connection_string(settings)
    assert "Server=tcp:mercek-sql.database.windows.net,1433;" in text
    assert "Authentication=ActiveDirectoryDefault" in text
    assert "Pwd" not in text


def test_select_sql_reads_datetimes_with_offset():
    statement = sql.select_sql("incidents")
    assert "CONVERT(NVARCHAR(40), [created_at], 126) AS [created_at]" in statement
    assert statement.endswith("FROM dbo.incidents")


def test_every_table_has_columns():
    assert set(sql.TABLE_COLUMNS) == set(TABLES)


def test_read_columns_exist_in_data_and_schema(data_dir):
    columns = sql.TABLE_COLUMNS["incidents"]
    assert {"reporter_user_name", "scenario_path"} <= set(columns)
    assert set(columns) <= set(read_json(data_dir).incidents[0])
    schema = parse_schema((REPO_ROOT / "db" / "schema.sql").read_text(encoding="utf-8"))
    for table, table_columns in sql.TABLE_COLUMNS.items():
        assert set(table_columns) <= set(schema[table]), table
    for column in sql.DATETIME_COLUMNS:
        assert any(schema[t].get(column, "").startswith("DATETIMEOFFSET") for t in schema)


def test_read_raw_builds_same_catalog_as_json(data_dir):
    raw = read_json(data_dir)
    from_sql = build_catalog(sql.read_raw(FakeConnection(raw)))
    assert from_sql == json_catalog(data_dir)
    assert len(from_sql.logs) == 2002


def test_catalog_uses_json_without_sql_server(monkeypatch, data_dir):
    monkeypatch.setattr(catalog_module, "get_settings", lambda: Settings(data_dir=data_dir))
    catalog_module._load.cache_clear()
    try:
        assert catalog_module.get_catalog() is json_catalog(data_dir)
    finally:
        catalog_module._load.cache_clear()


def test_catalog_falls_back_to_json_when_sql_fails(monkeypatch, data_dir):
    settings = Settings(data_dir=data_dir, sql_server="yok.database.windows.net")
    monkeypatch.setattr(catalog_module, "get_settings", lambda: settings)

    def broken_connect(_settings):
        raise RuntimeError("bağlantı yok")

    monkeypatch.setattr(catalog_module.sql, "connect", broken_connect)
    catalog_module._load.cache_clear()
    try:
        assert catalog_module.get_catalog() is json_catalog(data_dir)
    finally:
        catalog_module._load.cache_clear()


def test_catalog_reads_sql_when_configured(monkeypatch, data_dir):
    settings = Settings(data_dir=data_dir, sql_server="mercek-sql.database.windows.net")
    monkeypatch.setattr(catalog_module, "get_settings", lambda: settings)
    raw = read_json(data_dir)

    class FakeContext:
        def __enter__(self):
            return FakeConnection(raw)

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(catalog_module.sql, "connect", lambda _settings: FakeContext())
    catalog_module._load.cache_clear()
    try:
        loaded = catalog_module.get_catalog()
        assert loaded == json_catalog(data_dir)
        assert loaded is not json_catalog(data_dir)
    finally:
        catalog_module._load.cache_clear()


def test_connect_does_not_retry_firewall_error(monkeypatch):
    import mssql_python

    calls = []

    def refuse(_text):
        calls.append(1)
        raise mssql_python.ProgrammingError(
            "Client with IP address '1.2.3.4' is not allowed to access the server.", ""
        )

    monkeypatch.setattr(mssql_python, "connect", refuse)
    monkeypatch.setattr(sql.time, "sleep", lambda _s: None)
    settings = Settings(sql_server="x.database.windows.net", sql_user="u", sql_password="p")
    try:
        with sql.connect(settings):
            pass
    except mssql_python.Error:
        pass
    assert calls == [1]
