import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.api.chat import get_llm
from app.clients.llm import LLMReply
from app.main import app
from app.services.auth import AuthError, create_token, verify_token
from tests.conftest import FakeLLMClient, tool_call

client = TestClient(app)
NOW = datetime(2026, 10, 17, 6, 15, tzinfo=UTC)


def _returning(fake):
    def dependency():
        return fake

    return dependency


def login(user_name: str):
    return client.post("/api/login", json={"user_name": user_name})


def test_users_list_has_demo_users():
    users = client.get("/api/users").json()
    assert [u["user_name"] for u in users] == ["elif", "zeynep", "kerem"]
    assert users[0] == {
        "user_name": "elif",
        "name": "Elif Demir",
        "title": "Şube Müşteri Temsilcisi",
        "unit": "601 Kızılay Şubesi",
    }


def test_login_returns_token_and_user():
    response = login("elif")
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["name"] == "Elif Demir"
    assert body["token"].count(".") == 1


@pytest.mark.parametrize(("user_name", "status"), [("yok", 401), ("Elif", 422), ("", 422)])
def test_login_rejects_unknown_or_invalid(user_name, status):
    assert login(user_name).status_code == status


@pytest.mark.parametrize(
    "header",
    [None, "elif", "Bearer ", "Bearer bozuk", "Bearer a.b", "Basic abc"],
)
def test_chat_requires_valid_token(header):
    headers = {"Authorization": header} if header is not None else {}
    response = client.post("/api/chat", json={"message": "merhaba"}, headers=headers)
    assert response.status_code == 401


def test_chat_uses_user_from_token():
    """Model only_mine=true der; filtre token'daki kullanıcıyla uygulanır."""
    seen = {}
    for user_name in ("elif", "zeynep"):
        fake = FakeLLMClient(
            [
                tool_call(
                    "kibana_sorgula",
                    start_time="2026-10-17T08:00",
                    end_time="2026-10-17T09:15",
                    only_mine=True,
                ),
                LLMReply(content="tamam"),
            ]
        )
        app.dependency_overrides[get_llm] = _returning(fake)
        token = login(user_name).json()["token"]
        response = client.post(
            "/api/chat", json={"message": "x"}, headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        seen[user_name] = json.loads(fake.calls[1][-1]["content"])["total"]
    app.dependency_overrides.clear()
    assert seen == {"elif": 8, "zeynep": 3}


def test_token_roundtrip_and_tampering():
    token = create_token("elif", "s1", NOW, timedelta(hours=1))
    assert verify_token(token, "s1", NOW) == "elif"
    with pytest.raises(AuthError, match="imza"):
        verify_token(token, "baska-anahtar", NOW)
    payload, signature = token.split(".")
    forged = create_token("kerem", "s1", NOW, timedelta(hours=1)).split(".")[0]
    with pytest.raises(AuthError, match="imza"):
        verify_token(f"{forged}.{signature}", "s1", NOW)


def test_token_expires():
    token = create_token("elif", "s1", NOW, timedelta(hours=1))
    with pytest.raises(AuthError, match="süresi"):
        verify_token(token, "s1", NOW + timedelta(hours=1))


def test_chat_sends_user_role_to_model():
    fake = FakeLLMClient([LLMReply(content="tamam")])
    app.dependency_overrides[get_llm] = _returning(fake)
    token = login("kerem").json()["token"]
    client.post("/api/chat", json={"message": "x"}, headers={"Authorization": f"Bearer {token}"})
    app.dependency_overrides.clear()
    system = fake.calls[0][0]["content"]
    assert "Kullanıcının görevi: L2 Destek · 9010 BT Destek (L2)." in system
    assert "kerem" not in system


def test_zeynep_has_three_call_center_logs_this_morning(data_dir):
    from app.repositories.datav2 import load_error_logs

    zeynep = [e for e in load_error_logs(data_dir) if e.user_name == "zeynep"]
    assert [e.log_time.strftime("%H:%M") for e in zeynep] == ["08:33", "08:43", "08:54"]
    assert {(e.screen_code, e.error_number, e.institution_code) for e in zeynep} == {
        ("ODMTTLMT", 110731, "GAZ02")
    }
