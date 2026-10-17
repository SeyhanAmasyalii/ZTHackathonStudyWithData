import logging
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException

from app.config import Settings, get_settings
from app.models.auth import LoginRequest, LoginResponse, UserOut
from app.repositories.app_store import get_app_store
from app.repositories.users import DemoUser
from app.services.auth import AuthError, create_token, new_secret, verify_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


@lru_cache
def _session_secret(configured: str) -> str:
    if configured.strip():
        return configured
    logger.warning(
        "SESSION_SECRET tanımlı değil; geçici anahtar üretildi "
        "(yeniden başlatmada oturumlar düşer)."
    )
    return new_secret()


def find_user(user_name: str) -> DemoUser | None:
    """Kullanıcılar SQL'deki app_users tablosundan (yoksa koddaki demo listesi)."""
    return next((u for u in get_app_store().list_users() if u.user_name == user_name), None)


def _to_out(user: DemoUser) -> UserOut:
    return UserOut(user_name=user.user_name, name=user.name, title=user.title, unit=user.unit)


def get_current_user(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> DemoUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Giriş yapmanız gerekiyor.")
    try:
        user_name = verify_token(
            authorization.removeprefix("Bearer ").strip(),
            _session_secret(settings.session_secret),
            datetime.now(UTC),
        )
    except AuthError as exc:
        raise HTTPException(status_code=401, detail="Oturum geçersiz, tekrar giriş yapın.") from exc
    user = find_user(user_name)
    if user is None:
        raise HTTPException(status_code=401, detail="Oturum geçersiz, tekrar giriş yapın.")
    return user


@router.get("/users", response_model=list[UserOut])
def list_users() -> list[UserOut]:
    """Giriş ekranındaki demo kullanıcı listesi."""
    return [_to_out(user) for user in get_app_store().list_users()]


@router.post("/login", response_model=LoginResponse)
def login(
    request: LoginRequest, settings: Annotated[Settings, Depends(get_settings)]
) -> LoginResponse:
    user = find_user(request.user_name)
    if user is None:
        raise HTTPException(status_code=401, detail="Kullanıcı bulunamadı.")
    token = create_token(
        user.user_name,
        _session_secret(settings.session_secret),
        datetime.now(UTC),
        timedelta(hours=settings.session_ttl_hours),
    )
    return LoginResponse(token=token, user=_to_out(user))
