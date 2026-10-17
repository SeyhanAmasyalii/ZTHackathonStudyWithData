"""Kibana hata türlerinin AI Search indeksi (`mercek-loglar`): kaynak Azure SQL, indexer günceller.

Akış (kurulum: scripts/build_search_index.py):
  Azure SQL `dbo.v_hata_turleri` (db/search_views.sql; 2002 Warning/Error log → 107 hata türü)
    → veri kaynağı (yüksek su işareti `hwm`: yalnızca değişen türler)
    → indexer, 5 dakikada bir → beceri: Foundry embedding (metin → vektör)
    → indeks (kelime + vektör alanı; sorgu metnini de AI Search vektöre çevirir).
Arama yalnızca "hangi hata türü?" sorusunu yanıtlar; sayım ve zaman aralığı kibana_sorgula'dadır.
"""

from dataclasses import dataclass
from typing import Any

from app.clients.llm import _base_url
from app.clients.search import AzureSearchClient
from app.config import Settings

SQL_VIEW = "v_hata_turleri"
EMBEDDING_DIMENSIONS = 1536  # text-embedding-3-small
VECTOR_FIELD = "content_vector"
SCHEDULE = "PT5M"  # indexer en sık 5 dakikada bir çalışabilir
RESULT_FIELDS = (
    "screen_code",
    "screen_name",
    "error_number",
    "error_code",
    "institution_code",
    "institution_name",
    "bill_type",
    "message",
    "explanation",
    "log_count",
    "customer_count",
    "first_seen",
    "last_seen",
)


@dataclass(frozen=True)
class SearchNames:
    index: str

    @property
    def datasource(self) -> str:
        return f"{self.index}-sql"

    @property
    def skillset(self) -> str:
        return f"{self.index}-embedding"

    @property
    def indexer(self) -> str:
        return f"{self.index}-indexer"


def foundry_resource_uri(endpoint: str) -> str:
    """https://<kaynak>.openai.azure.com (sonunda /openai/v1 olmadan)."""
    return _base_url(endpoint).removesuffix("/openai/v1")


def _foundry(settings: Settings) -> dict[str, str]:
    return {
        "resourceUri": foundry_resource_uri(settings.azure_openai_endpoint),
        "deploymentId": settings.embedding_deployment,
        "apiKey": settings.azure_openai_api_key,
        "modelName": settings.embedding_deployment,
    }


