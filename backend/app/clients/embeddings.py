"""Foundry'deki embedding deploy'u: metni anlam araması için vektöre çevirir."""

from typing import Protocol

from openai import OpenAI, OpenAIError

from app.clients.llm import LLMError, _base_url
from app.config import Settings


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class AzureEmbedder:
    def __init__(self, settings: Settings) -> None:
        if not settings.azure_openai_endpoint.strip() or not settings.azure_openai_api_key.strip():
            raise LLMError("Eksik ortam değişkeni: AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY")
        self._deployment = settings.embedding_deployment
        self._client = OpenAI(
            base_url=_base_url(settings.azure_openai_endpoint),
            api_key=settings.azure_openai_api_key,
            timeout=settings.llm_timeout_seconds,
            max_retries=1,
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            response = self._client.embeddings.create(model=self._deployment, input=texts)
        except OpenAIError as exc:
            raise LLMError(f"Embedding çağrısı başarısız: {type(exc).__name__}") from exc
        return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]
