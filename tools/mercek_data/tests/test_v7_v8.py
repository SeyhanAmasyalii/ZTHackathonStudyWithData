"""V7/V8 testleri: şema, SQLite uçtan uca (yükle → sıfırla → doğrula), Azure SQL ve AI Search için sahte istemciler."""
import hashlib
import importlib.util
import math
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TOOLS / "mercek_data"))
sys.path.insert(0, str(TOOLS))

import db  # noqa: E402
import demo_reset  # noqa: E402
import load_all  # noqa: E402
import search as srch  # noqa: E402
import validate_scenarios as vs  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gen = _load("generate_banking_logs_v7", TOOLS / "generate_banking_logs.py")
inj = _load("inject_log_scenarios_v7", TOOLS / "mercek_data" / "inject_log_scenarios.py")
gp = _load("generate_portfolio_v7", TOOLS / "mercek_data" / "generate_portfolio.py")
gi = _load("generate_incidents_v7", TOOLS / "mercek_data" / "generate_incidents.py")
gr = _load("generate_requests_v7", TOOLS / "mercek_data" / "generate_requests.py")
TR = timezone(timedelta(hours=3))
END = gen.parse_end("2026-10-17T09:00:00+03:00")
NOW = datetime(2026, 10, 17, 9, 0, tzinfo=TR)


@pytest.fixture(scope="module")
def out_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("v7")
    base, logs = d / "base.ndjson", d / "mercek-logs.ndjson"
    gen.write_records(gen.generate(10000, 30, 42, 800, END), base, "ndjson", gen.DEFAULT_INDEX)
    inj.run(base, logs, END, 42)
    pf = gp.build(42, logs)
    gp.write_csv(d / "customers.csv", pf["customers"], gp.CUSTOMER_FIELDS)
    gp.write_csv(d / "loans.csv", pf["loans"], gp.LOAN_FIELDS)
    res = gi.build(42, d / "customers.csv", logs)
    gi.write_csv(d / "contacts.csv", res["contacts"], gi.CONTACT_FIELDS)
    gi.write_csv(d / "incidents.csv", res["incidents"], gi.INCIDENT_FIELDS)
    gi.write_csv(d / "solutions.csv", res["solutions"], gi.SOLUTION_FIELDS)
    gi.write_csv(d / "requests.csv", gr.build_requests(42), gr.FIELDS)
    return d


@pytest.fixture(scope="module")
def loaded(out_dir):
    database = db.Database.sqlite(out_dir / "mercek.db")
    counts = load_all.load_sql(database, out=out_dir, logs=out_dir / "mercek-logs.ndjson")
    yield database, counts
    database.close()


# ---------------------------------------------------------------------------
# Şema
# ---------------------------------------------------------------------------
def test_schema_file_is_in_sync():
    committed = (db.ROOT / "data" / "schema.sql").read_text(encoding="utf-8")
    body = committed.split("\n\n", 1)[1]
    assert body.startswith(";\n\n".join(db.ddl("mssql")) + ";\n")
    assert all(stmt in committed for stmt in db.change_tracking_statements())


def test_mssql_ddl_shape():
    sql = "\n".join(db.ddl("mssql"))
    assert len(re.findall(r"CREATE TABLE", sql)) == 15
    assert "BIGINT IDENTITY(1,1)" in sql and "DATETIMEOFFSET(3)" in sql and "ISJSON(raw_json)" in sql
    assert sql.index("DROP TABLE IF EXISTS mercek_events") < sql.index("DROP TABLE IF EXISTS services")


def test_utc_iso_normalizes_offsets():
    assert db.utc_iso("2026-10-17T09:00:00+03:00") == "2026-10-17T06:00:00.000+00:00"
    assert db.utc_iso("2026-10-17T06:00:00.500Z") == "2026-10-17T06:00:00.500+00:00"
    with pytest.raises(ValueError):
        db.utc_iso("2026-10-17T06:00:00")


# ---------------------------------------------------------------------------
# SQLite uçtan uca
# ---------------------------------------------------------------------------
def test_load_counts(loaded):
    _, counts = loaded
    assert counts["customers"] == 40_000 and counts["loans"] == 33_000 and counts["incidents"] == 1_400
    assert counts["solutions"] == 37 and counts["requests"] == 95 and counts["announcements"] == 20
    assert counts["screens"] == 20 and counts["services"] == 7 and counts["banking_logs"] > 10_000


