import logging
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import get_current_user
from app.clients.llm import AzureLLMClient, LLMClient, LLMError
from app.clients.search import AzureSearchClient, SearchError
from app.config import Settings, get_settings
from app.models.chat import ChatRequest, ChatResponse
from app.repositories.catalog import get_catalog
from app.repositories.datav2 import Catalog
from app.repositories.users import DemoUser
from app.services.chat import answer
from app.services.log_index import LogSearch
from app.services.tools import LogSearchFn, ToolContext

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


def get_llm() -> LLMClient:
    try:
        return AzureLLMClient(get_settings())
    except LLMError as exc:
        logger.error("LLM yapılandırması eksik: %s", exc)
        raise HTTPException(status_code=503, detail="Model bağlantısı yapılandırılmamış.") from exc


@lru_cache
def get_log_search() -> LogSearchFn | None:
    """AI Search yapılandırılmışsa hata_ara aracının arama fonksiyonu, değilse None."""
    settings = get_settings()
    if not settings.search_endpoint:
        return None
    try:
        return LogSearch(AzureSearchClient(settings), settings.search_log_index)
    except SearchError as exc:
        logger.error("AI Search yapılandırılamadı: %s", exc)
        return None


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    # Sıra önemli: önce oturum kontrolü (401), sonra model bağlantısı (503).
    user: Annotated[DemoUser, Depends(get_current_user)],
    llm: Annotated[LLMClient, Depends(get_llm)],
    settings: Annotated[Settings, Depends(get_settings)],
    catalog: Annotated[Catalog, Depends(get_catalog)],
    search_logs: Annotated[LogSearchFn | None, Depends(get_log_search)],
) -> ChatResponse:
    context = ToolContext(
        user_name=user.user_name,
        user_role=f"{user.title} · {user.unit}",
        now=settings.now(),
        logs=catalog.logs,
        incidents=catalog.incidents,
        search_logs=search_logs,
    )
    try:
        reply = answer(
            request.message,
            llm,
            context,
            catalog.screens,
            catalog.institutions,
            request.history,
        )
    except LLMError as exc:
        logger.error("Sohbet yanıtı üretilemedi: %s", exc)
        raise HTTPException(status_code=502, detail="Şu an yanıt üretilemiyor.") from exc
    return ChatResponse(reply=reply)
