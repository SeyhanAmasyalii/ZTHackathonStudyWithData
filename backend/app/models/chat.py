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


class ChatResponse(BaseModel):
    reply: str
