import json
import re

import httpx
import pytest

from app.clients.llm import LLMReply
from app.clients.search import AzureSearchClient, SearchError
from app.config import REPO_ROOT, Settings
from app.repositories.datav2 import json_catalog
from app.services import tools
from app.services.chat import answer
from app.services.log_index import (
    LogSearch,
    SearchNames,
    datasource_definition,
    index_definition,
    indexer_connection_string,
    indexer_definition,
    search_body,
    skillset_definition,
)
from app.services.tools import ToolContext, run_tool, tools_for
from tests.conftest import FakeLLMClient, tool_call

NOW = json_catalog(REPO_ROOT / "datav2").logs[-1].log_time


SETTINGS = Settings(
    azure_openai_endpoint="https://f.openai.azure.com/openai/v1/",
    azure_openai_api_key="foundry-key",
    sql_server="mercek-sql.database.windows.net",
    sql_user="mercekadmin",
    sql_password="p;a}ss",
)
NAMES = SearchNames("mercek-loglar")


def test_index_definition_has_vectorizer_and_turkish_analyzer():
    definition = index_definition("mercek-loglar", SETTINGS)
    fields = {field["name"]: field for field in definition["fields"]}
    assert fields["id"]["key"] is True
    assert fields["content_vector"]["dimensions"] == 1536
    assert fields["content"]["analyzer"] == "tr.microsoft"
    assert fields["screen_code"]["filterable"] is True
    vectorizer = definition["vectorSearch"]["vectorizers"][0]["azureOpenAIParameters"]
    assert vectorizer["resourceUri"] == "https://f.openai.azure.com"
    assert vectorizer["deploymentId"] == "text-embedding-3-small"
    assert definition["vectorSearch"]["profiles"][0]["vectorizer"] == "foundry"


def test_index_fields_match_sql_view_columns():
    view = (REPO_ROOT / "db" / "search_views.sql").read_text(encoding="utf-8")
    select = view[view.index("SELECT\n    CONCAT_WS") : view.index("FROM g")]
    columns = re.findall(r"(?:AS (\w+)|^    \w+\.(\w+),?$)", select, re.M)
    names = {alias or column for alias, column in columns}
    fields = {field["name"] for field in index_definition("x", SETTINGS)["fields"]}
    assert fields - {"content_vector"} <= names
    assert "hwm" in names


def test_datasource_uses_view_and_high_water_mark():
    connection = indexer_connection_string(SETTINGS)
    assert "Server=tcp:mercek-sql.database.windows.net,1433;" in connection
    assert 'Password="p;a}ss";' in connection
    plain = indexer_connection_string(
        Settings(sql_server="s", sql_user="u", sql_password="Abc{1}x")
    )
    assert "User ID=u;Password=Abc{1}x;" in plain
    quoted = indexer_connection_string(Settings(sql_server="s", sql_user="u", sql_password='a"b'))
    assert 'Password="a""b";' in quoted
    definition = datasource_definition(NAMES, connection)
    assert definition["name"] == "mercek-loglar-sql"
    assert definition["container"]["name"] == "v_hata_turleri"
    assert definition["dataChangeDetectionPolicy"]["highWaterMarkColumnName"] == "hwm"


def test_indexer_connection_string_requires_sql_user():
    with pytest.raises(ValueError):
        indexer_connection_string(Settings(sql_server="x"))


def test_skillset_and_indexer_definitions():
    skill = skillset_definition(NAMES, SETTINGS)["skills"][0]
    assert skill["@odata.type"].endswith("AzureOpenAIEmbeddingSkill")
    assert skill["inputs"][0]["source"] == "/document/content"
    indexer = indexer_definition(NAMES)
    assert indexer["schedule"] == {"interval": "PT5M"}
    assert indexer["dataSourceName"] == "mercek-loglar-sql"
    assert indexer["skillsetName"] == "mercek-loglar-embedding"
    assert indexer["fieldMappings"][0]["mappingFunction"]["name"] == "base64Encode"
    assert indexer["outputFieldMappings"][0]["targetFieldName"] == "content_vector"
    assert "schedule" not in indexer_definition(NAMES, schedule=None)


def test_search_body_is_hybrid_with_text_vector_query():
    body = search_body("abone no", "ODMTTLMT", 5)
    assert body["search"] == "abone no"
    assert body["vectorQueries"] == [
        {"kind": "text", "text": "abone no", "fields": "content_vector", "k": 5}
    ]
    assert body["filter"] == "screen_code eq 'ODMTTLMT'"
    assert "filter" not in search_body("x", None, 3)


