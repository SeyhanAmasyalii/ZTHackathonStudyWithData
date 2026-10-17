import json

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
    log_documents,
    log_index_definition,
    search_body,
)
from app.services.tools import ToolContext, run_tool, tools_for
from tests.conftest import FakeLLMClient, tool_call

NOW = json_catalog(REPO_ROOT / "datav2").logs[-1].log_time


@pytest.fixture
def documents(data_dir):
    rules = json.loads((data_dir / "error_handling_rules.json").read_text(encoding="utf-8"))
    return log_documents(json_catalog(data_dir), rules)


def test_documents_group_all_error_logs(documents):
    assert len(documents) == 107
    assert sum(doc["log_count"] for doc in documents) == 2002
    assert len({doc["id"] for doc in documents}) == len(documents)
    top = documents[0]
    assert (top["screen_code"], top["error_number"], top["institution_code"]) == (
        "ODMTTLMT",
        110412,
        "SU01",
    )
    assert top["log_count"] == 400
    assert "İSKİ (Su)" in top["content"] and "13 hane" in top["content"]
    assert top["explanation"]  # error_handling_rules ipucu
    assert ".." not in top["content"]
    assert all("user_name" not in doc and "customer_id" not in doc for doc in documents)


def test_index_definition_has_key_vector_and_turkish_analyzer():
    definition = log_index_definition("mercek-loglar", dimensions=8)
    fields = {field["name"]: field for field in definition["fields"]}
    assert fields["id"]["key"] is True
    assert fields["content_vector"]["dimensions"] == 8
    assert fields["content"]["analyzer"] == "tr.microsoft"
    assert fields["screen_code"]["filterable"] is True


def test_document_fields_match_index(documents):
    fields = {field["name"] for field in log_index_definition("x")["fields"]}
    assert set(documents[0]) | {"content_vector"} == fields


def test_search_body_is_hybrid_with_optional_filter():
    body = search_body("abone no", [0.1, 0.2], "ODMTTLMT", 5)
    assert body["search"] == "abone no"
    assert body["vectorQueries"][0]["vector"] == [0.1, 0.2]
    assert body["vectorQueries"][0]["k"] == 5
    assert body["filter"] == "screen_code eq 'ODMTTLMT'"
    assert "filter" not in search_body("x", [0.0], None, 3)


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


class FakeEmbedder:
    def embed(self, texts):
        return [[float(len(text)), 0.0] for text in texts]


def test_log_search_embeds_and_searches():
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
    hits = LogSearch(client, FakeEmbedder(), "mercek-loglar")("abone", None, 5)
    assert hits == [HIT]
    assert seen["url"].startswith("https://s.search.windows.net/indexes/mercek-loglar/docs/search")
    assert "api-version=" in seen["url"]
    assert seen["headers"]["api-key"] == "k"
    assert seen["body"]["vectorQueries"][0]["vector"] == [5.0, 0.0]


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
    client.delete_index("yok")