def test_reset_is_idempotent_and_validate_passes(loaded):
    database, _ = loaded
    first = demo_reset.reset(database, NOW, with_d_plan=True)
    assert first["demo_logs"] == 46 and first["demo_incidents"] == 12 and first["d_plan"] == 1
    database.execute("INSERT INTO incidents (incident_id, created_at, channel, status) VALUES "
                     "('CAG-2070', '2026-10-17T06:00:00.000+00:00', 'dijital', 'acik')")
    database.execute("INSERT INTO mercek_events (ts, kind) VALUES ('2026-10-17T06:00:00.000+00:00', 'analyze')")
    database.commit()
    later = NOW + timedelta(minutes=40)
    second = demo_reset.reset(database, later)
    assert second["silinen_banking_logs"] == 46 and second["silinen_incidents"] == 13
    assert second["silinen_requests"] == 1 and second["silinen_mercek_events"] == 1
    assert database.scalar("SELECT COUNT(*) FROM requests WHERE request_id = 'TLP-1043'") == 0
    master = database.query("SELECT created_at, institution, status FROM incidents WHERE incident_id = 'CAG-2051'")[0]
    assert master == (db.utc_iso(later - timedelta(minutes=24)), "Başkentgaz", "acik")

    results = vs.run_checks(vs.Ctx(database, later))
    failed = [r for r in results if r["status"] == "✗"]
    assert not failed, failed
    assert sum(r["status"] == "✓" for r in results) == 17
    assert {r["scenario"] for r in results if r["status"] == "–"} == {"Genel", "B", "C", "D", "E"}


def test_linked_cases_come_from_window(loaded):
    database, _ = loaded
    demo_reset.reset(database, NOW)
    linked = database.query("SELECT trace_id, subscriber_no, created_at FROM incidents WHERE master_incident_id = 'CAG-2051'")
    traces = {r[0] for r in database.query("SELECT trace_id FROM banking_logs WHERE source = 'demo'")}
    assert len(linked) == 11 and all(t in traces for t, _, _ in linked)
    ids = [r[0] for r in database.query("SELECT incident_id FROM incidents WHERE master_incident_id = 'CAG-2051' "
                                        "ORDER BY incident_id")]
    assert ids == [f"CAG-2051-{i:02d}" for i in range(1, 12)]
    last = database.scalar("SELECT MAX(incident_id) FROM incidents")
    assert int(last[4:8]) + 1 == 2052  # uygulamanın açacağı sonraki ana kayıt (C)
    times = sorted(r[2] for r in linked)
    assert times[0] == db.utc_iso(NOW - timedelta(minutes=22)) and times[-1] == db.utc_iso(NOW - timedelta(minutes=2))


def test_only_filter(loaded):
    database, _ = loaded
    results = vs.run_checks(vs.Ctx(database, NOW), only=["C"])
    assert {r["scenario"] for r in results} == {"C"}


# ---------------------------------------------------------------------------
# Takvim kuralı
# ---------------------------------------------------------------------------
def test_calendar_rule():
    cal = [{"service_id": "KREDI_TAKIP", "date_from": "2026-10-12", "date_to": "2026-11-08", "allocation_pct": 100}]
    assert vs.duration(15) == 18 and vs.duration(16) == 20 and vs.duration(8) == 10
    assert vs.plan(cal, "KREDI_TAKIP", 15) == (date(2026, 11, 9), date(2026, 12, 2))
    assert vs.plan(cal, "KREDI_TAKIP", 8, priority=True) == (date(2026, 10, 19), date(2026, 10, 30))


# ---------------------------------------------------------------------------
# Azure SQL: sahte pyodbc bağlantısı
# ---------------------------------------------------------------------------
class FakeCursor:
    def __init__(self, log):
        self.log, self.fast_executemany = log, False

    def execute(self, sql, params=()):
        self.log.append(("execute", sql, params))

    def executemany(self, sql, batch):
        self.log.append(("executemany", sql, len(batch), self.fast_executemany))

    def fetchall(self):
        return [(0,)]


class FakeConn:
    def __init__(self):
        self.log, self.committed, self.rolled_back, self.autocommit = [], False, False, False

    def cursor(self):
        return FakeCursor(self.log)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def test_mssql_bulk_insert_batches_and_params():
    conn = FakeConn()
    database = db.Database(conn, "mssql")
    rows = [{"ts": "2026-10-17T09:00:00+03:00", "level": "info", "screen_code": "ODMTFATR", "raw_json": {"a": 1}}] * 2500
    assert database.insert_many("banking_logs", rows) == 2500
    calls = [c for c in conn.log if c[0] == "executemany"]
    assert [c[2] for c in calls] == [1000, 1000, 500] and all(c[3] for c in calls)
    assert "log_id" not in calls[0][1] and calls[0][1].count("?") == len(db.TABLES["banking_logs"]["cols"]) - 1


def test_mssql_load_rolls_back_on_error(out_dir, tmp_path):
    conn = FakeConn()
    with pytest.raises(SystemExit):
        load_all.load_sql(db.Database(conn, "mssql"), out=tmp_path, logs=out_dir / "mercek-logs.ndjson")
    assert conn.rolled_back and not conn.committed
    assert any("NVARCHAR" in c[1] for c in conn.log if c[0] == "execute")


