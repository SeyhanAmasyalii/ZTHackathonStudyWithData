import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.api.chat import get_llm
from app.clients.llm import LLMReply, ToolCall
from app.config import TURKEY_TZ
from app.main import app
from app.repositories.datav2 import Customer, json_catalog
from app.services.affected import affected_customers, mask_phone
from app.services.tools import ToolContext
from tests.conftest import FakeLLMClient, tool_call

NOW = datetime(2026, 10, 17, 9, 15, tzinfo=TURKEY_TZ)
QUERY = {
    "start_time": "2026-10-10T09:15",
    "end_time": "2026-10-17T09:15",
    "only_mine": False,
    "screen_code": "ODMTTLMT",
    "error_number": 110610,
}

client = TestClient(app)


def token(user_name: str) -> dict[str, str]:
    value = client.post("/api/login", json={"user_name": user_name}).json()["token"]
    return {"Authorization": f"Bearer {value}"}


@pytest.fixture
def fake_llm():
    fake = FakeLLMClient()
    app.dependency_overrides[get_llm] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


def test_mask_phone_keeps_country_operator_and_last_two():
    assert mask_phone("+90 532 000 85 64") == "+90 5•• ••• •• 64"


def test_affected_customers_matches_tool_count_and_masks_without_permission(data_dir):
    catalog = json_catalog(data_dir)
    context = ToolContext(user_name="kerem", now=NOW, logs=catalog.logs)
    result = affected_customers(QUERY, context, catalog.customers)
    assert result["total_customers"] == len(result["rows"]) == 31
    times = [row["last_error_time"] for row in result["rows"]]
    assert times == sorted(times, reverse=True)
    for row in result["rows"]:
        customer = catalog.customers[row["customer_number"]]
        assert row["can_call"] is customer.perm_phone
        if customer.perm_phone:
            assert row["phone"] == customer.phone and row["channel"] == "Telefon"
        else:
            assert "•" in row["phone"] and row["channel"] != "Telefon"
    assert result["callable_customers"] == sum(row["can_call"] for row in result["rows"])
    # veri en aza indirme: gelir, doğum tarihi, adres, e-posta yok
    assert set(result["rows"][0]) == {
        "customer_number",
        "full_name",
        "phone",
        "can_call",
        "channel",
        "last_error_time",
        "screen_code",
        "error_number",
        "institution_code",
    }


def test_channel_falls_back_to_sms_email_or_none():
    from app.services.affected import _channel

    def customer(phone, sms, email):
        return Customer("1", "Ad", "+90 532 000 00 01", phone, sms, email)

    assert _channel(customer(False, True, True)) == "SMS"
    assert _channel(customer(False, False, True)) == "E-posta"
    assert _channel(customer(False, False, False)) == "İzin yok"
    assert _channel(None) == "Kayıt yok"


def test_endpoint_only_for_l2():
    for user_name in ("elif", "zeynep"):
        response = client.post("/api/affected-customers", json=QUERY, headers=token(user_name))
        assert response.status_code == 403
    response = client.post("/api/affected-customers", json=QUERY, headers=token("kerem"))
    assert response.status_code == 200
    assert response.json()["total_customers"] == 31


def test_endpoint_requires_login_and_valid_query():
    assert client.post("/api/affected-customers", json=QUERY).status_code == 401
    bad = {**QUERY, "screen_code": "ODM'; DROP"}
    assert (
        client.post("/api/affected-customers", json=bad, headers=token("kerem")).status_code == 422
    )


def test_endpoint_writes_audit_log_without_customer_data(caplog):
    with caplog.at_level("INFO", logger="mercek.audit"):
        client.post("/api/affected-customers", json=QUERY, headers=token("kerem"))
    message = caplog.records[-1].getMessage()
    assert "kullanıcı=kerem" in message and "müşteri=31" in message
    assert "+90" not in message


def kibana_then_reply(fake):
    fake.replies = [
        tool_call("kibana_sorgula", **QUERY),
        FakeLLMClient().replies[0],
    ]


def test_chat_offers_list_only_to_l2(fake_llm):
    kibana_then_reply(fake_llm)
    body = client.post("/api/chat", json={"message": "x"}, headers=token("kerem")).json()
    summary = body["affected_customers"]
    assert summary["customer_count"] == 31
    assert summary["screen_code"] == "ODMTTLMT" and summary["error_number"] == 110610
    # model listeyi görmez: araç sonucu yalnızca sayı içerir
    tool_message = fake_llm.calls[1][-1]["content"]
    assert "+90" not in tool_message and "full_name" not in tool_message

    kibana_then_reply(fake_llm)
    body = client.post("/api/chat", json={"message": "x"}, headers=token("elif")).json()
    assert "affected_customers" not in body


def test_chat_offers_list_when_last_query_is_empty(fake_llm):
    # Model iki sorguyu aynı turda yapar: 7 gün (31 müşteri) ve son 30 dk (0 müşteri).
    empty = {**QUERY, "start_time": "2026-10-17T08:45"}
    fake_llm.replies = [
        LLMReply(
            content=None,
            tool_calls=[
                ToolCall(id="a", name="kibana_sorgula", arguments=json.dumps(QUERY)),
                ToolCall(id="b", name="kibana_sorgula", arguments=json.dumps(empty)),
            ],
        ),
        FakeLLMClient().replies[0],
    ]
    body = client.post("/api/chat", json={"message": "x"}, headers=token("kerem")).json()
    assert body["affected_customers"]["customer_count"] == 31
    assert body["affected_customers"]["start_time"] == "2026-10-10T09:15"
