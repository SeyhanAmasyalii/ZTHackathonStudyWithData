import pytest
from fastapi.testclient import TestClient

from app.api.chat import get_llm
from app.clients.llm import AzureLLMClient, LLMError, _base_url
from app.config import Settings
from app.main import app


class FakeLLMClient:
    def __init__(self, reply: str = "Merhaba, size nasıl yardımcı olabilirim?", fail: bool = False):
        self.reply = reply
        self.fail = fail
        self.calls: list[tuple[str, str]] = []

    def complete(self, system_prompt: str, user_message: str) -> str:
        self.calls.append((system_prompt, user_message))
        if self.fail:
            raise LLMError("sahte hata")
        return self.reply


@pytest.fixture
def fake_llm():
    fake = FakeLLMClient()
    app.dependency_overrides[get_llm] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_returns_model_reply(fake_llm):
    response = client.post("/api/chat", json={"message": "  merhaba  "})
    assert response.status_code == 200
    assert response.json() == {"reply": "Merhaba, size nasıl yardımcı olabilirim?"}
    system_prompt, user_message = fake_llm.calls[0]
    assert "Mercek" in system_prompt
    assert user_message == "merhaba"


@pytest.mark.parametrize("message", ["", "x" * 2001])
def test_chat_rejects_invalid_message(fake_llm, message):
    response = client.post("/api/chat", json={"message": message})
    assert response.status_code == 422
    assert fake_llm.calls == []


def test_chat_model_error_returns_502(fake_llm):
    fake_llm.fail = True
    response = client.post("/api/chat", json={"message": "merhaba"})
    assert response.status_code == 502
    assert response.json() == {"detail": "Şu an yanıt üretilemiyor."}


def test_chat_without_configuration_returns_503(monkeypatch):
    monkeypatch.setattr(
        "app.api.chat.get_settings",
        lambda: Settings(azure_openai_endpoint="", azure_openai_api_key=""),
    )
    response = client.post("/api/chat", json={"message": "merhaba"})
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
