"""Mercek agent'ını Foundry Agent Service'te kurar ya da günceller (yeni sürüm).

Kullanım (repo kökünden; önce `az login`):
    uv run --directory backend python ../scripts/setup_agent.py

1. Talimat prompts/mercek-chat.md'den (ekran ve kurum listesiyle), araç tanımları backend
   kodundan alınır (kibana_sorgula, cagri_ara; AI Search ayarlıysa hata_ara, benzer_cozum_ara).
2. Foundry projesinde FOUNDRY_AGENT_NAME adlı agent'ın yeni sürümü oluşturulur.
3. Kısa bir deneme yapılır (araç gerektirmeyen soru).
Prompt ya da araç değişince betik tekrar çalıştırılır; LLM_MODE=agent iken backend bu agent'ı
çağırır (başka bir şey değişmez).

Ayarlar backend/.env'den: FOUNDRY_PROJECT_ENDPOINT, FOUNDRY_AGENT_NAME (varsayılan mercek-cagri),
CHAT_DEPLOYMENT (agent'ın modeli), SEARCH_ENDPOINT, SEARCH_SOLUTION_INDEX.
Kimlik: Microsoft Entra (az login); hesabınızın projede "Azure AI User" (ya da üstü) rolü olmalı.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import get_settings  # noqa: E402
from app.repositories.datav2 import json_catalog  # noqa: E402
from app.services.agent_setup import agent_definition  # noqa: E402

SAMPLE = "Kendini bir cümleyle tanıt; hangi araçları kullanabildiğini say."


def main() -> None:
    settings = get_settings()
    if not settings.foundry_project_endpoint:
        sys.exit("backend/.env'de eksik: FOUNDRY_PROJECT_ENDPOINT")

    from azure.ai.projects import AIProjectClient
    from azure.ai.projects.models import PromptAgentDefinition
    from azure.core.exceptions import HttpResponseError
    from azure.identity import DefaultAzureCredential

    catalog = json_catalog(settings.data_dir)
    body = agent_definition(settings, catalog.screens, catalog.institutions)
    tools = ", ".join(tool["name"] for tool in body["tools"])

    project = AIProjectClient(
        endpoint=settings.foundry_project_endpoint, credential=DefaultAzureCredential()
    )
    try:
        version = project.agents.create_version(
            agent_name=settings.foundry_agent_name,
            definition=PromptAgentDefinition(body),
            description="Mercek: banka personeline ilk temas asistanı (araçlar backend'de)",
        )
    except HttpResponseError as exc:
        sys.exit(f"✗ Agent oluşturulamadı: {exc.status_code} {str(exc.message)[:300]}")
    print(
        f"✓ Agent '{settings.foundry_agent_name}' sürüm {version.version} · "
        f"model {settings.chat_deployment} · araçlar: {tools}"
    )

    client = project.get_openai_client()
    response = client.responses.create(
        input=[{"role": "user", "content": SAMPLE}],
        extra_body={
            "agent_reference": {"name": settings.foundry_agent_name, "type": "agent_reference"}
        },
    )
    print(f"Deneme: {(response.output_text or '').strip()[:300]}")


if __name__ == "__main__":
    main()
