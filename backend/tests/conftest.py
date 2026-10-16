import json
from collections.abc import Callable

import pytest

from app.clients.llm import LLMError, LLMReply, ToolCall
from app.config import REPO_ROOT


class FakeLLMClient:
    """Önceden yazılmış cevapları sırayla döner; gelen mesajları kaydeder."""

    def __init__(self, replies: list[LLMReply] | None = None, fail: bool = False):
        self.replies = list(replies or [LLMReply(content="Merhaba, ben Mercek.")])
        self.fail = fail
        self.calls: list[list[dict]] = []

    def chat(self, messages, tools):
        self.calls.append([dict(m) for m in messages])
        if self.fail:
            raise LLMError("sahte hata")
        return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]


def tool_call(name: str, call_id: str = "call_1", **arguments) -> LLMReply:
    return LLMReply(
        content=None,
        tool_calls=[ToolCall(id=call_id, name=name, arguments=json.dumps(arguments))],
    )


@pytest.fixture
def data_dir():
    return REPO_ROOT / "datav2"


@pytest.fixture
def make_fake() -> Callable[..., FakeLLMClient]:
    return FakeLLMClient
