"""Etkilenen müşteri listesi: yalnızca yetkili kullanıcı (L2), liste modele gitmez."""

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import get_current_user
from app.config import Settings, get_settings
from app.models.chat import AffectedCustomersResponse, AffectedQuery
from app.repositories.catalog import get_catalog
from app.repositories.datav2 import Catalog
from app.repositories.users import DemoUser
from app.services.affected import affected_customers
from app.services.tools import ToolContext, ToolInputError

# Erişim kaydı (KVKK): kim, ne zaman, hangi sorgu, kaç müşteri. Müşteri bilgisi yazılmaz.
audit = logging.getLogger("mercek.audit")

router = APIRouter(tags=["customers"])


@router.post("/affected-customers", response_model=AffectedCustomersResponse)
def list_affected_customers(
    query: AffectedQuery,
    user: Annotated[DemoUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    catalog: Annotated[Catalog, Depends(get_catalog)],
) -> AffectedCustomersResponse:
    if not user.can_view_customers:
        audit.warning("Müşteri listesi reddedildi: kullanıcı=%s", user.user_name)
        raise HTTPException(status_code=403, detail="Bu listeyi görme yetkiniz yok.")
    context = ToolContext(user_name=user.user_name, now=settings.now(), logs=catalog.logs)
    try:
        result = affected_customers(query.model_dump(), context, catalog.customers)
    except ToolInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    audit.info(
        "Müşteri listesi görüntülendi: kullanıcı=%s sorgu=%s müşteri=%d",
        user.user_name,
        json.dumps(result["query"], ensure_ascii=False),
        result["total_customers"],
    )
    return AffectedCustomersResponse(**result)