# ---------------------------------------------------------------------------
# AI Search: sahte arama ve embedding
# ---------------------------------------------------------------------------
DIM = 64


class FakeEmbedder:
    def __init__(self):
        self.calls = []

    def embed(self, texts):
        self.calls.append(len(texts))
        out = []
        for t in texts:
            v = [0.0] * DIM
            for w in re.findall(r"\w+", t.lower()):
                v[int(hashlib.md5(w.encode()).hexdigest(), 16) % DIM] += 1
            n = math.sqrt(sum(x * x for x in v)) or 1
            out.append([x / n for x in v])
        return out


class FakeSearch:
    def __init__(self):
        self.indexes, self.docs = {}, {}

    def create_index(self, definition):
        self.indexes[definition["name"]] = definition
        self.docs[definition["name"]] = []

    def upload(self, index, docs):
        self.docs[index].extend(docs)

    def count(self, index):
        return len(self.docs[index])

    def vector_search(self, index, vector, top=5, filter=None):
        docs = self.docs[index]
        if filter:
            field, value = re.match(r"(\w+) eq '([^']*)'", filter).groups()
            docs = [d for d in docs if d.get(field) == value]
        scored = [(sum(a * b for a, b in zip(vector, d["content_vector"])), d["id"]) for d in docs]
        return [{"id": i, "score": round(s, 4)} for s, i in sorted(scored, reverse=True)[:top]]


def test_search_load_and_query(out_dir):
    search, emb = FakeSearch(), FakeEmbedder()
    counts = load_all.load_search(search, emb, DIM, out=out_dir)
    assert counts == {"solutions": 37, "requests": 95, "announcements": 20}
    assert max(emb.calls) <= srch.EMBED_BATCH
    sol = search.indexes["solutions"]
    vec = next(f for f in sol["fields"] if f["name"] == "content_vector")
    assert vec["dimensions"] == DIM and sol["vectorSearch"]["algorithms"][0]["hnswParameters"]["metric"] == "cosine"
    assert all(f.get("analyzer") == "tr.microsoft" for f in sol["fields"] if f.get("searchable") and f["type"] == "Edm.String")
    ctx = vs.Ctx(None, NOW, search, emb)
    top = ctx.find("solutions", "Kurum entegrasyonu zaman aşımı kurumdan yanıt alınamıyor", 3)
    assert top[0]["id"] == "SOL-031"
    results = vs.run_checks(ctx, only=["C"])
    assert {r["label"]: r["status"] for r in results}[f"solutions: \"{vs.C_QUERY}\" en yüksek skor"] in "✓✗"


def test_dim_mismatch_stops(out_dir):
    with pytest.raises(SystemExit):
        load_all.load_search(FakeSearch(), FakeEmbedder(), DIM + 1, out=out_dir)


def test_similarity_conversion():
    assert srch.similarity(1.0) == 1.0 and srch.similarity(1 / 1.65) == 0.35


def test_eval_counting():
    class Fixed:
        def __init__(self, answers):
            self.answers = answers

        def vector_search(self, index, vector, top=5):
            return self.answers.pop(0)

    cases = [{"group": "match", "text": "x", "expected_solution_id": "SOL-001", "reviewed": True}] * 10
    cases += [{"group": "no_match", "text": "y", "reviewed": True}] * 10
    answers = [[{"id": "SOL-001", "score": 0.9}]] * 8 + [[{"id": "SOL-002", "score": 0.9}]] * 2
    answers += [[{"id": "SOL-005", "score": 0.8}]] + [[{"id": "SOL-005", "score": 0.4}]] * 9
    ctx = vs.Ctx(None, NOW, Fixed(list(answers)), FakeEmbedder())
    res = vs.run_eval(ctx, cases)
    assert res[0]["found"] == "8/10" and res[0]["status"] == "✓"
    assert res[1]["found"] == "1/10" and res[1]["status"] == "✓"


# ---------------------------------------------------------------------------
# Otomatik eşitleme (indexer)
# ---------------------------------------------------------------------------
def test_sqlite_search_text_is_generated(loaded):
    database, _ = loaded
    row = database.query("SELECT title, symptom, search_text FROM solutions WHERE solution_id = 'SOL-031'")[0]
    assert row[2].startswith(row[0] + "\n" + row[1])
    assert "search_text" not in [c for c, _, _ in db.TABLES["solutions"]["cols"]]  # uygulama yazmaz


def test_change_tracking_runs_outside_transaction():
    conn = FakeConn()
    db.enable_change_tracking(db.Database(conn, "mssql"))
    stmts = [c[1] for c in conn.log if c[0] == "execute"]
    assert "ALTER DATABASE CURRENT SET CHANGE_TRACKING = ON" in stmts[0]
    assert stmts[1:] == [f"ALTER TABLE {t} ENABLE CHANGE_TRACKING" for t in db.SEARCH_SOURCES]
    assert conn.autocommit is False  # eski hâline döndü


