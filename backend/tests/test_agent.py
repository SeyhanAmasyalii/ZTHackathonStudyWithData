import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.api.chat import get_agent, get_llm
from app.clients.agent import AgentReply, FoundryAgentClient, PreviousResponseNotFound
from app.clients.llm import LLMError, ToolCall
from app.config import REPO_ROOT, TURKEY_TZ, Settings
from app.main import app
from app.models.chat import HistoryMessage
from app.repositories.app_store import MemoryAppStore, get_app_store
from app.repositories.datav2 import json_catalog
from app.services.agent_setup import agent_definition, agent_tools
from app.services.chat import answer_with_agent, build_agent_instructions
from app.services.tools import ToolContext

NOW = datetime(2026, 10, 17, 9, 15, tzinfo=TURKEY_TZ)
CATALOG = json_catalog(REPO_ROOT / "datav2")


class FakeAgent:
    """Önceden yazılmış cevapları sırayla döner; gelen girdileri kaydeder."""

    def __init__(self, replies=None, lose_previous=False):
        self.replies = list(replies or [AgentReply("resp_1", "Merhaba, ben Mercek.")])
        self.lose_previous = lose_previous
        self.calls: list[tuple[list[dict], str | None]] = []

    def respond(self, input_items, previous_response_id):
        self.calls.append((input_items, previous_response_id))
        if self.lose_previous and previous_response_id:
            raise PreviousResponseNotFound("yok")
        return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]


def context() -> ToolContext:
    return ToolContext(
        user_name="elif",
        user_role="Şube Müşteri Temsilcisi · 601 Kızılay",
        now=NOW,
        logs=CATALOG.logs,
        incidents=CATALOG.incidents,
    )


def kibana_call(call_id="call_1"):
    args = {
        "start_time": "2026-10-17T08:45",
        "end_time": "2026-10-17T09:15",
        "only_mine": True,
        "screen_code": "ODMTTLMT",
    }
    return ToolCall(id=call_id, name="kibana_sorgula", arguments=json.dumps(args))


def test_agent_runs_tools_in_backend_and_chains_responses():
    agent = FakeAgent(
        [
            AgentReply("resp_1", None, [kibana_call()]),
            AgentReply("resp_2", "ODMTTLMT'de 7 hata var."),
        ]
    )
    trace: list = []
    reply, response_id = answer_with_agent(
        "ODMTTLMT ekranında hata alıyorum", agent, context(), trace=trace
    )
    assert (reply, response_id) == ("ODMTTLMT'de 7 hata var.", "resp_2")
    first_input, first_previous = agent.calls[0]
    assert first_previous is None
    assert first_input[0]["role"] == "developer"
    assert "2026-10-17 09:15" in first_input[0]["content"]
    assert "elif" not in first_input[0]["content"]  # kullanıcı kodu modele gitmez
    assert first_input[1] == {
        "type": "message",
        "role": "user",
        "content": "ODMTTLMT ekranında hata alıyorum",
    }
    assert all(item["type"] == "message" for item in first_input)
    # Araç sonucu backend'de hesaplanır, function_call_output olarak önceki cevaba eklenir.
    second_input, second_previous = agent.calls[1]
    assert second_previous == "resp_1"
    output = second_input[0]
    assert output["type"] == "function_call_output" and output["call_id"] == "call_1"
    assert json.loads(output["output"])["total"] == 7
    assert trace[0][0] == "kibana_sorgula"


def test_agent_uses_previous_response_without_resending_history():
    agent = FakeAgent()
    history = [HistoryMessage(role="user", content="önceki soru")]
    answer_with_agent("peki ya dün?", agent, context(), history, previous_response_id="resp_9")
    items, previous = agent.calls[0]
    assert previous == "resp_9"
    assert [item["role"] for item in items] == ["developer", "user"]


