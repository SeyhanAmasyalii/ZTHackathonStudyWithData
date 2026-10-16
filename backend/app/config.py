"""Uygulama ayarları. Değerler ortam değişkeninden ya da backend/.env dosyasından okunur."""

from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Türkiye 2016'dan beri sabit UTC+3 (yaz saati yok).
TURKEY_TZ = timezone(timedelta(hours=3))

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Mercek API"
    cors_origins: list[str] = ["http://localhost:3000"]

    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    chat_deployment: str = "gpt-5.5"
    llm_timeout_seconds: float = 60.0
    # true: modele giden ve dönen içeriğin tamamı (kullanıcı mesajları dahil) loglanır.
    # Yalnızca yerelde hata ayıklama için; Azure'da kapalı kalmalı.
    llm_debug: bool = False

    data_dir: Path = REPO_ROOT / "datav2"
    # Veri 2026-10-17 09:00'da bitiyor; demoda "şu an" 09:15'e sabitlenir.
    # Gerçek saat için ortamda DEMO_NOW boş bırakılır (DEMO_NOW=).
    demo_now: datetime | None = datetime(2026, 10, 17, 9, 15, tzinfo=TURKEY_TZ)
    # Giriş ekranı gelene kadar sohbeti yapan demo kullanıcısı (kibana_logs.user_name).
    demo_user: str = "elif"

    @field_validator("demo_now", mode="before")
    @classmethod
    def _empty_demo_now(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    def now(self) -> datetime:
        if self.demo_now is None:
            return datetime.now(TURKEY_TZ)
        if self.demo_now.tzinfo is None:
            return self.demo_now.replace(tzinfo=TURKEY_TZ)
        return self.demo_now


@lru_cache
def get_settings() -> Settings:
    return Settings()
