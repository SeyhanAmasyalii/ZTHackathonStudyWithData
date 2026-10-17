import json
import re

import httpx
import pytest

from app.clients.search import AzureSearchClient
from app.config import REPO_ROOT, Settings
from app.services import solution_index
from app.services.log_index import SearchNames, datasource_definition
from app.services.solution_index import (
    SolutionSearch,
    cosine_from_score,
    index_definition,
    match_score,
    parse_steps,
    search_body,
)
from app.services.tools import ToolContext, run_tool, tools_for

SETTINGS = Settings(
    azure_openai_endpoint="https://f.openai.azure.com/openai/v1/",
    azure_openai_api_key="foundry-key",
)
NOW = __import__("datetime").datetime(2026, 10, 17, 9, 15)


def score_for(cosine: float) -> float:
    """AI Search'ün cosine puanı: 1 / (1 + (1 - cos))."""
    return 1 / (2 - cosine)


HIT = {
    "@search.score": score_for(0.664),
    "solution_template_id": "SOL-026",
    "title": "Adres güncellemede zorunlu alan boş",
    "symptom": "Adres güncellemesi kaydedilemiyor.",
    "root_cause": "İlçe gibi zorunlu alan boş.",
    "steps": '["Eksik alanı tamamla.", "Özeti kontrol edip kaydet."]',
    "error_code": "VALIDATION_ERROR",
    "closure_code": "KULLANICI_KAYNAKLI",
    "sub_closure_code": "KULLANICI_HATASI",
    "department_id": "MUSTERI_YONETIM",
    "closed_count": 12,
}
WEAK_HIT = {**HIT, "@search.score": score_for(0.585), "solution_template_id": "SOL-001"}


class FakeSolutions:
    def __init__(self, hits=None, fail=False):
        self.hits = hits or []
        self.fail = fail
        self.calls = []

    def __call__(self, text, top):
        self.calls.append((text, top))
        if self.fail:
            raise RuntimeError("503")
        return self.hits


def context(search=None) -> ToolContext:
    return ToolContext(user_name="elif", now=NOW, logs=(), search_solutions=search)


def test_cosine_from_score_inverts_ai_search_formula():
    for cosine in (0.2, 0.5, 0.75, 1.0):
        assert cosine_from_score(score_for(cosine)) == pytest.approx(cosine)
    assert cosine_from_score(0) == 0.0


def test_match_score_scales_and_adds_error_code_bonus():
    floor, ceil = solution_index.SIMILARITY_FLOOR, solution_index.SIMILARITY_CEIL
    assert match_score(floor, None, "X") == 0.0
    assert match_score(ceil, None, "X") == 1.0
    middle = (floor + ceil) / 2
    assert match_score(middle, None, "X") == pytest.approx(0.5)
    with_code = match_score(middle, "VALIDATION_ERROR", "VALIDATION_ERROR")
    assert with_code == pytest.approx(0.5 + solution_index.ERROR_CODE_BONUS)
    assert match_score(middle, "OTHER", "VALIDATION_ERROR") == pytest.approx(0.5)
    assert match_score(1.0, "X", "X") == 1.0


def test_parse_steps():
    assert parse_steps('["a", "b"]') == ["a", "b"]
    assert parse_steps("düz metin") == ["düz metin"]
    assert parse_steps(None) == []


def test_benzer_cozum_ara_marks_threshold_in_code():
    search = FakeSolutions([WEAK_HIT, HIT])
    result = run_tool(
        "benzer_cozum_ara", json.dumps({"description": "adres kaydedilmiyor"}), context(search)
    )
    assert result["threshold_percent"] == 75
    assert result["matched"] is True
    best, weak = result["results"]
    assert best["solution_template_id"] == "SOL-026"
    assert best["match_percent"] == 83
    assert best["above_threshold"] is True
    assert best["steps"] == ["Eksik alanı tamamla.", "Özeti kontrol edip kaydet."]
    assert best["closed_incident_count"] == 12
    assert weak["above_threshold"] is False
    assert search.calls == [("adres kaydedilmiyor", 3)]


