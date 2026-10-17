import logging
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, chat, health
from app.config import get_settings
from app.repositories.catalog import get_catalog

settings = get_settings()

# Uygulama logları (ör. araç çağrıları) uvicorn terminalinde görünsün.
logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Veri (SQL uykudaysa uyanması dahil) ilk sohbeti beklemeden arka planda yüklenir.
    threading.Thread(target=get_catalog, name="catalog-warmup", daemon=True).start()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
