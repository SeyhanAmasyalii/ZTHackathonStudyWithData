import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, health
from app.config import get_settings

settings = get_settings()

# Uygulama logları (ör. araç çağrıları) uvicorn terminalinde görünsün.
logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s: %(message)s")

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(health.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
