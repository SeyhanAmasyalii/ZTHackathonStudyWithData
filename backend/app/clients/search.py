"""Azure AI Search REST istemcisi (indeks/indexer kurulumu, hibrit arama).

Kimlik: SEARCH_API_KEY verilirse `api-key` başlığı, verilmezse Microsoft Entra token'ı
(yerelde `az login`, App Service'te Managed Identity). Anahtar loglanmaz.
"""

import logging
from typing import Any

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)

API_VERSION = "2024-07-01"
TOKEN_SCOPE = "https://search.azure.com/.default"


class SearchError(Exception):
    """Arama servisi çağrısı başarısız oldu ya da yapılandırma eksik."""


class AzureSearchClient:
    def __init__(self, settings: Settings, http: httpx.Client | None = None) -> None:
        if not settings.search_endpoint.strip():
            raise SearchError("Eksik ortam değişkeni: SEARCH_ENDPOINT")
        self._endpoint = settings.search_endpoint.strip().rstrip("/")
        self._api_key = settings.search_api_key.strip()
        self._credential: Any = None
        self._http = http or httpx.Client(timeout=30)

    def _headers(self) -> dict[str, str]:
        if self._api_key:
            return {"api-key": self._api_key}
        if self._credential is None:
            from azure.identity import DefaultAzureCredential

            self._credential = DefaultAzureCredential()
        token = self._credential.get_token(TOKEN_SCOPE).token
        return {"Authorization": f"Bearer {token}"}

    def _request(self, method: str, path: str, body: Any = None) -> httpx.Response:
        try:
            response = self._http.request(
                method,
                f"{self._endpoint}{path}",
                params={"api-version": API_VERSION},
                json=body,
                headers=self._headers(),
            )
        except httpx.HTTPError as exc:
            raise SearchError(f"Arama servisine ulaşılamadı: {type(exc).__name__}") from exc
        if response.status_code >= 400:
            raise SearchError(f"Arama servisi {response.status_code}: {response.text[:300]}")
        return response

    def put(self, kind: str, definition: dict[str, Any]) -> None:
        """Veri kaynağı, beceri kümesi ya da indexer oluşturur/günceller (kind: datasources...)."""
        self._request("PUT", f"/{kind}/{definition['name']}", definition)

    def delete(self, kind: str, name: str) -> None:
        try:
            self._request("DELETE", f"/{kind}/{name}")
        except SearchError as exc:
            if " 404:" not in str(exc):
                raise

    def post(self, path: str) -> None:
        self._request("POST", path)

    def get(self, path: str) -> dict[str, Any]:
        return self._request("GET", path).json()

    def count(self, index: str) -> int:
        return int(self._request("GET", f"/indexes/{index}/docs/$count").text.strip("﻿ "))

    def search(self, index: str, body: dict[str, Any]) -> list[dict[str, Any]]:
        return self._request("POST", f"/indexes/{index}/docs/search", body).json().get("value", [])
