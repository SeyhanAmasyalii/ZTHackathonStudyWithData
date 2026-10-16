import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.clients.llm import AzureLLMClient, LLMClient, LLMError
from app.config import Settings, get_settings
from app.models.chat import ChatRequest, ChatResponse
from app.repositories.datav2 import load_error_logs, load_screens
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
    llm: Annotated[LLMClient, Depends(get_llm)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChatResponse:
    context = ToolContext(
        user_name=settings.demo_user,
        now=settings.now(),
        logs=load_error_logs(settings.data_dir),
    )
    try:
        reply = answer(request.message, llm, context, load_screens(settings.data_dir))
    except LLMError as exc:
        logger.error("Sohbet yanıtı üretilemedi: %s", exc)
        raise HTTPException(status_code=502, detail="Şu an yanıt üretilemiyor.") from exc
    return ChatResponse(reply=reply)