def index_definition(name: str, settings: Settings) -> dict[str, Any]:
    def text(field: str, searchable: bool = False, filterable: bool = False) -> dict[str, Any]:
        spec: dict[str, Any] = {
            "name": field,
            "type": "Edm.String",
            "searchable": searchable,
            "filterable": filterable,
            "retrievable": True,
        }
        if searchable:
            spec["analyzer"] = "tr.microsoft"
        return spec

    return {
        "name": name,
        "fields": [
            {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
            text("screen_code", filterable=True),
            text("screen_name", searchable=True),
            {"name": "error_number", "type": "Edm.Int32", "filterable": True},
            text("error_code", searchable=True, filterable=True),
            text("institution_code", filterable=True),
            text("institution_name", searchable=True),
            text("bill_type", searchable=True),
            text("message", searchable=True),
            text("explanation", searchable=True),
            text("content", searchable=True),
            {"name": "log_count", "type": "Edm.Int32", "filterable": True},
            {"name": "customer_count", "type": "Edm.Int32"},
            {"name": "first_seen", "type": "Edm.DateTimeOffset", "filterable": True},
            {"name": "last_seen", "type": "Edm.DateTimeOffset", "filterable": True},
            {
                "name": VECTOR_FIELD,
                "type": "Collection(Edm.Single)",
                "searchable": True,
                "retrievable": False,
                "dimensions": EMBEDDING_DIMENSIONS,
                "vectorSearchProfile": "vektor",
            },
        ],
        "vectorSearch": {
            "algorithms": [{"name": "hnsw", "kind": "hnsw"}],
            "profiles": [{"name": "vektor", "algorithm": "hnsw", "vectorizer": "foundry"}],
            # Sorgu metnini AI Search, Foundry embedding'iyle kendisi vektöre çevirir.
            "vectorizers": [
                {
                    "name": "foundry",
                    "kind": "azureOpenAI",
                    "azureOpenAIParameters": _foundry(settings),
                }
            ],
        },
    }


def indexer_connection_string(settings: Settings) -> str:
    """Indexer'ın SQL bağlantısı (SQL kimlik doğrulaması); AI Search'te saklanır, repoya girmez."""
    if not settings.sql_user or not settings.sql_password:
        raise ValueError("Indexer için SQL_USER ve SQL_PASSWORD gerekli (backend/.env)")
    server = settings.sql_server.strip().removeprefix("tcp:")
    if "," not in server:
        server = f"{server},1433"
    password = settings.sql_password.replace("}", "}}")
    return (
        f"Server=tcp:{server};Database={settings.sql_database};User ID={settings.sql_user};"
        f"Password={{{password}}};Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;"
    )


def datasource_definition(names: SearchNames, connection_string: str) -> dict[str, Any]:
    return {
        "name": names.datasource,
        "type": "azuresql",
        "credentials": {"connectionString": connection_string},
        "container": {"name": SQL_VIEW},
        "dataChangeDetectionPolicy": {
            "@odata.type": "#Microsoft.Azure.Search.HighWaterMarkChangeDetectionPolicy",
            "highWaterMarkColumnName": "hwm",
        },
    }


def skillset_definition(names: SearchNames, settings: Settings) -> dict[str, Any]:
    return {
        "name": names.skillset,
        "description": "Hata türü metnini Foundry embedding ile vektöre çevirir",
        "skills": [
            {
                "@odata.type": "#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill",
                "name": "embedding",
                "context": "/document",
                **_foundry(settings),
                "dimensions": EMBEDDING_DIMENSIONS,
                "inputs": [{"name": "text", "source": "/document/content"}],
                "outputs": [{"name": "embedding", "targetName": VECTOR_FIELD}],
            }
        ],
    }


def indexer_definition(names: SearchNames, schedule: str | None = SCHEDULE) -> dict[str, Any]:
    definition: dict[str, Any] = {
        "name": names.indexer,
        "dataSourceName": names.datasource,
        "targetIndexName": names.index,
        "skillsetName": names.skillset,
        # Anahtar Base64'e çevrilir: kimlik metnindeki karakterler AI Search kurallarına uysun.
        "fieldMappings": [
            {
                "sourceFieldName": "id",
                "targetFieldName": "id",
                "mappingFunction": {"name": "base64Encode"},
            }
        ],
        "outputFieldMappings": [
            {"sourceFieldName": f"/document/{VECTOR_FIELD}", "targetFieldName": VECTOR_FIELD}
        ],
    }
    if schedule:
        definition["schedule"] = {"interval": schedule}
    return definition


def search_body(text: str, screen_code: str | None, top: int) -> dict[str, Any]:
    """Hibrit arama: kelime (BM25) + vektör (sorgu metnini AI Search vektöre çevirir), RRF."""
    body: dict[str, Any] = {
        "search": text,
        "searchFields": "content",
        "vectorQueries": [{"kind": "text", "text": text, "fields": VECTOR_FIELD, "k": top}],
        "select": ",".join(RESULT_FIELDS),
        "top": top,
    }
    if screen_code:
        # Ekran kodu yalnızca büyük harf/rakam: tools.hata_ara doğrular.
        body["filter"] = f"screen_code eq '{screen_code}'"
    return body


@dataclass
class LogSearch:
    client: AzureSearchClient
    index: str

    def __call__(self, text: str, screen_code: str | None, top: int) -> list[dict[str, Any]]:
        return self.client.search(self.index, search_body(text, screen_code, top))
