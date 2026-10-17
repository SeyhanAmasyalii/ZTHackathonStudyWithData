"""Uygulama ayarları. Değerler ortam değişkeninden ya da backend/.env dosyasından okunur."""

import json
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Türkiye 2016'dan beri sabit UTC+3 (yaz saati yok).
TURKEY_TZ = timezone(timedelta(hours=3))

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent


def _bundled_or_repo(bundled: str, in_repo: str) -> Path:
    """Azure paketinde backend/<bundled> (scripts/package_azure.py kopyalar), yerelde repo kökü."""
    path = BACKEND_ROOT / bundled
    return path if path.is_dir() else REPO_ROOT / in_repo


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_ROOT / ".env", extra="ignore")

    app_name: str = "Mercek API"
    # JSON listesi ya da virgülle ayrılmış adresler: https://a.azurewebsites.net,http://localhost:3000
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    chat_deployment: str = "gpt-5.5"
    llm_timeout_seconds: float = 60.0
    # true: modele giden ve dönen içeriğin tamamı (kullanıcı mesajları dahil) loglanır.
    # Yalnızca yerelde hata ayıklama için; Azure'da kapalı kalmalı.
    llm_debug: bool = False
    # chat: model doğrudan çağrılır (geçmiş her turda gönderilir).
    # agent: Foundry Agent Service'teki agent çağrılır (scripts/setup_agent.py ile kurulur);
    # araçlar yine backend'de çalışır, modelin hafızası Foundry'de (previous_response_id).
    llm_mode: Literal["chat", "agent"] = "chat"
    # Foundry proje uç noktası: https://<kaynak>.services.ai.azure.com/api/projects/<proje>
    # Yalnızca Microsoft Entra ile (yerelde az login, Azure'da Managed Identity).
    foundry_project_endpoint: str = ""
    foundry_agent_name: str = "mercek"

    data_dir: Path = _bundled_or_repo("data", "datav2")
    # Azure SQL. SQL_SERVER boşsa veri data_dir'deki JSON'lardan okunur.
    # SQL_USER boşsa Microsoft Entra ile bağlanılır (yerelde az login, Azure'da Managed Identity).
    sql_server: str = ""
    sql_database: str = "mercekdb"
    sql_user: str = ""
    sql_password: str = ""
    # Azure AI Search. SEARCH_ENDPOINT boşsa hata_ara aracı sunulmaz.
    # SEARCH_API_KEY boşsa Microsoft Entra ile bağlanılır (Azure'da Managed Identity).
    search_endpoint: str = ""
    search_api_key: str = ""
    search_log_index: str = "mercek-loglar"
    # Hazır çözüm indeksi (ör. mercek-cozumler); boşsa benzer_cozum_ara aracı sunulmaz.
    search_solution_index: str = ""
    # Foundry'deki embedding deploy'u; AI Search indexer'ı ve vektörleştiricisi kullanır
    # (kurulum: scripts/build_search_index.py). Backend kendisi çağırmaz.
    embedding_deployment: str = "text-embedding-3-small"
    prompts_dir: Path = _bundled_or_repo("prompts", "prompts")
    # Veri 2026-10-17 09:00'da bitiyor; demoda "şu an" 09:15'e sabitlenir.
    # Gerçek saat için ortamda DEMO_NOW boş bırakılır (DEMO_NOW=).
    demo_now: datetime | None = datetime(2026, 10, 17, 9, 15, tzinfo=TURKEY_TZ)
    # Oturum token'larını imzalayan anahtar. Boşsa açılışta geçici bir anahtar üretilir
    # (yeniden başlatmada oturumlar düşer). Azure'da App Settings'te tanımlanır.
    session_secret: str = ""
    session_ttl_hours: int = 12

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            text = value.strip()
            if text.startswith("["):
                return json.loads(text)
            return [item.strip() for item in text.split(",") if item.strip()]
        return value

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
