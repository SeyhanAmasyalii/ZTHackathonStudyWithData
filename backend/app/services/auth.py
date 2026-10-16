"""Demo oturumu: imzalı, süreli token (HMAC-SHA256). Şifre yok; kullanıcı listeden seçilir."""

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta


class AuthError(Exception):
    """Token yok, bozuk, imzası geçersiz ya da süresi dolmuş."""


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(payload: str, secret: str) -> str:
    return _b64encode(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest())


def create_token(user_name: str, secret: str, now: datetime, ttl: timedelta) -> str:
    body = {"u": user_name, "exp": int((now + ttl).timestamp())}
    payload = _b64encode(json.dumps(body, separators=(",", ":")).encode())
    return f"{payload}.{_sign(payload, secret)}"


def verify_token(token: str, secret: str, now: datetime) -> str:
    """Geçerliyse kullanıcı adını döner, değilse AuthError."""
    try:
        payload, signature = token.split(".")
    except ValueError as exc:
        raise AuthError("Token biçimi geçersiz") from exc
    if not hmac.compare_digest(signature, _sign(payload, secret)):
        raise AuthError("Token imzası geçersiz")
    try:
        body = json.loads(_b64decode(payload))
        user_name, expires = body["u"], body["exp"]
    except (ValueError, KeyError, TypeError) as exc:
        raise AuthError("Token içeriği geçersiz") from exc
    if not isinstance(user_name, str) or not isinstance(expires, int):
        raise AuthError("Token içeriği geçersiz")
    if now.timestamp() >= expires:
        raise AuthError("Oturumun süresi doldu")
    return user_name


def new_secret() -> str:
    return secrets.token_urlsafe(32)
