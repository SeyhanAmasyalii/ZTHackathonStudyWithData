"""Foundry agent tanımı: talimat prompts/mercek-chat.md'den, araçlar koddaki tanımlardan.

Talimat portalda elle yazılmaz; scripts/setup_agent.py tanımı Foundry'ye yeni sürüm olarak yükler.
Araçlar `function` türündedir: agent çağırır, backend çalıştırır (hazır AI Search aracı kullanılmaz,
eşik ve sayım kodda kalsın).
"""

from typing import Any

from app.config import Settings
from app.repositories.datav2 import Institution, Screen
from app.services.chat import build_agent_instructions
from app.services.tools import BENZER_COZUM_ARA, HATA_ARA, TOOLS


def agent_tools(settings: Settings) -> list[dict[str, Any]]:
    """Agent'a tanıtılan araçlar (backend'in tools_for kuralıyla aynı)."""
    tools = list(TOOLS)
    if settings.search_endpoint:
        tools.append(HATA_ARA)
        if settings.search_solution_index:
            tools.append(BENZER_COZUM_ARA)
    return [
        {
            "type": "function",
            "name": tool["function"]["name"],
            "description": tool["function"]["description"],
            "parameters": tool["function"]["parameters"],
            # strict=false: isteğe bağlı parametreler var; doğrulamayı araçların kendisi yapar.
            "strict": False,
        }
        for tool in tools
    ]


def agent_definition(
    settings: Settings, screens: tuple[Screen, ...], institutions: tuple[Institution, ...]
) -> dict[str, Any]:
    """PromptAgentDefinition gövdesi (kind=prompt)."""
    return {
        "kind": "prompt",
        "model": settings.chat_deployment,
        "instructions": build_agent_instructions(screens, institutions),
        "tools": agent_tools(settings),
    }
