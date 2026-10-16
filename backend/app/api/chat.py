import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.clients.llm import AzureLLMClient, LLMClient, LLMError
from app.config import get_settings
from app.models.chat import ChatRequest, ChatResponse
from app.services.chat import answer

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


def get_llm() -> LLMClient:
    try:
        return AzureLLMClient(get_settings())
    except LLMError as exc:
        logger.error("LLM yapılandırması eksik: %s", exc)
        raise HTTPException(status_code=503, detail="Model bağlantısı yapılandırılmamış.") from exc


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, llm: Annotated[LLMClient, Depends(get_llm)]) -> ChatResponse:
    try:
        reply = answer(request.message, llm)
    except LLMError as exc:
        logger.error("Sohbet yanıtı üretilemedi: %s", exc)
        raise HTTPException(status_code=502, detail="Şu an yanıt üretilemiyor.") from exc
    return ChatResponse(reply=reply)
