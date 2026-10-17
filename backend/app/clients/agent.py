"""Foundry Agent Service'teki Mercek agent'ına erişim (Responses API, agent_reference).

Agent'ın talimatı ve araç tanımları Foundry'de durur (kurulum: scripts/setup_agent.py).
Araçları agent seçer, backend çalıştırır: agent `function_call` döner, backend sonucu
`function_call_output` olarak geri verir. Konuşma hafızası `previous_response_id` ile Foundry'de.
Kimlik yalnızca Microsoft Entra (yerelde az login, Azure'da Managed Identity).
"""

import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.clients.llm import LLMError, ToolCall, _debug_log
from app.config import Settings


@dataclass(frozen=True)
class AgentReply:
    response_id: str
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)


class AgentClient(Protocol):
    def respond(
        self, input_items: list[dict[str, Any]], previous_response_id: str | None
    ) -> AgentReply: ...


class PreviousResponseNotFound(LLMError):
    """Foundry önceki cevabı bulamadı (süresi doldu ya da silindi); geçmiş yeniden gönderilir."""


class FoundryAgentClient:
    def __init__(self, settings: Settings) -> None:
        if not settings.foundry_project_endpoint.strip():
            raise LLMError("Eksik ortam değişkeni: FOUNDRY_PROJECT_ENDPOINT")
        # Paketler burada yüklenir: LLM_MODE=chat iken gerekmez.
        from azure.ai.projects import AIProjectClient
        from azure.identity import DefaultAzureCredential

        self._agent = {"name": settings.foundry_agent_name, "type": "agent_reference"}
        self._debug = settings.llm_debug
        project = AIProjectClient(
            endpoint=settings.foundry_project_endpoint.strip(),
            credential=DefaultAzureCredential(),
        )
        self._client = project.get_openai_client(
            timeout=settings.llm_timeout_seconds, max_retries=1
        )

    def respond(
        self, input_items: list[dict[str, Any]], previous_response_id: str | None
    ) -> AgentReply:
        from openai import BadRequestError, NotFoundError, OpenAIError

        if self._debug:
            _debug_log(
                "AGENT'A GİDEN",
                {"previous_response_id": previous_response_id, "input": input_items},
            )
        try:
            options: dict[str, Any] = {}
            if previous_response_id:
                options["previous_response_id"] = previous_response_id
            response = self._client.responses.create(
                input=input_items,
                extra_body={"agent_reference": self._agent},
                **options,
            )
        except (NotFoundError, BadRequestError) as exc:
            if previous_response_id and "previous_response" in str(exc).lower():
                raise PreviousResponseNotFound("Önceki agent cevabı bulunamadı") from exc
            raise LLMError(f"Agent çağrısı başarısız: {type(exc).__name__}") from exc
        except OpenAIError as exc:
            raise LLMError(f"Agent çağrısı başarısız: {type(exc).__name__}") from exc

        calls = [
            ToolCall(id=item.call_id, name=item.name, arguments=item.arguments)
            for item in response.output
            if item.type == "function_call"
        ]
        reply = AgentReply(response.id, response.output_text or None, calls)
        if self._debug:
            _debug_log(
                "AGENT'TAN DÖNEN",
                {
                    "response_id": reply.response_id,
                    "content": reply.content,
                    "tool_calls": [
                        {"id": c.id, "name": c.name, "arguments": c.arguments}
                        for c in reply.tool_calls
                    ],
                },
            )
        return reply


def function_call_output(call_id: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function_call_output",
        "call_id": call_id,
        "output": json.dumps(result, ensure_ascii=False),
    }
