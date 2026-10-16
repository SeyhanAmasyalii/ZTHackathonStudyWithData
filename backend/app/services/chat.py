"""Mercek sohbeti: model gerektiğinde araç çağırır, sonunda kullanıcıya cevap yazar."""

import json
import logging
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.clients.llm import LLMClient, LLMError
from app.repositories.datav2 import Institution, Screen
from app.services.tools import TOOLS, ToolContext, run_tool

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).resolve().parents[3] / "prompts" / "mercek-chat.md"
MAX_TURNS = 5


@lru_cache
def _prompt_template() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


def build_system_prompt(
    now: datetime, screens: tuple[Screen, ...], institutions: tuple[Institution, ...]
) -> str:
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
        .replace("{{now}}", now.strftime("%Y-%m-%d %H:%M"))
        .replace("{{screens}}", screen_lines)
        .replace("{{institutions}}", institution_lines)
    )


def answer(
    message: str,
    llm: LLMClient,
    context: ToolContext,
    screens: tuple[Screen, ...],
    institutions: tuple[Institution, ...],
) -> str:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": build_system_prompt(context.now, screens, institutions)},
        {"role": "user", "content": message.strip()},
    ]
    for turn in range(MAX_TURNS):
        reply = llm.chat(messages, TOOLS)
        if not reply.tool_calls:
            if not reply.content:
                raise LLMError("Model boş yanıt döndü")
            return reply.content

        messages.append(reply.as_message())
        for call in reply.tool_calls:
            result = run_tool(call.name, call.arguments, context)
            logger.info(
                "Araç çağrısı: tur=%d ad=%s sonuç=%s",
                turn + 1,
                call.name,
                result.get("total", result.get("error")),
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )
    raise LLMError(f"{MAX_TURNS} turda cevap üretilemedi")
