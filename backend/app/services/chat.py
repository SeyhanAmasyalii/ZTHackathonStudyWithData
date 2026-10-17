"""Mercek sohbeti: model gerektiğinde araç çağırır, sonunda kullanıcıya cevap yazar."""

import json
import logging
from collections.abc import Sequence
from datetime import datetime
from functools import lru_cache
from typing import Any

from app.clients.agent import AgentClient, PreviousResponseNotFound, function_call_output
from app.clients.llm import LLMClient, LLMError
from app.config import get_settings
from app.models.chat import HistoryMessage
from app.repositories.datav2 import Institution, Screen
from app.services.tools import ToolContext, run_tool, tools_for

logger = logging.getLogger(__name__)

# Bir soruda araç zinciri: hata_ara → kibana_sorgula (kendi) → kibana_sorgula (herkes) → cagri_ara
# → benzer_cozum_ara → cevap = 6 tur; pay bırakılır.
MAX_TURNS = 8


@lru_cache
def _prompt_template() -> str:
    path = get_settings().prompts_dir / "mercek-chat.md"
    return path.read_text(encoding="utf-8").strip()


# Agent'ın talimatı sabittir (Foundry'de saklanır); saat ve görev her turda BAĞLAM mesajıyla gelir.
AGENT_NOW = "her kullanıcı mesajından önceki BAĞLAM mesajında"
AGENT_USER_ROLE = "BAĞLAM mesajında"


def build_system_prompt(
    now: datetime | str,
    screens: tuple[Screen, ...],
    institutions: tuple[Institution, ...],
    user_role: str = "",
) -> str:
    now_text = now if isinstance(now, str) else now.strftime("%Y-%m-%d %H:%M")
    screen_lines = "\n".join(
        f"{screen.code} · {screen.name} — {screen.description}" for screen in screens
    )
    institution_lines = "\n".join(
        f"{inst.code} · {inst.name} ({inst.bill_type}) → ekran: "
        f"{', '.join(inst.screen_codes) or '-'}"
        for inst in institutions
    )
    return (
        _prompt_template()
        .replace("{{now}}", now_text)
        .replace("{{user_role}}", user_role or "belirtilmedi")
        .replace("{{screens}}", screen_lines)
        .replace("{{institutions}}", institution_lines)
    )


def build_agent_instructions(
    screens: tuple[Screen, ...], institutions: tuple[Institution, ...]
) -> str:
    """Foundry agent talimatı: aynı prompt; saat ve görev yerine BAĞLAM mesajına yönlendirme."""
    return build_system_prompt(AGENT_NOW, screens, institutions, AGENT_USER_ROLE)


def context_message(context: ToolContext) -> dict[str, Any]:
    """Agent yolunda her turdaki değişken bilgi (kullanıcı kodu değil, görev bilgisi)."""
    return {
        "type": "message",
        "role": "developer",
        "content": (
            f"BAĞLAM — Şu an: {context.now.strftime('%Y-%m-%d %H:%M')} (Türkiye saati). "
            f"Kullanıcının görevi: {context.user_role or 'belirtilmedi'}."
        ),
    }


def _run_calls(
    calls: Sequence[Any],
    context: ToolContext,
    turn: int,
    trace: list[tuple[str, dict[str, Any]]] | None,
) -> list[tuple[str, dict[str, Any]]]:
    """Araçları çalıştırır, loglar; (çağrı kimliği, sonuç) listesi döner."""
    results = []
    for call in calls:
        result = run_tool(call.name, call.arguments, context)
        if trace is not None:
            trace.append((call.name, result))
        logger.info(
            "Araç çağrısı: tur=%d ad=%s sorgu=%s sonuç=%s",
            turn + 1,
            call.name,
            json.dumps(result.get("query", call.arguments), ensure_ascii=False),
            result.get("total", result.get("error")),
        )
        results.append((call.id, result))
    return results


def answer_with_agent(
    message: str,
    agent: AgentClient,
    context: ToolContext,
    history: Sequence[HistoryMessage] = (),
    previous_response_id: str | None = None,
    trace: list[tuple[str, dict[str, Any]]] | None = None,
) -> tuple[str, str]:
    """Foundry agent'ıyla cevap; (cevap, son response_id) döner.

    previous_response_id varsa model önceki turları Foundry'den hatırlar, geçmiş gönderilmez.
    Yoksa ya da Foundry bulamazsa SQL'deki geçmiş (history) gönderilir.
    """
    # Agent uç noktası her girdide "type" ister (ör. message, function_call_output).
    user_items = [context_message(context), _message("user", message.strip())]
    try:
        return _agent_loop(agent, context, user_items, previous_response_id, trace)
    except PreviousResponseNotFound:
        logger.warning("Agent önceki cevabı bulamadı; geçmiş yeniden gönderiliyor")
    replay = [_message(item.role, item.content) for item in history]
    return _agent_loop(agent, context, [*replay, *user_items], None, trace)


def _message(role: str, content: str) -> dict[str, Any]:
    return {"type": "message", "role": role, "content": content}


def _agent_loop(
    agent: AgentClient,
    context: ToolContext,
    input_items: list[dict[str, Any]],
    previous_response_id: str | None,
    trace: list[tuple[str, dict[str, Any]]] | None,
) -> tuple[str, str]:
    for turn in range(MAX_TURNS):
        reply = agent.respond(input_items, previous_response_id)
        previous_response_id = reply.response_id
        if not reply.tool_calls:
            if not reply.content:
                raise LLMError("Agent boş yanıt döndü")
            return reply.content, reply.response_id
        input_items = [
            function_call_output(call_id, result)
            for call_id, result in _run_calls(reply.tool_calls, context, turn, trace)
        ]
    raise LLMError(f"{MAX_TURNS} turda cevap üretilemedi")


def answer(
    message: str,
    llm: LLMClient,
    context: ToolContext,
    screens: tuple[Screen, ...],
    institutions: tuple[Institution, ...],
    history: Sequence[HistoryMessage] = (),
    trace: list[tuple[str, dict[str, Any]]] | None = None,
) -> str:
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": build_system_prompt(context.now, screens, institutions, context.user_role),
        },
        # Konuşma hafızası: önceki kullanıcı mesajları ve Mercek'in son cevapları.
        *({"role": item.role, "content": item.content} for item in history),
        {"role": "user", "content": message.strip()},
    ]
    tools = tools_for(context)
    for turn in range(MAX_TURNS):
        reply = llm.chat(messages, tools)
        if not reply.tool_calls:
            if not reply.content:
                raise LLMError("Model boş yanıt döndü")
            return reply.content

        messages.append(reply.as_message())
        for call_id, result in _run_calls(reply.tool_calls, context, turn, trace):
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )
    raise LLMError(f"{MAX_TURNS} turda cevap üretilemedi")
