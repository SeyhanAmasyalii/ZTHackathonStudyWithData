import json
import sys

from fastapi.testclient import TestClient

from app.api.chat import get_llm
from app.config import REPO_ROOT, Settings
from app.main import app
from app.repositories import app_store
from app.repositories.app_store import MemoryAppStore, SqlAppStore, StoredMessage
from app.repositories.users import DEMO_USERS
from tests.conftest import FakeLLMClient

sys.path.insert(0, str(REPO_ROOT / "scripts"))
import setup_app_tables  # noqa: E402

client = TestClient(app)


def login(user_name: str) -> dict[str, str]:
    token = client.post("/api/login", json={"user_name": user_name}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_memory_store_conversation_is_owned_by_user():
    store = MemoryAppStore()
    conversation_id = store.create_conversation("elif")
    assert len(conversation_id) == 32
    store.append_messages(conversation_id, [StoredMessage("user", "merhaba")])
    assert store.get_conversation(conversation_id, "elif") == [StoredMessage("user", "merhaba")]
    assert store.get_conversation(conversation_id, "kerem") is None
    assert store.get_conversation("0" * 32, "elif") is None


def test_chat_keeps_history_on_server():
    fake = FakeLLMClient([])
    fake.replies = [FakeLLMClient().replies[0]]
    app.dependency_overrides[get_llm] = lambda: fake
    try:
        headers = login("elif")
        first = client.post("/api/chat", json={"message": "ilk soru"}, headers=headers).json()
        conversation_id = first["conversation_id"]
        client.post(
            "/api/chat",
            json={"message": "ikinci soru", "conversation_id": conversation_id},
            headers=headers,
        )
        # İkinci istekte frontend geçmiş göndermedi; model yine ilk soruyu ve cevabı gördü.
        roles = [(m["role"], m["content"]) for m in fake.calls[-1][1:]]
        assert roles == [
            ("user", "ilk soru"),
            ("assistant", "Merhaba, ben Mercek."),
            ("user", "ikinci soru"),
        ]
        restored = client.get(f"/api/conversations/{conversation_id}", headers=headers).json()
        assert [m["content"] for m in restored["messages"]] == [
            "ilk soru",
            "Merhaba, ben Mercek.",
            "ikinci soru",
            "Merhaba, ben Mercek.",
        ]
        # Başkasının konuşması: 404; bilinmeyen konuşma kimliğiyle sohbet yeni konuşma açar.
        other = client.get(f"/api/conversations/{conversation_id}", headers=login("kerem"))
        assert other.status_code == 404
        unknown = client.post(
            "/api/chat", json={"message": "x", "conversation_id": "f" * 32}, headers=headers
        ).json()
        assert unknown["conversation_id"] != "f" * 32
    finally:
        app.dependency_overrides.clear()


def test_conversation_id_is_validated():
    headers = login("elif")
    assert client.get("/api/conversations/../x", headers=headers).status_code == 404
    assert client.get("/api/conversations/" + "Z" * 32, headers=headers).status_code == 422
    app.dependency_overrides[get_llm] = lambda: FakeLLMClient()
    try:
        bad = client.post(
            "/api/chat", json={"message": "x", "conversation_id": "abc"}, headers=headers
        )
    finally:
        app.dependency_overrides.clear()
    assert bad.status_code == 422


def test_affected_customers_view_is_audited():
    store = app_store.get_app_store()
    before = len(store.audit)
    query = {
        "start_time": "2026-10-10T09:15",
        "end_time": "2026-10-17T09:15",
        "only_mine": False,
        "screen_code": "ODMTTLMT",
        "error_number": 110610,
    }
    client.post("/api/affected-customers", json=query, headers=login("kerem"))
    client.post("/api/affected-customers", json=query, headers=login("elif"))
    actions = [(row["user_name"], row["action"], row["row_count"]) for row in store.audit[before:]]
    assert actions == [
        ("kerem", "affected_customers_view", 31),
        ("elif", "affected_customers_denied", None),
    ]
    assert "+90" not in json.dumps(store.audit)


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.executed = []

    def execute(self, statement, params=()):
        self.executed.append((statement, params))

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, rows=()):
        self.cursor_ = FakeCursor(list(rows))

    def cursor(self):
        return self.cursor_

    def commit(self):
        pass


def fake_connect(connection):
    class Context:
        def __enter__(self):
            return connection

        def __exit__(self, *exc):
            return False

    return lambda _settings: Context()


def test_sql_store_inserts_messages_as_ascii_json(monkeypatch):
    connection = FakeConnection()
    monkeypatch.setattr(app_store.sql, "connect", fake_connect(connection))
    store = SqlAppStore(Settings(sql_server="x"))
    store.append_messages("a" * 32, [StoredMessage("user", "Doğalgaz", {"screen_code": "X"})])
    statement, params = connection.cursor_.executed[0]
    assert "OPENJSON(?)" in statement
    assert params[0].isascii()
    row = json.loads(params[0])[0]
    assert row["content"] == "Doğalgaz" and json.loads(row["affected_json"]) == {"screen_code": "X"}


def test_sql_store_users_fall_back_to_demo_users_on_error(monkeypatch):
    def broken(_settings):
        raise RuntimeError("bağlantı yok")

    monkeypatch.setattr(app_store.sql, "connect", broken)
    store = SqlAppStore(Settings(sql_server="x"))
    assert store.list_users() == DEMO_USERS
    # Yazma hataları sohbeti durdurmaz
    store.write_audit("kerem", "x", {}, 1)
    store.append_messages("a" * 32, [StoredMessage("user", "x")])
    assert len(store.create_conversation("kerem")) == 32
    assert store.get_conversation("a" * 32, "kerem") is None


def test_sql_store_reads_users_from_table(monkeypatch):
    rows = [("kerem", "Kerem Aydın", "L2 Destek", "9010", True)]
    monkeypatch.setattr(app_store.sql, "connect", fake_connect(FakeConnection(rows)))
    users = SqlAppStore(Settings(sql_server="x")).list_users()
    assert users[0].user_name == "kerem" and users[0].can_view_customers is True


def test_setup_seed_rows_match_demo_users():
    rows = setup_app_tables.user_rows()
    assert [row["user_name"] for row in rows] == [u.user_name for u in DEMO_USERS]
    assert {row["user_name"]: row["role"] for row in rows} == {
        "elif": "sube",
        "zeynep": "cagri_merkezi",
        "kerem": "l2",
    }
    assert [row["can_view_customers"] for row in rows] == [False, False, True]