def test_agent_replays_history_when_previous_response_is_lost():
    agent = FakeAgent(lose_previous=True)
    history = [
        HistoryMessage(role="user", content="ODMTTLMT hatası"),
        HistoryMessage(role="assistant", content="7 hata var."),
    ]
    reply, _ = answer_with_agent("peki nasıl çözerim?", agent, context(), history, "resp_old")
    assert reply == "Merhaba, ben Mercek."
    items, previous = agent.calls[1]
    assert previous is None
    assert [item["content"] for item in items[:2]] == ["ODMTTLMT hatası", "7 hata var."]
    assert items[-1]["content"] == "peki nasıl çözerim?"


def test_agent_empty_reply_and_turn_limit_raise():
    with pytest.raises(LLMError):
        answer_with_agent("x", FakeAgent([AgentReply("r", None)]), context())
    looping = FakeAgent([AgentReply("r", None, [kibana_call()])])
    with pytest.raises(LLMError):
        answer_with_agent("x", looping, context())


def test_agent_instructions_have_static_context():
    instructions = build_agent_instructions(CATALOG.screens, CATALOG.institutions)
    assert "{{" not in instructions
    assert "BAĞLAM" in instructions
    assert "ODMTTLMT" in instructions and "GAZ02" in instructions


def test_agent_tools_follow_search_settings():
    def names(settings):
        return [tool["name"] for tool in agent_tools(settings)]

    assert names(Settings()) == ["kibana_sorgula", "cagri_ara"]
    assert names(Settings(search_endpoint="https://s")) == [
        "kibana_sorgula",
        "cagri_ara",
        "hata_ara",
    ]
    full = Settings(search_endpoint="https://s", search_solution_index="mercek-cozumler")
    assert names(full)[-1] == "benzer_cozum_ara"
    definition = agent_definition(full, CATALOG.screens, CATALOG.institutions)
    assert definition["kind"] == "prompt" and definition["model"] == "gpt-5.5"
    tool = definition["tools"][0]
    assert tool["type"] == "function" and tool["strict"] is False
    assert tool["parameters"]["type"] == "object"


def test_foundry_agent_client_requires_endpoint():
    with pytest.raises(LLMError, match="FOUNDRY_PROJECT_ENDPOINT"):
        FoundryAgentClient(Settings(foundry_project_endpoint=""))


def test_memory_store_keeps_agent_response_id():
    store = MemoryAppStore()
    conversation_id = store.create_conversation("elif")
    assert store.get_agent_response_id(conversation_id) is None
    store.set_agent_response_id(conversation_id, "resp_1")
    assert store.get_agent_response_id(conversation_id) == "resp_1"


def test_chat_endpoint_in_agent_mode_stores_response_id():
    client = TestClient(app)
    agent = FakeAgent([AgentReply("resp_1", "İlk cevap"), AgentReply("resp_2", "İkinci cevap")])
    store = MemoryAppStore()
    app.dependency_overrides[get_llm] = lambda: None
    app.dependency_overrides[get_agent] = lambda: agent
    app.dependency_overrides[get_app_store] = lambda: store
    try:
        token = client.post("/api/login", json={"user_name": "elif"}).json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        first = client.post("/api/chat", json={"message": "merhaba"}, headers=headers).json()
        assert first["reply"] == "İlk cevap"
        conversation_id = first["conversation_id"]
        assert store.get_agent_response_id(conversation_id) == "resp_1"

        second = client.post(
            "/api/chat",
            json={"message": "devam", "conversation_id": conversation_id},
            headers=headers,
        ).json()
        assert second["reply"] == "İkinci cevap"
        assert agent.calls[1][1] == "resp_1"  # önceki tur Foundry'den hatırlanır
        assert store.get_agent_response_id(conversation_id) == "resp_2"
        # Ekrana geri yükleme SQL'den: yalnızca kullanıcı ve asistan mesajları.
        stored = store.get_conversation(conversation_id, "elif")
        assert [m.content for m in stored] == ["merhaba", "İlk cevap", "devam", "İkinci cevap"]
    finally:
        app.dependency_overrides.clear()
