"""Uygulama verisi: kullanıcılar, erişim kaydı (audit), konuşma geçmişi.

SQL_SERVER tanımlıysa Azure SQL (db/app_tables.sql), değilse bellek (yerel geliştirme, testler).
SQL hatası sohbeti durdurmaz: kullanıcılar koddaki listeye düşer, geçmiş/kayıt yazılamazsa loglanır.
Metinler SQL'e ASCII kaçışlı tek JSON parametresiyle (OPENJSON) gider: Türkçe karakter bozulmaz.
"""

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Protocol

from app.config import Settings, get_settings
from app.repositories import sql
from app.repositories.users import DEMO_USERS, DemoUser

logger = logging.getLogger(__name__)

USERS_TTL_SECONDS = 60


@dataclass(frozen=True)
class StoredMessage:
    role: str  # user / assistant
    content: str
    affected: dict[str, Any] | None = None


class AppStore(Protocol):
    def list_users(self) -> tuple[DemoUser, ...]: ...

    def write_audit(
        self, user_name: str, action: str, detail: dict[str, Any], row_count: int | None
    ) -> None: ...

    def create_conversation(self, user_name: str) -> str: ...

    def get_conversation(self, conversation_id: str, user_name: str) -> list[StoredMessage] | None:
        """Mesajlar (eskiden yeniye); konuşma yoksa ya da başkasınınsa None."""
        ...

    def append_messages(self, conversation_id: str, messages: list[StoredMessage]) -> None: ...

    def get_agent_response_id(self, conversation_id: str) -> str | None:
        """Foundry agent'ının bu konuşmadaki son cevap kimliği (LLM_MODE=agent)."""
        ...

    def set_agent_response_id(self, conversation_id: str, response_id: str) -> None: ...


def new_conversation_id() -> str:
    return uuid.uuid4().hex


