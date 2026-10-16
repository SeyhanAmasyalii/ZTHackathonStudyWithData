"""Mercek sohbeti: kullanıcı mesajını modele iletir."""

from functools import lru_cache
from pathlib import Path

from app.clients.llm import LLMClient

PROMPT_PATH = Path(__file__).resolve().parents[3] / "prompts" / "mercek-chat.md"


@lru_cache
def load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


def answer(message: str, llm: LLMClient) -> str:
    return llm.complete(load_system_prompt(), message.strip())
