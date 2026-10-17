from typing import Literal

from pydantic import BaseModel, Field

MAX_HISTORY = 20


class HistoryMessage(BaseModel):
    """Aynı sohbetteki önceki mesaj (kullanıcı ya da Mercek'in cevabı)."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    # Konuşma hafızası: frontend o sohbetteki son mesajları gönderir (eskiden yeniye).
    history: list[HistoryMessage] = Field(default_factory=list, max_length=MAX_HISTORY)
    # Sunucudaki konuşma (SQL). Verilirse geçmiş sunucudan okunur; yoksa yeni konuşma açılır.
    conversation_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{32}$")


class AffectedQuery(BaseModel):
    """Son kibana_sorgula filtresi; etkilenen müşteri listesi bununla yeniden hesaplanır."""

    start_time: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$")
    end_time: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$")
    only_mine: bool = False
    screen_code: str | None = Field(default=None, pattern=r"^[A-Za-z0-9]{2,20}$")
    institution_code: str | None = Field(default=None, pattern=r"^[A-Za-z0-9]{2,20}$")
    error_number: int | None = None
    keyword: str | None = Field(default=None, max_length=100)


class AffectedSummary(AffectedQuery):
    customer_count: int


class ChatResponse(BaseModel):
    reply: str
    # Yalnızca yetkili kullanıcıya (L2) ve son sorguda müşteri varsa: "Etkilenen müşteriler".
    affected_customers: AffectedSummary | None = None
    conversation_id: str | None = None


class AffectedCustomer(BaseModel):
    customer_number: str
    full_name: str | None
    phone: str | None
    can_call: bool
    channel: str
    last_error_time: str
    screen_code: str
    error_number: int | None
    institution_code: str | None


class AffectedCustomersResponse(BaseModel):
    total_customers: int
    callable_customers: int
    truncated: bool
    rows: list[AffectedCustomer]


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    affected_customers: AffectedSummary | None = None


class ConversationOut(BaseModel):
    conversation_id: str
    messages: list[ConversationMessage]
