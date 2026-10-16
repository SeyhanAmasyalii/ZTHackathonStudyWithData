"""Azure AI Foundry'deki sohbet modeline erişim."""

from dataclasses import dataclass, field
from typing import Any, Protocol

from openai import OpenAI, OpenAIError

from app.config import Settings


class LLMError(Exception):
    """Model çağrısı başarısız oldu ya da yapılandırma eksik."""


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: str  # model JSON metni olarak verir


@dataclass(frozen=True)
class LLMReply:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)

    def as_message(self) -> dict[str, Any]:
        """Konuşma geçmişine eklenecek asistan mesajı."""
        message: dict[str, Any] = {"role": "assistant", "content": self.content}
        if self.tool_calls:
            message["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": call.arguments},
                }
                for call in self.tool_calls
            ]
        return message


class LLMClient(Protocol):
    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LLMReply: ...


def _base_url(endpoint: str) -> str:
    endpoint = endpoint.strip().rstrip("/")
    if endpoint.endswith("/openai/v1"):
        return endpoint
    return f"{endpoint}/openai/v1"


class AzureLLMClient:
    """Foundry'deki deploy'a OpenAI v1 uyumlu uç üzerinden bağlanır."""

    def __init__(self, settings: Settings) -> None:
        missing = [
            name
            for name, value in (
                ("AZURE_OPENAI_ENDPOINT", settings.azure_openai_endpoint),
                ("AZURE_OPENAI_API_KEY", settings.azure_openai_api_key),
            )
            if not value.strip()
        ]
        if missing:
            raise LLMError(f"Eksik ortam değişkeni: {', '.join(missing)}")

        self._deployment = settings.chat_deployment
        self._client = OpenAI(
            base_url=_base_url(settings.azure_openai_endpoint),
            api_key=settings.azure_openai_api_key,
            timeout=settings.llm_timeout_seconds,
            max_retries=1,
        )

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LLMReply:
        try:
            response = self._client.chat.completions.create(
                model=self._deployment,
                messages=messages,
                tools=tools,
            )
        except OpenAIError as exc:
            raise LLMError(f"Model çağrısı başarısız: {type(exc).__name__}") from exc

        if not response.choices:
            raise LLMError("Model boş yanıt döndü")
        message = response.choices[0].message
        calls = [
            ToolCall(id=call.id, name=call.function.name, arguments=call.function.arguments)
            for call in (message.tool_calls or [])
            if call.type == "function"
        ]
        return LLMReply(content=message.content, tool_calls=calls)
