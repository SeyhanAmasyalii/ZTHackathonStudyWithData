"""Mercek veritabanı katmanı: tablo tanımları, DDL, bağlantı ve toplu yazma (V7, V8).

Aynı tablo tanımından iki lehçe üretilir:
  mssql  · Azure SQL (pyodbc + ODBC Driver 18). data/schema.sql bu lehçededir.
  sqlite · Yerel geliştirme ve testler (standart kütüphane).

Bağlantı (Azure SQL), ortam değişkenlerinden:
  SQL_SERVER, SQL_DATABASE ve
  SQL_USER + SQL_PASSWORD  (SQL kimlik doğrulama)  ya da  yoksa ActiveDirectoryDefault (Entra / Managed Identity)
Şifre koda ve loga yazılmaz.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SQLITE = ROOT / "data" / "out" / "mercek.db"
SCHEMA_FILE = ROOT / "data" / "schema.sql"

# ---------------------------------------------------------------------------
# Tablo tanımları: (kolon, tür, boş olabilir mi)
# Türler: id · s<n> (kısa metin) · text · json · int · bigint · float · bool · date · dt
# ---------------------------------------------------------------------------
TABLES: Dict[str, Dict] = {
    "services": {"pk": ["service_id"], "cols": [("service_id", "s40", False), ("name", "s120", False),
                                                ("description", "text", True)]},
    "screens": {"pk": ["code"], "cols": [("code", "s8", False), ("name", "s120", False), ("module", "s3", False),
                                         ("type", "s1", False), ("simulated", "bool", False),
                                         ("description", "text", True), ("components_json", "json", True),
                                         ("flow_json", "json", True), ("files_json", "json", True)]},
    "screen_services": {"pk": ["screen_code", "service_id"],
                        "cols": [("screen_code", "s8", False), ("service_id", "s40", False), ("role", "s20", False)]},
    "error_rules": {"pk": ["screen_code", "error_code"],
                    "cols": [("screen_code", "s8", False), ("error_code", "s40", False), ("error_type", "s20", False),
                             ("service_id", "s40", True), ("open_incident", "bool", False),
                             ("explanation_hint", "text", True)]},
    "service_calendar": {"pk": ["service_id", "date_from"],
                         "cols": [("service_id", "s40", False), ("date_from", "date", False), ("date_to", "date", False),
                                  ("allocation_pct", "int", False), ("note", "s200", True)]},
    "scope_addons": {"pk": ["addon_id"], "cols": [("addon_id", "s40", False), ("name", "s200", False),
                                                  ("effort_md", "int", False), ("main_share", "int", False),
                                                  ("customer_mgmt_share", "int", False)]},
    "announcements": {"pk": ["ann_id"], "cols": [("ann_id", "s20", False), ("institution", "s80", False),
                                                 ("published_at", "date", False), ("effective_at", "date", False),
                                                 ("title", "s300", False), ("body", "text", False)]},
    "customers": {"pk": ["customer_number"],
                  "cols": [("customer_number", "s12", False), ("full_name", "s120", False), ("segment", "s40", False),
                           ("age", "int", True), ("monthly_income", "int", True), ("city", "s40", False),
                           ("district", "s40", True), ("region_affected", "bool", False),
                           ("address_changed_at", "date", True), ("email", "s120", True), ("phone", "s30", True),
                           ("perm_email", "bool", False), ("perm_sms", "bool", False), ("perm_phone", "bool", False),
                           ("in_logs", "bool", False)]},
    "loans": {"pk": ["loan_id"],
              "cols": [("loan_id", "s12", False), ("customer_number", "s12", False), ("product", "s60", False),
                       ("principal", "float", False), ("remaining_principal", "float", False),
                       ("monthly_rate", "float", False), ("term", "int", False), ("installment", "float", False),
                       ("paid_installments", "int", False), ("next_due_date", "date", False), ("status", "s20", False),
                       ("delinquent_12m", "bool", False), ("collection_account", "s34", True)]},
    "banking_logs": {"pk": ["log_id"], "identity": "log_id",
                     "cols": [("log_id", "id", False), ("ts", "dt", False), ("level", "s10", False),
                              ("screen_code", "s8", False), ("event_action", "s40", True), ("outcome", "s20", True),
                              ("error_code", "s40", True), ("error_type", "s20", True), ("error_field", "s40", True),
                              ("customer_number", "s12", True), ("trace_id", "s40", True), ("channel", "s30", True),
                              ("branch_code", "s10", True), ("employee_id", "s20", True), ("institution", "s80", True),
                              ("subscriber_no", "s30", True), ("subscriber_no_len", "int", True),
                              ("amount", "float", True), ("message", "s1000", True), ("source", "s10", True),
                              ("raw_json", "json", True)]},
    "contacts": {"pk": ["contact_id"],
                 "cols": [("contact_id", "s12", False), ("created_at", "dt", False), ("channel", "s20", False),
                          ("customer_number", "s12", True), ("city", "s40", True), ("region_affected", "bool", False),
                          ("category", "s60", False), ("subcategory", "s80", False), ("note", "text", True),
                          ("incident_id", "s16", True)]},
    "incidents": {"pk": ["incident_id"],
                  "cols": [("incident_id", "s16", False), ("created_at", "dt", False), ("channel", "s20", False),
                           ("screen_code", "s8", True), ("category", "s60", True), ("subcategory", "s80", True),
                           ("note", "text", True), ("customer_number", "s12", True), ("subscriber_no", "s30", True),
                           ("trace_id", "s40", True), ("city", "s40", True), ("service_id", "s40", True),
                           ("error_code", "s40", True), ("institution", "s80", True),
                           ("master_incident_id", "s16", True), ("status", "s10", False), ("solution_id", "s10", True),
                           ("resolution_minutes", "int", True), ("enriched_json", "json", True)]},
    "solutions": {"pk": ["solution_id"],
                  "cols": [("solution_id", "s10", False), ("title", "s300", False), ("symptom", "text", True),
                           ("root_cause", "text", True), ("steps", "json", True), ("error_code", "s40", True),
                           ("service_id", "s40", True)]},
    "requests": {"pk": ["request_id"],
                 "cols": [("request_id", "s10", False), ("created_at", "date", False), ("requester_unit", "s80", True),
                          ("title", "s300", False), ("description", "text", True), ("type", "s20", False),
                          ("components_json", "json", True), ("screens_json", "json", True),
                          ("services_json", "json", True), ("effort_md", "int", True),
                          ("component_efforts_json", "json", True), ("service_efforts_json", "json", True),
                          ("decisions", "text", True), ("analysis_json", "json", True), ("analyst", "s80", True),
                          ("approved_by", "s80", True), ("scope_additions", "json", True), ("status", "s20", False),
                          ("planned_service_id", "s40", True), ("planned_from", "date", True),
                          ("planned_to", "date", True)]},
    "mercek_events": {"pk": ["event_id"], "identity": "event_id",
                      "cols": [("event_id", "id", False), ("ts", "dt", False), ("kind", "s30", False),
                               ("screen_code", "s8", True), ("incident_id", "s16", True), ("duration_ms", "int", True),
                               ("tokens", "int", True), ("detail_json", "json", True)]},
}
# AI Search indexer'ının okuduğu tablolar (V7, otomatik eşitleme). search_text: embedding'e giden metin,
# hesaplanan kolon olarak her lehçede veritabanı kendisi üretir; uygulama yazmaz.
SEARCH_SOURCES: Dict[str, List[str]] = {
    "solutions": ["title", "symptom", "root_cause", "steps"],
    "requests": ["title", "description"],
    "announcements": ["institution", "title", "body"],
}
LOAD_ORDER = ["services", "screens", "screen_services", "error_rules", "service_calendar", "scope_addons",
              "announcements", "customers", "loans", "banking_logs", "contacts", "solutions", "incidents", "requests",
              "mercek_events"]
INDEXES = [
    ("banking_logs", ["screen_code", "ts"]), ("banking_logs", ["institution", "ts"]), ("banking_logs", ["trace_id"]),
    ("banking_logs", ["customer_number", "ts"]), ("banking_logs", ["error_code", "error_field", "ts"]),
    ("contacts", ["category", "subcategory", "created_at"]), ("contacts", ["region_affected", "created_at"]),
    ("incidents", ["screen_code", "institution", "error_code", "status"]), ("incidents", ["master_incident_id"]),
    ("loans", ["customer_number"]), ("customers", ["region_affected"]), ("banking_logs", ["source"]),
]
# Yabancı anahtar bilinçli olarak yok: toplu yükleme ve demo sıfırlama sırası serbest kalır;
# ilişki bütünlüğünü validate_scenarios.py "Genel · bütünlük" satırı kontrol eder.


def _type(kind: str, dialect: str) -> str:
    if dialect == "sqlite":
        if kind in ("int", "bigint", "bool", "id"):
            return "INTEGER"
        return "REAL" if kind == "float" else "TEXT"
    if kind.startswith("s"):
        return f"NVARCHAR({kind[1:]})"
    return {"text": "NVARCHAR(MAX)", "json": "NVARCHAR(MAX)", "int": "INT", "bigint": "BIGINT", "float": "FLOAT",
            "bool": "BIT", "date": "DATE", "dt": "DATETIMEOFFSET(3)", "id": "BIGINT IDENTITY(1,1)"}[kind]


def ddl(dialect: str) -> List[str]:
    """DROP + CREATE + INDEX ifadeleri (bağımlılığın tersi sırada düşürülür)."""
    stmts = [f"DROP TABLE IF EXISTS {t}" for t in reversed(LOAD_ORDER)]
    for name in LOAD_ORDER:
        spec = TABLES[name]
        cols = []
        for col, kind, nullable in spec["cols"]:
            if dialect == "sqlite" and kind == "id":
                cols.append(f"{col} INTEGER PRIMARY KEY AUTOINCREMENT")
                continue
            line = f"{col} {_type(kind, dialect)}{'' if nullable else ' NOT NULL'}"
            if kind == "json" and dialect == "mssql":
                line += f" CHECK ({col} IS NULL OR ISJSON({col}) = 1)"
            cols.append(line)
        if name in SEARCH_SOURCES:
            cols.append(search_text_column(SEARCH_SOURCES[name], dialect))
        if not (dialect == "sqlite" and spec.get("identity")):
            cols.append(f"PRIMARY KEY ({', '.join(spec['pk'])})")
        stmts.append(f"CREATE TABLE {name} (\n  " + ",\n  ".join(cols) + "\n)")
    for i, (table, cols) in enumerate(INDEXES, 1):
        stmts.append(f"CREATE INDEX ix_{table}_{i} ON {table} ({', '.join(cols)})")
    return stmts


def search_text_column(fields: List[str], dialect: str) -> str:
    if dialect == "sqlite":
        expr = " || char(10) || ".join(f"COALESCE({f}, '')" for f in fields)
        return f"search_text TEXT GENERATED ALWAYS AS ({expr}) VIRTUAL"
    return f"search_text AS (CONCAT_WS(NCHAR(10), {', '.join(fields)})) PERSISTED"


def change_tracking_statements() -> List[str]:
    """Azure SQL değişiklik takibi: indexer yalnızca yeni/değişen/silinen satırı okur. Transaction dışında çalışır."""
    return (["IF NOT EXISTS (SELECT 1 FROM sys.change_tracking_databases WHERE database_id = DB_ID()) "
             "ALTER DATABASE CURRENT SET CHANGE_TRACKING = ON (CHANGE_RETENTION = 2 DAYS, AUTO_CLEANUP = ON)"]
            + [f"ALTER TABLE {t} ENABLE CHANGE_TRACKING" for t in SEARCH_SOURCES])


def enable_change_tracking(database: Database) -> None:
    if database.dialect != "mssql":
        return  # SQLite'ta indexer yok; search_text kolonu yine de var (aynı metin)
    previous = getattr(database.conn, "autocommit", False)
    database.conn.autocommit = True  # ALTER DATABASE kullanıcı transaction'ı içinde çalışmaz
    try:
        for stmt in change_tracking_statements():
            database.execute(stmt)
    finally:
        database.conn.autocommit = previous


def write_schema_file(path: Path = SCHEMA_FILE) -> Path:
    header = ("-- Mercek veritabanı şeması (Azure SQL / T-SQL). tools/mercek_data/db.py tablo tanımlarından üretilir;\n"
              "-- elle düzenlemeyin: python3 tools/mercek_data/load_all.py --write-schema\n\n")
    tail = ("\n\n-- AI Search indexer için değişiklik takibi (transaction dışında; load_all.py --sql kendisi çalıştırır)\n"
            + ";\n".join(change_tracking_statements()) + ";\n")
    path.write_text(header + ";\n\n".join(ddl("mssql")) + ";\n" + tail, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Bağlantı
# ---------------------------------------------------------------------------
class Database:
    """İnce sarmalayıcı: lehçe, çalıştırma, toplu yazma, sorgu."""

    def __init__(self, conn, dialect: str):
        self.conn, self.dialect = conn, dialect

    @classmethod
    def sqlite(cls, path: Path = DEFAULT_SQLITE) -> Database:
        path.parent.mkdir(parents=True, exist_ok=True)
        return cls(sqlite3.connect(str(path)), "sqlite")

    @classmethod
    def azure(cls) -> Database:  # pragma: no cover - Azure gerektirir
        import pyodbc  # isteğe bağlı bağımlılık

        server, database = os.environ.get("SQL_SERVER"), os.environ.get("SQL_DATABASE")
        if not server or not database:
            raise SystemExit("SQL_SERVER ve SQL_DATABASE ortam değişkenleri gerekli")
        base = (f"Driver={{ODBC Driver 18 for SQL Server}};Server=tcp:{server},1433;Database={database};"
                "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;")
        user, password = os.environ.get("SQL_USER"), os.environ.get("SQL_PASSWORD")
        auth = f"Uid={user};Pwd={password};" if user and password else "Authentication=ActiveDirectoryDefault;"
        conn = pyodbc.connect(base + auth, autocommit=False)
        return cls(conn, "mssql")

    def execute(self, sql: str, params: Sequence = ()) -> None:
        cur = self.conn.cursor()
        cur.execute(sql, tuple(params))

    def query(self, sql: str, params: Sequence = ()) -> List[Tuple]:
        cur = self.conn.cursor()
        cur.execute(sql, tuple(params))
        return [tuple(r) for r in cur.fetchall()]

    def scalar(self, sql: str, params: Sequence = ()):
        rows = self.query(sql, params)
        return rows[0][0] if rows else None

    def insert_many(self, table: str, rows: Iterable[Dict], chunk: int = 1000) -> int:
        spec = TABLES[table]
        cols = [c for c, k, _ in spec["cols"] if k != "id"]
        kinds = {c: k for c, k, _ in spec["cols"]}
        sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})"
        cur = self.conn.cursor()
        if self.dialect == "mssql":  # pragma: no cover
            cur.fast_executemany = True
        batch: List[Tuple] = []
        total = 0
        for row in rows:
            batch.append(tuple(_value(row.get(c), kinds[c]) for c in cols))
            if len(batch) >= chunk:
                cur.executemany(sql, batch)
                total += len(batch)
                batch = []
        if batch:
            cur.executemany(sql, batch)
            total += len(batch)
        return total

    def commit(self) -> None:
        self.conn.commit()

    def rollback(self) -> None:
        self.conn.rollback()

    def close(self) -> None:
        self.conn.close()


def utc_iso(v) -> str:
    """Zaman damgalarını tek biçime çevirir (UTC, milisaniye): metin karşılaştırması SQLite'ta da doğru çalışsın."""
    ts = v if isinstance(v, datetime) else datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    if ts.tzinfo is None:
        raise ValueError(f"saat dilimi olmayan zaman: {v}")
    return ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{ts.microsecond // 1000:03d}+00:00"


def _value(v, kind: str):
    if v is None or (isinstance(v, str) and v == ""):
        return None
    if kind == "bool":
        return 1 if v in (True, 1, "1", "true", "True") else 0
    if kind in ("int", "bigint"):
        return int(float(v))
    if kind == "float":
        return float(v)
    if kind == "dt":
        return utc_iso(v)
    if kind == "json" and not isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    return v


# ---------------------------------------------------------------------------
# Log düzleştirme (V3 kaydı → banking_logs satırı)
# ---------------------------------------------------------------------------
def flatten_log(r: Dict, source: str = "seed") -> Dict:
    err = r.get("error", {})
    bill = r.get("banking", {}).get("bill", {})
    return {
        "ts": r["@timestamp"], "level": r["log.level"], "screen_code": r["screen"]["code"],
        "event_action": r.get("event", {}).get("action"), "outcome": r.get("event", {}).get("outcome"),
        "error_code": err.get("code"), "error_type": err.get("type"), "error_field": err.get("field"),
        "customer_number": r.get("customer", {}).get("number"), "trace_id": r.get("trace", {}).get("id"),
        "channel": r.get("channel"), "branch_code": r.get("branch", {}).get("code"),
        "employee_id": r.get("employee", {}).get("id"), "institution": bill.get("institution"),
        "subscriber_no": bill.get("subscriber_no"), "subscriber_no_len": bill.get("subscriber_no_len"),
        "amount": r.get("amount", {}).get("value"), "message": r.get("message"), "source": source,
        "raw_json": json.dumps(r, ensure_ascii=False),
    }


def open_database(target: str, sqlite_path: Optional[Path] = None) -> Database:
    if target == "sqlite":
        return Database.sqlite(sqlite_path or DEFAULT_SQLITE)
    return Database.azure()
