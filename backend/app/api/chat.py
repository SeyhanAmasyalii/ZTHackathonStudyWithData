import logging
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from app.api.auth import get_current_user
from app.clients.llm import AzureLLMClient, LLMClient, LLMError
from app.clients.search import AzureSearchClient, SearchError
from app.config import Settings, get_settings
from app.models.chat import (
    MAX_HISTORY,
    AffectedSummary,
    ChatRequest,
    ChatResponse,
    ConversationMessage,
    ConversationOut,
    HistoryMessage,
)
from app.repositories.app_store import AppStore, StoredMessage, get_app_store
from app.repositories.catalog import get_catalog
from app.repositories.datav2 import Catalog
from app.repositories.users import DemoUser
from app.services.chat import answer
from app.services.log_index import LogSearch
from app.services.tools import LogSearchFn, ToolContext

logger = logging.getLogger(__name__)

MAX_HISTORY_CONTENT = 8000

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


@router.post("/chat", response_model=ChatResponse, response_model_exclude_none=True)
def chat(
    request: ChatRequest,
    # Sıra önemli: önce oturum kontrolü (401), sonra model bağlantısı (503).
    user: Annotated[DemoUser, Depends(get_current_user)],
    llm: Annotated[LLMClient, Depends(get_llm)],
    settings: Annotated[Settings, Depends(get_settings)],
    catalog: Annotated[Catalog, Depends(get_catalog)],
    search_logs: Annotated[LogSearchFn | None, Depends(get_log_search)],
    store: Annotated[AppStore, Depends(get_app_store)],
) -> ChatResponse:
    context = ToolContext(
        user_name=user.user_name,
        user_role=f"{user.title} · {user.unit}",
        now=settings.now(),
        logs=catalog.logs,
        incidents=catalog.incidents,
        search_logs=search_logs,
    )
    # Konuşma hafızası sunucuda (SQL): kayıt varsa geçmiş oradan okunur. Kayıt yoksa (yeni sohbet
    # ya da sunucu belleği sıfırlandıysa) yeni konuşma açılır, frontend'in geçmişi kullanılır.
    history = list(request.history)
    conversation_id = request.conversation_id
    stored = store.get_conversation(conversation_id, user.user_name) if conversation_id else None
    if stored is None:
        conversation_id = store.create_conversation(user.user_name)
    else:
        history = [
            HistoryMessage(role=item.role, content=item.content[:MAX_HISTORY_CONTENT])
            for item in stored[-MAX_HISTORY:]
        ]

    trace: list[tuple[str, dict]] = []
    try:
        reply = answer(
            request.message,
            llm,
            context,
            catalog.screens,
            catalog.institutions,
            history,
            trace,
        )
    except LLMError as exc:
        logger.error("Sohbet yanıtı üretilemedi: %s", exc)
        raise HTTPException(status_code=502, detail="Şu an yanıt üretilemiyor.") from exc
    affected = _affected_summary(user, trace)
    store.append_messages(
        conversation_id,
        [
            StoredMessage("user", request.message.strip()),
            StoredMessage("assistant", reply, affected.model_dump() if affected else None),
        ],
    )
    return ChatResponse(reply=reply, affected_customers=affected, conversation_id=conversation_id)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationOut,
    response_model_exclude_none=True,
)
def get_conversation(
    conversation_id: Annotated[str, Path(pattern=r"^[0-9a-f]{32}$")],
    user: Annotated[DemoUser, Depends(get_current_user)],
    store: Annotated[AppStore, Depends(get_app_store)],
) -> ConversationOut:
    """Sayfa yenilenince sohbeti geri yüklemek için; yalnızca konuşmanın sahibi görür."""
    stored = store.get_conversation(conversation_id, user.user_name)
    if stored is None:
        raise HTTPException(status_code=404, detail="Konuşma bulunamadı.")
    return ConversationOut(
        conversation_id=conversation_id,
        messages=[
            ConversationMessage(
                role=item.role,
                content=item.content,
                affected_customers=(
                    AffectedSummary(**item.affected)
                    if item.affected and user.can_view_customers
                    else None
                ),
            )
            for item in stored
        ],
    )


def _affected_summary(user: DemoUser, trace: list[tuple[str, dict]]) -> AffectedSummary | None:
    """Yetkili kullanıcıya, modelin son kibana_sorgula sorgusundan müşteri listesi düğmesi.

    Sorguyu model seçer ama düğmeyi ve listeyi kod üretir; liste modele gönderilmez.
    """
    if not user.can_view_customers:
        return None
    # Model aynı turda birden fazla sorgu yapabilir (ör. önce 30 dk, sonra 7 gün; ya da tersi).
    # Müşteri bulunan en son sorgu esas alınır; boş sorgu düğmeyi gizlemez.
    for name, result in reversed(trace):
        if name != "kibana_sorgula" or "query" not in result or "error" in result:
            continue
        count = result.get("distinct_customers", 0)
        if count:
            return AffectedSummary(**result["query"], customer_count=count)
    return None