class FakeIndexerSearch(FakeSearch):
    def __init__(self, statuses=None):
        super().__init__()
        self.defs, self.calls = {}, []
        self.statuses = statuses or []

    def put(self, kind, definition):
        self.defs[(kind, definition["name"])] = definition

    def reset_indexer(self, name):
        self.calls.append(("reset", name))

    def run_indexer(self, name):
        self.calls.append(("run", name))

    def indexer_status(self, name):
        return self.statuses.pop(0) if self.statuses else {"status": "success", "items": 1, "failed": 0, "error": None}


def test_setup_indexers_definitions(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://foundry.example/")
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    fake = FakeIndexerSearch()
    names = srch.setup_indexers(fake, DIM, connection="Database=x;ResourceId=/sub/y;")
    assert names == ["mercek-ix-solutions", "mercek-ix-requests", "mercek-ix-announcements"]
    ds = fake.defs[("datasources", "mercek-sql-requests")]
    assert ds["type"] == "azuresql" and ds["container"]["name"] == "requests"
    assert ds["dataChangeDetectionPolicy"]["@odata.type"].endswith("SqlIntegratedChangeTrackingPolicy")
    skill = fake.defs[("skillsets", srch.SKILLSET)]["skills"][0]
    assert skill["inputs"][0]["source"] == "/document/search_text" and skill["dimensions"] == DIM
    assert skill["resourceUri"] == "https://foundry.example" and "apiKey" not in skill  # Managed Identity
    ix = fake.defs[("indexers", "mercek-ix-requests")]
    assert ix["schedule"]["interval"] == "PT5M" and ix["skillsetName"] == srch.SKILLSET
    assert {"sourceFieldName": "request_id", "targetFieldName": "id"} in ix["fieldMappings"]
    assert ix["outputFieldMappings"][0]["targetFieldName"] == "content_vector"
    idx = fake.indexes["requests"]
    assert idx["vectorSearch"]["profiles"][0]["vectorizer"] == srch.VECTORIZER
    assert any(f["name"] == "status" and f["filterable"] for f in idx["fields"])
    assert fake.calls[:2] == [("reset", "mercek-ix-solutions"), ("run", "mercek-ix-solutions")]


def test_connection_string_from_env(monkeypatch):
    monkeypatch.delenv("SEARCH_SQL_CONNECTION", raising=False)
    monkeypatch.setenv("SQL_RESOURCE_ID", "/subscriptions/s/resourceGroups/r/providers/Microsoft.Sql/servers/m")
    monkeypatch.setenv("SQL_DATABASE", "mercek")
    assert srch.sql_connection_string().startswith("Database=mercek;ResourceId=/subscriptions/")
    monkeypatch.delenv("SQL_RESOURCE_ID")
    with pytest.raises(SystemExit):
        srch.sql_connection_string()


def test_wait_indexers():
    busy = {"status": "inProgress", "items": 0, "failed": 0, "error": None}
    ok = {"status": "success", "items": 37, "failed": 0, "error": None}
    fake = FakeIndexerSearch([busy, ok, ok, ok])
    res = srch.wait_indexers(fake, ["a", "b"], sleep=lambda s: None)
    assert res["b"]["items"] == 37
    bad = FakeIndexerSearch([{"status": "persistentFailure", "items": 0, "failed": 3, "error": "x"}])
    with pytest.raises(SystemExit):
        srch.wait_indexers(bad, ["a"], sleep=lambda s: None)


def test_completed_filter_and_sync_check(loaded, out_dir):
    database, _ = loaded
    demo_reset.reset(database, NOW, with_d_plan=True)  # TLP-1043 planli
    search, emb = FakeSearch(), FakeEmbedder()
    load_all.load_search(search, emb, DIM, out=out_dir)
    plan = srch.request_doc({**demo_reset.D_PLAN, "components_json": "[]", "services_json": "[]"})
    plan["content_vector"] = emb.embed([demo_reset.D_TEXT])[0]
    search.docs["requests"].append(plan)  # indexer SQL'deki planlı talebi de alır
    ctx = vs.Ctx(database, NOW, search, emb)
    assert "TLP-1043" in [r["id"] for r in ctx.find("requests", demo_reset.D_TEXT, 5)]
    assert "TLP-1043" not in [r["id"] for r in ctx.find("requests", demo_reset.D_TEXT, 5, srch.COMPLETED_REQUESTS)]
    sync = {r["label"]: r for r in vs.run_checks(ctx, only=["Genel"])}
    row = next(v for k, v in sync.items() if k.startswith("SQL ↔ AI Search"))
    assert row["status"] == "✓", row
