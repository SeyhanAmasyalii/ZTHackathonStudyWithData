import json
from datetime import datetime

import pytest

from app.clients.llm import LLMError, LLMReply
from app.config import TURKEY_TZ
from app.repositories.datav2 import load_error_logs, load_institutions, load_screens
from app.services.chat import MAX_TURNS, answer, build_system_prompt
from app.services.tools import ToolContext
from tests.conftest import tool_call

NOW = datetime(2026, 10, 17, 9, 15, tzinfo=TURKEY_TZ)


@pytest.fixture
def context(data_dir):
    return ToolContext(user_name="elif", now=NOW, logs=load_error_logs(data_dir))


@pytest.fixture
def screens(data_dir):
    return load_screens(data_dir)


@pytest.fixture
def institutions(data_dir):
    return load_institutions(data_dir)


def test_system_prompt_has_now_screens_and_institutions(screens, institutions):
    prompt = build_system_prompt(NOW, screens, institutions)
    assert "Şu an: 2026-10-17 09:15" in prompt
    assert (
        "ODMTTLMT · Fatura Talimat Bilgileri Giriş — Kurum ve abone numarasıyla otomatik fatura"
        in prompt
    )
    assert "GAZ02 · Başkentgaz (Doğalgaz) → ekran: ODMTTLMT" in prompt
    assert "{{" not in prompt


def test_answer_without_tool(make_fake, context, screens, institutions):
    fake = make_fake([LLMReply(content="Hangi ekranda hata alıyorsunuz?")])
    assert (
        answer("hata alıyorum", fake, context, screens, institutions)
        == "Hangi ekranda hata alıyorsunuz?"
    )
    assert len(fake.calls) == 1


def test_answer_runs_tool_then_replies(make_fake, context, screens, institutions):
    fake = make_fake(
        [
            tool_call(
                "kibana_sorgula",
                screen_code="ODMTTLMT",
                start_time="2026-10-17T08:45",
                end_time="2026-10-17T09:15",
                only_mine=True,
            ),
            LLMReply(content="Son 30 dakikada 7 kez Başkentgaz zaman aşımı hatası aldınız."),
        ]
    )
    reply = answer("ODMTTLMT ekranında hata alıyorum", fake, context, screens, institutions)

    assert reply.startswith("Son 30 dakikada 7 kez")
    second_call = fake.calls[1]
    assert second_call[-2]["role"] == "assistant"
    assert second_call[-2]["tool_calls"][0]["function"]["name"] == "kibana_sorgula"
    tool_message = second_call[-1]
    assert tool_message["role"] == "tool"
    assert tool_message["tool_call_id"] == "call_1"
    assert json.loads(tool_message["content"])["total"] == 7


def test_tool_error_is_sent_back_to_model(make_fake, context, screens, institutions):
    fake = make_fake(
        [tool_call("bilinmeyen_arac"), LLMReply(content="Loglara şu an erişemiyorum.")]
    )
    assert answer("x", fake, context, screens, institutions) == "Loglara şu an erişemiyorum."
    assert json.loads(fake.calls[1][-1]["content"]) == {"error": "Bilinmeyen araç: bilinmeyen_arac"}


def test_too_many_tool_turns_raises(make_fake, context, screens, institutions):
    fake = make_fake([tool_call("kibana_sorgula", start_time="x", end_time="y", only_mine=True)])
    with pytest.raises(LLMError, match="turda"):
        answer("x", fake, context, screens, institutions)
    assert len(fake.calls) == MAX_TURNS


def test_empty_final_reply_raises(make_fake, context, screens, institutions):
    with pytest.raises(LLMError, match="boş"):
        answer("x", make_fake([LLMReply(content=None)]), context, screens, institutions)