class MemoryAppStore:
    """SQL yokken: süreç yeniden başlayınca geçmiş ve kayıtlar silinir."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._owners: dict[str, str] = {}
        self._messages: dict[str, list[StoredMessage]] = {}
        self._agent_responses: dict[str, str] = {}
        self.audit: list[dict[str, Any]] = []

    def list_users(self) -> tuple[DemoUser, ...]:
        return DEMO_USERS

    def write_audit(
        self, user_name: str, action: str, detail: dict[str, Any], row_count: int | None
    ) -> None:
        with self._lock:
            self.audit.append(
                {"user_name": user_name, "action": action, "detail": detail, "row_count": row_count}
            )

    def create_conversation(self, user_name: str) -> str:
        conversation_id = new_conversation_id()
        with self._lock:
            self._owners[conversation_id] = user_name
            self._messages[conversation_id] = []
        return conversation_id

    def get_conversation(self, conversation_id: str, user_name: str) -> list[StoredMessage] | None:
        with self._lock:
            if self._owners.get(conversation_id) != user_name:
                return None
            return list(self._messages[conversation_id])

    def append_messages(self, conversation_id: str, messages: list[StoredMessage]) -> None:
        with self._lock:
            self._messages.setdefault(conversation_id, []).extend(messages)

    def get_agent_response_id(self, conversation_id: str) -> str | None:
        with self._lock:
            return self._agent_responses.get(conversation_id)

    def set_agent_response_id(self, conversation_id: str, response_id: str) -> None:
        with self._lock:
            self._agent_responses[conversation_id] = response_id


def _payload(rows: list[dict[str, Any]]) -> str:
    return json.dumps(rows)  # ensure_ascii=True (varsayılan)


INSERT_MESSAGES = (
    "INSERT INTO dbo.conversation_messages (conversation_id, role, content, affected_json) "
    "SELECT conversation_id, role, content, affected_json FROM OPENJSON(?) WITH ("
    "conversation_id CHAR(32) '$.conversation_id', role NVARCHAR(10) '$.role', "
    "content NVARCHAR(MAX) '$.content', affected_json NVARCHAR(MAX) '$.affected_json')"
)
INSERT_AUDIT = (
    "INSERT INTO dbo.audit_log (user_name, action, detail, row_count) "
    "SELECT user_name, action, detail, row_count FROM OPENJSON(?) WITH ("
    "user_name NVARCHAR(50) '$.user_name', action NVARCHAR(50) '$.action', "
    "detail NVARCHAR(MAX) '$.detail', row_count INT '$.row_count')"
)
SELECT_USERS = (
    "SELECT user_name, full_name, title, unit, can_view_customers FROM dbo.app_users "
    "WHERE is_active = 1 ORDER BY sort_order, user_name"
)
SELECT_MESSAGES = (
    "SELECT m.role, m.content, m.affected_json FROM dbo.conversation_messages AS m "
    "JOIN dbo.conversations AS c ON c.conversation_id = m.conversation_id "
    "WHERE c.conversation_id = ? AND c.user_name = ? ORDER BY m.message_id"
)


class SqlAppStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._users: tuple[DemoUser, ...] | None = None
        self._users_at = 0.0
        self._lock = threading.Lock()

    def _run(self, statement: str, params: list[Any], fetch: bool = False) -> list[tuple]:
        with sql.connect(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(statement, params)
            rows = [tuple(row) for row in cursor.fetchall()] if fetch else []
            connection.commit()
            return rows

    def list_users(self) -> tuple[DemoUser, ...]:
        with self._lock:
            if self._users is not None and time.monotonic() - self._users_at < USERS_TTL_SECONDS:
                return self._users
            try:
                rows = self._run(SELECT_USERS, [], fetch=True)
                users = tuple(
                    DemoUser(name_, full, title, unit, can_view_customers=bool(can_view))
                    for name_, full, title, unit, can_view in rows
                )
            except Exception:
                logger.exception("app_users okunamadı; koddaki demo kullanıcıları kullanılıyor")
                users = ()
            self._users = users or DEMO_USERS
            self._users_at = time.monotonic()
            return self._users

    def write_audit(
        self, user_name: str, action: str, detail: dict[str, Any], row_count: int | None
    ) -> None:
        row = {
            "user_name": user_name,
            "action": action,
            "detail": json.dumps(detail, ensure_ascii=False),
            "row_count": row_count,
        }
        try:
            self._run(INSERT_AUDIT, [_payload([row])])
        except Exception:
            logger.exception("audit_log yazılamadı (kayıt uygulama logunda)")

    def create_conversation(self, user_name: str) -> str:
        conversation_id = new_conversation_id()
        try:
            self._run(
                "INSERT INTO dbo.conversations (conversation_id, user_name) VALUES (?, ?)",
                [conversation_id, user_name],
            )
        except Exception:
            logger.exception("Konuşma kaydı açılamadı; geçmiş bu sohbette tutulmayacak")
        return conversation_id

    def get_conversation(self, conversation_id: str, user_name: str) -> list[StoredMessage] | None:
        try:
            rows = self._run(SELECT_MESSAGES, [conversation_id, user_name], fetch=True)
            if not rows:
                owner = self._run(
                    "SELECT 1 FROM dbo.conversations WHERE conversation_id = ? AND user_name = ?",
                    [conversation_id, user_name],
                    fetch=True,
                )
                return [] if owner else None
        except Exception:
            logger.exception("Konuşma geçmişi okunamadı")
            return None
        return [
            StoredMessage(role, content, json.loads(affected) if affected else None)
            for role, content, affected in rows
        ]

    def append_messages(self, conversation_id: str, messages: list[StoredMessage]) -> None:
        rows = [
            {
                "conversation_id": conversation_id,
                "role": message.role,
                "content": message.content,
                "affected_json": json.dumps(message.affected) if message.affected else None,
            }
            for message in messages
        ]
        try:
            self._run(INSERT_MESSAGES, [_payload(rows)])
            self._run(
                "UPDATE dbo.conversations SET updated_at = SYSDATETIMEOFFSET() "
                "WHERE conversation_id = ?",
                [conversation_id],
            )
        except Exception:
            logger.exception("Konuşma mesajları yazılamadı")

    def get_agent_response_id(self, conversation_id: str) -> str | None:
        try:
            rows = self._run(
                "SELECT agent_response_id FROM dbo.conversations WHERE conversation_id = ?",
                [conversation_id],
                fetch=True,
            )
        except Exception:
            logger.exception("Agent cevap kimliği okunamadı; geçmiş yeniden gönderilecek")
            return None
        return rows[0][0] if rows and rows[0][0] else None

    def set_agent_response_id(self, conversation_id: str, response_id: str) -> None:
        try:
            self._run(
                "UPDATE dbo.conversations SET agent_response_id = ? WHERE conversation_id = ?",
                [response_id, conversation_id],
            )
        except Exception:
            logger.exception("Agent cevap kimliği yazılamadı")


@lru_cache
def get_app_store() -> AppStore:
    settings = get_settings()
    return SqlAppStore(settings) if settings.sql_server else MemoryAppStore()
