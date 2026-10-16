from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.api.chat import get_llm
from app.clients.llm import AzureLLMClient, LLMError, _base_url
from app.config import TURKEY_TZ, Settings
from app.main import app
from tests.conftest import FakeLLMClient

client = TestClient(app)


@pytest.fixture
def auth():
    token = client.post("/api/login", json={"user_name": "elif"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def fake_llm():
    fake = FakeLLMClient()
    app.dependency_overrides[get_llm] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_returns_model_reply(fake_llm, auth):
    response = client.post("/api/chat", json={"message": "  merhaba  "}, headers=auth)
    assert response.status_code == 200
    assert response.json() == {"reply": "Merhaba, ben Mercek."}
    system, user = fake_llm.calls[0]
    assert "Mercek" in system["content"]
    assert user == {"role": "user", "content": "merhaba"}


@pytest.mark.parametrize("message", ["", "x" * 2001])
def test_chat_rejects_invalid_message(fake_llm, auth, message):
    response = client.post("/api/chat", json={"message": message}, headers=auth)
    assert response.status_code == 422
    assert fake_llm.calls == []


def test_chat_model_error_returns_502(fake_llm, auth):
    fake_llm.fail = True
    response = client.post("/api/chat", json={"message": "merhaba"}, headers=auth)
    assert response.status_code == 502
    assert response.json() == {"detail": "Şu an yanıt üretilemiyor."}


def test_chat_without_configuration_returns_503(monkeypatch, auth):
    monkeypatch.setattr(
        "app.api.chat.get_settings",
        lambda: Settings(azure_openai_endpoint="", azure_openai_api_key=""),
    )
    response = client.post("/api/chat", json={"message": "merhaba"}, headers=auth)
    assert response.status_code == 503


def test_azure_client_requires_endpoint_and_key():
    with pytest.raises(LLMError, match="AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY"):
        AzureLLMClient(Settings(azure_openai_endpoint="", azure_openai_api_key=""))


@pytest.mark.parametrize(
    ("endpoint", "expected"),
    [
        ("https://ornek.openai.azure.com", "https://ornek.openai.azure.com/openai/v1"),
        ("https://ornek.openai.azure.com/", "https://ornek.openai.azure.com/openai/v1"),
        (
            "https://ornek.services.ai.azure.com/openai/v1",
            "https://ornek.services.ai.azure.com/openai/v1",
        ),
    ],
)
def test_base_url(endpoint, expected):
    assert _base_url(endpoint) == expected


def test_demo_now_default_and_empty():
    assert Settings().now() == datetime(2026, 10, 17, 9, 15, tzinfo=TURKEY_TZ)
    assert Settings(demo_now="").demo_now is None
    assert Settings(demo_now="2026-10-17T10:00").now().tzinfo == TURKEY_TZ


def test_azure_client_parses_tool_calls(caplog):
    """OpenAI SDK'sının gerçek cevap biçimini, ağa çıkmadan sahte HTTP cevabıyla dener."""
    import httpx
    from openai import OpenAI

    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = request.read().decode()
        return httpx.Response(
            200,
            json={
                "id": "x",
                "object": "chat.completion",
                "created": 0,
                "model": "gpt-5.5",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "tool_calls",
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_9",
                                    "type": "function",
                                    "function": {
                                        "name": "kibana_sorgula",
                                        "arguments": '{"only_mine": true}',
                                    },
                                }
                            ],
                        },
                    }
                ],
            },
        )

    llm = AzureLLMClient(
        Settings(
            azure_openai_endpoint="https://ornek.openai.azure.com",
            azure_openai_api_key="gizli-anahtar-123",
            llm_debug=True,
        )
    )
    llm._client = OpenAI(
        base_url="https://ornek.openai.azure.com/openai/v1",
        api_key="k",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with caplog.at_level("INFO", logger="app.clients.llm"):
        reply = llm.chat([{"role": "user", "content": "x"}], [{"type": "function", "function": {}}])

    assert seen["url"] == "https://ornek.openai.azure.com/openai/v1/chat/completions"
    assert '"model":"gpt-5.5"' in seen["body"].replace(" ", "")
    assert reply.content is None
    assert reply.tool_calls[0].name == "kibana_sorgula"
    assert reply.as_message()["tool_calls"][0]["id"] == "call_9"
    assert "MODELE GİDEN" in caplog.text
    assert "MODELDEN DÖNEN" in caplog.text
    assert '"arguments": "{\\"only_mine\\": true}"' in caplog.text
    assert "gizli-anahtar-123" not in caplog.text