def test_benzer_cozum_ara_no_match_below_threshold():
    result = run_tool(
        "benzer_cozum_ara",
        '{"description": "Input string was not in a correct format"}',
        context(FakeSolutions([WEAK_HIT])),
    )
    assert result["matched"] is False
    assert result["results"][0]["match_percent"] == 58


def test_benzer_cozum_ara_error_code_can_lift_over_threshold():
    hit = {**HIT, "@search.score": score_for(0.573)}  # %54 (SOL-031 ölçümü)
    args = {"description": "adres", "error_code": "validation_error"}
    result = run_tool("benzer_cozum_ara", json.dumps(args), context(FakeSolutions([hit])))
    assert result["query"]["error_code"] == "VALIDATION_ERROR"
    assert result["results"][0]["match_percent"] == 79
    assert result["matched"] is True


@pytest.mark.parametrize(
    "args",
    [{}, {"description": ""}, {"description": "x", "error_code": "drop table;"}],
)
def test_benzer_cozum_ara_rejects_bad_input(args):
    assert "error" in run_tool("benzer_cozum_ara", json.dumps(args), context(FakeSolutions()))


def test_benzer_cozum_ara_truncates_and_survives_errors():
    search = FakeSolutions()
    run_tool("benzer_cozum_ara", json.dumps({"description": "a" * 1000}), context(search))
    assert len(search.calls[0][0]) == 300
    failed = run_tool("benzer_cozum_ara", '{"description": "x"}', context(FakeSolutions(fail=True)))
    assert failed["error"] == "Çözüm araması şu an yapılamıyor"


def test_benzer_cozum_ara_offered_only_when_configured():
    names = lambda ctx: [t["function"]["name"] for t in tools_for(ctx)]  # noqa: E731
    assert "benzer_cozum_ara" not in names(context())
    assert "benzer_cozum_ara" in names(context(FakeSolutions()))
    assert run_tool("benzer_cozum_ara", '{"description": "x"}', context())["error"]


def test_index_fields_match_sql_view_columns():
    view = (REPO_ROOT / "db" / "search_views.sql").read_text(encoding="utf-8")
    body = view[view.index("CREATE OR ALTER VIEW dbo.v_cozum_sablonlari") :]
    start = body.index("SELECT\n    t.solution_template_id AS id")
    select = body[start : body.index("FROM dbo.solution_templates", start)]
    columns = re.findall(r"(?:AS (\w+)|^    \w+\.(\w+),?$)", select, re.M)
    names = {alias or column for alias, column in columns}
    fields = {field["name"] for field in index_definition("x", SETTINGS)["fields"]}
    assert fields - {"content_vector"} <= names
    assert "hwm" in names
    # Kişisel veri indekse girmez.
    assert "customer_number" not in body and "reporter_user_name" not in body


def test_datasource_points_to_solution_view():
    definition = datasource_definition(
        SearchNames("mercek-cozumler"), "cs", solution_index.SQL_VIEW
    )
    assert definition["name"] == "mercek-cozumler-sql"
    assert definition["container"]["name"] == "v_cozum_sablonlari"


def test_solution_search_sends_vector_only_query():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"value": [HIT]})

    client = AzureSearchClient(
        Settings(search_endpoint="https://s.search.windows.net", search_api_key="k"),
        http=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert SolutionSearch(client, "mercek-cozumler")("adres", 3) == [HIT]
    assert "/indexes/mercek-cozumler/docs/search" in seen["url"]
    assert seen["body"] == search_body("adres", 3)
    assert "search" not in seen["body"]  # hibrit değil: puan cosine'e çevrilebilsin
    assert seen["body"]["vectorQueries"][0]["k"] == 3
