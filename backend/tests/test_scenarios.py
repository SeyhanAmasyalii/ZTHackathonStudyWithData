import json

from fastapi.testclient import TestClient

from app.api.chat import get_llm
from app.clients.llm import LLMReply
from app.config import REPO_ROOT
from app.main import app
from app.repositories.app_store import (
    MemoryAppStore,
    SqlAppStore,
    StoredMessage,
    _decode_extras,
    _encode_extras,
    get_app_store,
)
from app.repositories.datav2 import json_catalog
from app.services.scenarios import safe_url, scenario_links, scenario_map
from tests.conftest import FakeLLMClient, tool_call

CATALOG = json_catalog(REPO_ROOT / "datav2")
MAPPING = scenario_map(CATALOG.incidents)


def test_scenario_map_from_incidents():
    assert MAPPING["SOL-031"].endswith("/tour/bankacilik/ODMTTLMT/odm-baskentgaz-zaman-asimi")
    assert all(url.startswith("https://") for url in MAPPING.values())


def test_safe_url_rejects_non_https_and_credentials():
    assert safe_url("https://a.example/tour/x") == "https://a.example/tour/x"
    assert safe_url("http://a.example/tour/x") is None
    assert safe_url("javascript:alert(1)") is None
    assert safe_url("https://user:pw@a.example/x") is None
    assert safe_url("/tour/x") is None
    assert safe_url(None) is None


def test_links_from_cagri_ara_and_matched_benzer_cozum_ara():
    trace = [
        ("kibana_sorgula", {"total": 7}),
        ("cagri_ara", {"by_solution": [{"solution_template_id": "SOL-031", "title": "Kurum"}]}),
        (
            "benzer_cozum_ara",
            {
                "results": [
                    {"solution_template_id": "SOL-026", "title": "Adres", "above_threshold": True},
                    {"solution_template_id": "SOL-027", "title": "Tel", "above_threshold": False},
                ]
            },
        ),
    ]
    links = scenario_links(trace, MAPPING)
    assert [link["solution_template_id"] for link in links] == ["SOL-026", "SOL-031"]
    assert links[1]["url"] == MAPPING["SOL-031"]


def test_no_links_for_errors_or_unknown_templates():
    assert scenario_links([("cagri_ara", {"error": "x"})], MAPPING) == []
    unknown = [("cagri_ara", {"by_solution": [{"solution_template_id": "SOL-999"}]})]
    assert scenario_links(unknown, MAPPING) == []


def test_extras_encoding_is_backward_compatible():
    affected = {"customer_count": 3}
    links = [{"solution_template_id": "SOL-031", "title": "t", "url": "https://a/x"}]
    assert _decode_extras(json.dumps(affected)) == (affected, None)  # eski kayıt
    assert _decode_extras(_encode_extras(StoredMessage("assistant", "c", affected, links))) == (
        affected,
        links,
    )
    assert _decode_extras(_encode_extras(StoredMessage("assistant", "c", None, links))) == (
        None,
        links,
    )
    assert _encode_extras(StoredMessage("assistant", "c")) is None
    assert SqlAppStore  # SQL deposu aynı kodlamayı kullanır


def test_chat_returns_and_restores_scenario_links():
    client = TestClient(app)
    llm = FakeLLMClient(
        [
            tool_call("cagri_ara", screen_code="ODMTTLMT", error_number=110731),
            LLMReply(content="SOL-031 adımları; aşağıdaki akıştan izleyebilirsiniz."),
        ]
    )
    store = MemoryAppStore()
    app.dependency_overrides[get_llm] = lambda: llm
    app.dependency_overrides[get_app_store] = lambda: store
    try:
        token = client.post("/api/login", json={"user_name": "elif"}).json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        body = client.post("/api/chat", json={"message": "talimat hatası"}, headers=headers).json()
        link = body["scenario_links"][0]
        assert link["solution_template_id"] == "SOL-031"
        assert link["url"] == MAPPING["SOL-031"]
        # Bağlantı modele gitmez: araç sonucunda adres yok.
        tool_message = llm.calls[1][-1]
        assert "https://" not in tool_message["content"]

        restored = client.get(
            f"/api/conversations/{body['conversation_id']}", headers=headers
        ).json()
        assert restored["messages"][1]["scenario_links"][0]["url"] == MAPPING["SOL-031"]
    finally:
        app.dependency_overrides.clear()
