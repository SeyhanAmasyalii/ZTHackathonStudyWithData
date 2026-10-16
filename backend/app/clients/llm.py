"""Azure AI Foundry'deki sohbet modeline erişim."""

from typing import Protocol

from openai import OpenAI, OpenAIError

from app.config import Settings


class LLMError(Exception):
    """Model çağrısı başarısız oldu ya da yapılandırma eksik."""


class LLMClient(Protocol):
    def complete(self, system_prompt: str, user_message: str) -> str: ...


def _base_url(endpoint: str) -> str:
    endpoint = endpoint.strip().rstrip("/")
    if endpoint.endswith("/openai/v1"):
        return endpoint
    return f"{endpoint}/openai/v1"


class AzureLLMClient:
    """Foundry'deki deploy'a OpenAI v1 uyumlu uç üzerinden bağlanır."""

    def __init__(self, settings: Settings) -> None:
        missing = [
            name
            for name, value in (
                ("AZURE_OPENAI_ENDPOINT", settings.azure_openai_endpoint),
                ("AZURE_OPENAI_API_KEY", settings.azure_openai_api_key),
            )
            if not value.strip()
        ]
        if missing:
            raise LLMError(f"Eksik ortam değişkeni: {', '.join(missing)}")

        self._deployment = settings.chat_deployment
        self._client = OpenAI(
            base_url=_base_url(settings.azure_openai_endpoint),
            api_key=settings.azure_openai_api_key,
            timeout=settings.llm_timeout_seconds,
            max_retries=1,
        )

    def complete(self, system_prompt: str, user_message: str) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
        except OpenAIError as exc:
            raise LLMError(f"Model çağrısı başarısız: {type(exc).__name__}") from exc

        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise LLMError("Model boş yanıt döndü")
        return content