class FakeSearch:
    def __init__(self, hits=None, fail=False):
        self.hits = hits or []
        self.fail = fail
        self.calls = []

    def __call__(self, text, screen_code, top):
        self.calls.append((text, screen_code, top))
        if self.fail:
            raise SearchError("servis yok")
        return self.hits


HIT = {
    "screen_code": "ODMTTLMT",
    "screen_name": "Fatura Talimat Bilgileri Giriş",
    "error_number": 110412,
    "error_code": "SUBSCRIBER_NO_INVALID",
    "institution_code": "SU01",
    "institution_name": "İSKİ",
    "message": "Abone numarası 13 hane; ekran 6–12 hane kabul ediyor.",
    "log_count": 400,
    "customer_count": 393,
    "last_seen": "2026-10-17T08:04:47.43+03:00",
    "@search.score": 0.0331,
}


def context(search=None):
    return ToolContext(user_name="elif", now=NOW, logs=(), search_logs=search)


def test_hata_ara_returns_hits_without_personal_fields():
    search = FakeSearch([HIT])
    result = run_tool(
        "hata_ara",
        json.dumps({"description": "abone no olmuyor", "screen_code": "odmttlmt"}),
        context(search),
    )
    assert search.calls == [("abone no olmuyor", "ODMTTLMT", tools.HATA_ARA_TOP)]
    assert result["total"] == 1
    assert result["results"][0]["error_number"] == 110412
    assert result["results"][0]["score"] == 0.0331
    assert "user_name" not in json.dumps(result)


@pytest.mark.parametrize(
    "args",
    [{}, {"description": "  "}, {"description": "x", "screen_code": "ODM'; DROP"}],
)
def test_hata_ara_rejects_bad_input(args):
    result = run_tool("hata_ara", json.dumps(args), context(FakeSearch()))
    assert "error" in result


def test_hata_ara_truncates_long_description():
    search = FakeSearch()
    run_tool("hata_ara", json.dumps({"description": "a" * 1000}), context(search))
    assert len(search.calls[0][0]) == tools.MAX_DESCRIPTION


def test_hata_ara_service_error_is_reported_not_raised():
    result = run_tool("hata_ara", json.dumps({"description": "x"}), context(FakeSearch(fail=True)))
    assert result["error"] == "Hata araması şu an yapılamıyor"


def test_hata_ara_offered_only_when_configured():
    assert "hata_ara" not in [t["function"]["name"] for t in tools_for(context())]
    assert "hata_ara" in [t["function"]["name"] for t in tools_for(context(FakeSearch()))]
    assert run_tool("hata_ara", '{"description": "x"}', context())["error"]


def test_chat_uses_hata_ara_then_answers(data_dir):
    llm = FakeLLMClient(
        [
            tool_call("hata_ara", description="abone numarası kabul edilmiyor"),
            LLMReply(content="ODMTTLMT 110412 görünüyor."),
        ]
    )
    catalog = json_catalog(data_dir)
    reply = answer(
        "abone numarasını kabul etmiyor",
        llm,
        context(FakeSearch([HIT])),
        catalog.screens,
        catalog.institutions,
    )
    assert reply == "ODMTTLMT 110412 görünüyor."
    tool_message = llm.calls[1][-1]
    assert tool_message["role"] == "tool"
    assert json.loads(tool_message["content"])["results"][0]["error_number"] == 110412


def test_log_search_sends_hybrid_query():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["headers"] = request.headers
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"value": [HIT]})

    client = AzureSearchClient(
        Settings(search_endpoint="https://s.search.windows.net/", search_api_key="k"),
        http=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    hits = LogSearch(client, "mercek-loglar")("abone", None, 5)
    assert hits == [HIT]
    assert seen["url"].startswith("https://s.search.windows.net/indexes/mercek-loglar/docs/search")
    assert "api-version=" in seen["url"]
    assert seen["headers"]["api-key"] == "k"
    assert seen["body"]["vectorQueries"][0]["text"] == "abone"


def test_search_client_errors():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="Forbidden")

    client = AzureSearchClient(
        Settings(search_endpoint="https://s.search.windows.net", search_api_key="k"),
        http=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(SearchError, match="403"):
        client.search("x", {})
    with pytest.raises(SearchError):
        AzureSearchClient(Settings())


def test_delete_index_ignores_missing():
    client = AzureSearchClient(
        Settings(search_endpoint="https://s.search.windows.net", search_api_key="k"),
        http=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404, text="no"))),
    )
    client.delete("indexes", "yok")
