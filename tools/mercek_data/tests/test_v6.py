"""V6 testleri: temaslar, çağrı kayıtları, çözümler, geçmiş talepler, değerlendirme seti."""
import importlib.util
import json
import re
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[2]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gen = _load("generate_banking_logs", TOOLS / "generate_banking_logs.py")
inj = _load("inject_log_scenarios", TOOLS / "mercek_data" / "inject_log_scenarios.py")
gp = _load("generate_portfolio", TOOLS / "mercek_data" / "generate_portfolio.py")
gi = _load("generate_incidents", TOOLS / "mercek_data" / "generate_incidents.py")
gr = _load("generate_requests", TOOLS / "mercek_data" / "generate_requests.py")
END = gen.parse_end("2026-10-17T09:00:00+03:00")


@pytest.fixture(scope="module")
def chain(tmp_path_factory):
    d = tmp_path_factory.mktemp("v6")
    base, logs = d / "base.ndjson", d / "mercek.ndjson"
    gen.write_records(gen.generate(10000, 30, 42, 800, END), base, "ndjson", gen.DEFAULT_INDEX)
    inj.run(base, logs, END, 42)
    pf = gp.build(42, logs)
    gp.write_csv(d / "customers.csv", pf["customers"], gp.CUSTOMER_FIELDS)
    gp.write_csv(d / "loans.csv", pf["loans"], gp.LOAN_FIELDS)
    result = gi.build(42, d / "customers.csv", logs)
    gi.write_csv(d / "solutions.csv", result["solutions"], gi.SOLUTION_FIELDS)
    requests = gr.build_requests(42)
    ev = gr.build_eval(42, requests, d / "solutions.csv")
    return {"dir": d, "logs": logs, **result, "requests": requests, "eval": ev}


def test_scenario_numbers(chain):
    s = gi.summarize(chain["contacts"], chain["incidents"], chain["solutions"])
    for k, v in gi.EXPECTED.items():
        assert s[k] == v, k
    assert s["d_counts"] == gi.D_SUBCATS


def test_c_incidents_match_logs(chain):
    iski = {no: (sub, trace) for no, sub, trace in gi.iski_customers(chain["logs"])}
    c = [r for r in chain["incidents"] if r["subcategory"] == gi.C_SUBCAT]
    assert len(c) == 23
    for r in c:
        assert r["customer_number"] in iski
        assert (r["subscriber_no"], r["trace_id"]) == iski[r["customer_number"]]
        assert r["service_id"] == "FATURA_ODEME" and r["solution_id"] == ""


def test_b_history_and_demo_window_free(chain):
    b = [r for r in chain["incidents"] if r["solution_id"] == "SOL-031"]
    assert len(b) == 6 and all(r["error_code"] == "INSTITUTION_TIMEOUT" for r in b)
    assert all(45 <= int(r["resolution_minutes"]) <= 120 for r in b)
    open_baskent = [r for r in chain["incidents"] if r["institution"] == "Başkentgaz" and r["status"] == "acik"]
    assert not open_baskent  # CAG-2051 yalnızca demo_reset ile açılır


def test_services_follow_rules(chain):
    services = {s["service_id"] for s in json.loads((gi.SEED / "catalog.json").read_text(encoding="utf-8"))["services"]}
    assert all(r["service_id"] in services for r in chain["incidents"])


def test_solutions(chain):
    ids = [s["solution_id"] for s in chain["solutions"]]
    assert len(ids) == 37 and len(set(ids)) == 37 and "SOL-031" in ids
    for s in chain["solutions"]:
        assert not re.search(r"abone numaras|\bhane", s["title"] + s["symptom"] + s["root_cause"] + s["steps"], re.I)


def test_requests(chain):
    rows = chain["requests"]
    assert len(rows) == 95
    assert [r["request_id"] for r in rows] == sorted(r["request_id"] for r in rows)
    assert all("TLP-0500" <= r["request_id"] <= "TLP-1037" for r in rows)
    flagged = {r["request_id"] for r in rows if re.search(r"hatırlatma|erteleme|ertelen", r["title"] + r["description"], re.I)}
    assert flagged <= set(gr.FIXED)
    by_id = {r["request_id"]: r for r in rows}
    d_efforts = sorted(int(by_id[i]["effort_md"]) for i in ("TLP-0871", "TLP-0915", "TLP-0962"))
    assert d_efforts[1] == 11  # otomatik bileşen medyanı
    assert json.loads(by_id["TLP-0588"]["service_efforts_json"]) == {"KREDI_TAKIP": 8, "KREDI_KULLANDIRIM": 3, "MUSTERI_YONETIM": 4}
    dates = [r["created_at"] for r in rows]
    assert dates == sorted(dates)


def test_eval_set(chain):
    cases = chain["eval"]["cases"]
    groups = [c["group"] for c in cases]
    assert (groups.count("match"), groups.count("no_match"), groups.count("request")) == (10, 10, 10)
    assert all(c["leak_check"] for c in cases)
    sol_ids = {s["solution_id"] for s in chain["solutions"]}
    assert all(c["expected_solution_id"] in sol_ids for c in cases if c["group"] == "match")


def test_incident_subcategory_matches_error(chain):
    """Arka plan çağrılarında alt kategori hata koduyla tutarlı olmalı (ör. yetersiz bakiye ≠ dekont)."""
    allowed = {
        "INSUFFICIENT_BALANCE": {"yetersiz bakiye", "havale/EFT gerçekleşmedi"},
        "INSTITUTION_TIMEOUT": {"kurumdan yanıt alınamadı"},
        "AFFORDABILITY_EXCEEDED": {"kullandırım yapılamadı"},
        "INSUFFICIENT_INCOME": {"başvuru reddedildi"},
        "KYC_CHECK_FAILED": {"kimlik doğrulama başarısız", "hesap açılamadı"},
    }
    for r in chain["incidents"]:
        if r["error_code"] in allowed:
            assert r["subcategory"] in allowed[r["error_code"]], (r["incident_id"], r["error_code"], r["subcategory"])
    pairs = {(r["subcategory"], r["note"]) for r in chain["incidents"]}
    assert all("dekont" not in note.lower() for sub, note in pairs if sub == "yetersiz bakiye")
    contact_subs = {r["subcategory"] for r in chain["contacts"]}
    assert not contact_subs & gi.INCIDENT_ONLY_SUBCATS
