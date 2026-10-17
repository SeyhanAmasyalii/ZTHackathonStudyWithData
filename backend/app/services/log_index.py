"""Kibana hata loglarının AI Search indeksi (`mercek-loglar`).

Her belge bir hata türüdür: aynı ekran + hata numarası + hata kodu + kurum. 2002 Warning/Error
logu 107 belgeye iner; böylece anlam araması aynı mesajın yüzlerce kopyasını döndürmez.
Arama yalnızca "hangi hata türü?" sorusunu yanıtlar; sayım ve zaman aralığı kibana_sorgula'dadır.
"""

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from app.clients.embeddings import Embedder
from app.clients.search import AzureSearchClient
from app.repositories.datav2 import Catalog, LogEntry

EMBEDDING_DIMENSIONS = 1536  # text-embedding-3-small
VECTOR_FIELD = "content_vector"
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


def log_index_definition(name: str, dimensions: int = EMBEDDING_DIMENSIONS) -> dict[str, Any]:
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
                "dimensions": dimensions,
                "vectorSearchProfile": "vektor",
            },
        ],
        "vectorSearch": {
            "algorithms": [{"name": "hnsw", "kind": "hnsw"}],
            "profiles": [{"name": "vektor", "algorithm": "hnsw"}],
        },
    }


def _doc_id(*parts: object) -> str:
    raw = "-".join("x" if part in (None, "") else str(part) for part in parts)
    return re.sub(r"[^A-Za-z0-9_-]", "_", raw)


def log_documents(catalog: Catalog, rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Hata türü başına bir belge (vektörsüz). `content` hem kelime hem anlam aramasına girer."""
    screens = {screen.code: screen for screen in catalog.screens}
    institutions = {inst.code: inst for inst in catalog.institutions}
    hints = {
        (rule.get("screen_code"), rule.get("error_number")): rule.get("explanation_hint") or ""
        for rule in rules
    }
    groups: dict[tuple, list[LogEntry]] = defaultdict(list)
    for log in catalog.logs:
        key = (log.screen_code, log.error_number, log.error_code, log.institution_code)
        groups[key].append(log)

    documents = []
    for (screen_code, error_number, error_code, institution_code), logs in sorted(
        groups.items(), key=lambda item: -len(item[1])
    ):
        screen = screens.get(screen_code)
        institution = institutions.get(institution_code or "")
        messages = sorted({log.message for log in logs})
        explanation = hints.get((screen_code, error_number), "")
        content_parts = [
            f"Ekran: {screen_code} {screen.name if screen else ''}".strip(),
            screen.description if screen else "",
            f"Kurum: {institution.name} ({institution.bill_type})" if institution else "",
            f"Hata {error_number or ''} {error_code or ''}".strip(),
            *messages,
            explanation,
        ]
        documents.append(
            {
                "id": _doc_id(screen_code, error_number, error_code, institution_code),
                "screen_code": screen_code,
                "screen_name": screen.name if screen else "",
                "error_number": error_number,
                "error_code": error_code,
                "institution_code": institution_code,
                "institution_name": institution.name if institution else None,
                "bill_type": institution.bill_type if institution else None,
                "message": " | ".join(messages),
                "explanation": explanation or None,
                "content": ". ".join(p.rstrip(". ") for p in content_parts if p.strip()) + ".",
                "log_count": len(logs),
                "customer_count": len({log.customer_id for log in logs if log.customer_id}),
                "first_seen": min(log.log_time for log in logs).isoformat(),
                "last_seen": max(log.log_time for log in logs).isoformat(),
            }
        )
    return documents


def search_body(
    text: str, vector: list[float], screen_code: str | None, top: int
) -> dict[str, Any]:
    """Hibrit arama: kelime (BM25) + vektör, sonuçlar RRF ile birleşir."""
    body: dict[str, Any] = {
        "search": text,
        "searchFields": "content",
        "vectorQueries": [{"kind": "vector", "vector": vector, "fields": VECTOR_FIELD, "k": top}],
        "select": ",".join(RESULT_FIELDS),
        "top": top,
    }
    if screen_code:
        # Ekran kodu yalnızca harf/rakam: ToolInputError ile doğrulanmış olarak gelir.
        body["filter"] = f"screen_code eq '{screen_code}'"
    return body


@dataclass
class LogSearch:
    client: AzureSearchClient
    embedder: Embedder
    index: str

    def __call__(self, text: str, screen_code: str | None, top: int) -> list[dict[str, Any]]:
        vector = self.embedder.embed([text])[0]
        return self.client.search(self.index, search_body(text, vector, screen_code, top))
