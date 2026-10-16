import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import get_current_user
from app.clients.llm import AzureLLMClient, LLMClient, LLMError
from app.config import Settings, get_settings
from app.models.chat import ChatRequest, ChatResponse
from app.repositories.datav2 import (
    load_error_logs,
    load_incidents,
    load_institutions,
    load_screens,
)
from app.repositories.users import DemoUser
from app.services.chat import answer
from app.services.tools import ToolContext

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


def get_llm() -> LLMClient:
    try:
        return AzureLLMClient(get_settings())
    except LLMError as exc:
        logger.error("LLM yapılandırması eksik: %s", exc)
        raise HTTPException(status_code=503, detail="Model bağlantısı yapılandırılmamış.") from exc


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    # Sıra önemli: önce oturum kontrolü (401), sonra model bağlantısı (503).
    user: Annotated[DemoUser, Depends(get_current_user)],
    llm: Annotated[LLMClient, Depends(get_llm)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChatResponse:
    context = ToolContext(
        user_name=user.user_name,
        user_role=f"{user.title} · {user.unit}",
        now=settings.now(),
        logs=load_error_logs(settings.data_dir),
        incidents=load_incidents(settings.data_dir),
    )
    try:
        reply = answer(
            request.message,
            llm,
            context,
            load_screens(settings.data_dir),
            load_institutions(settings.data_dir),
            request.history,
        )
    except LLMError as exc:
        logger.error("Sohbet yanıtı üretilemedi: %s", exc)
        raise HTTPException(status_code=502, detail="Şu an yanıt üretilemiyor.") from exc
    return ChatResponse(reply=reply)
