from app.config import Settings
from app.repositories import catalog as catalog_module
from app.repositories import sql
from app.repositories.datav2 import TABLES, build_catalog, json_catalog, read_json


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


def test_insert_sql_uses_parameters():
    statement = sql.insert_sql("institution_screens")
    assert statement == (
        "INSERT INTO dbo.institution_screens (institution_code, screen_code) VALUES (?, ?)"
    )


def test_select_sql_reads_datetimes_as_iso_text():
    statement = sql.select_sql("incidents")
    assert "CONVERT(NVARCHAR(40), created_at, 127) AS created_at" in statement
    assert statement.endswith("FROM dbo.incidents")


def test_every_table_has_columns():
    assert set(sql.TABLE_COLUMNS) == set(TABLES)


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
