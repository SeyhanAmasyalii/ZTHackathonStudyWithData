"""Hazır çözümlerin AI Search indeksi (`mercek-cozumler`) ve eşleşme yüzdesi.

Akış (kurulum: scripts/build_search_index.py --indeks cozumler):
  Azure SQL `dbo.v_cozum_sablonlari` (db/search_views.sql; 37 şablon + kapanmış çağrı notları)
    → veri kaynağı (yüksek su işareti `hwm`) → indexer, 5 dakikada bir → Foundry embedding → indeks.
Eşleşme yüzdesini kod hesaplar (AI çıkarmaz): sorgu ile belge arasındaki anlam benzerliği
(vektör araması, cosine) + hata kodu aynıysa ek puan. Eşik %75 (MATCH_THRESHOLD).
"""

import json
from dataclasses import dataclass
from typing import Any

from app.clients.search import AzureSearchClient
from app.config import Settings
from app.services.log_index import EMBEDDING_DIMENSIONS, VECTOR_FIELD, foundry_params

SQL_VIEW = "v_cozum_sablonlari"
MATCH_THRESHOLD = 0.75
# Cosine benzerliği yüzdeye çevrilir: SIMILARITY_FLOOR ve altı %0, SIMILARITY_CEIL ve üstü %100.
# text-embedding-3-small'da ilgisiz Türkçe metinler bile ~0,2 benzerlik verir; değerler
# scripts/build_search_index.py --dene ile ölçülerek ayarlanır.
SIMILARITY_FLOOR = 0.20
SIMILARITY_CEIL = 0.70
ERROR_CODE_BONUS = 0.15
RESULT_FIELDS = (
    "solution_template_id",
    "title",
    "symptom",
    "root_cause",
    "steps",
    "error_code",
    "closure_code",
    "sub_closure_code",
    "department_id",
    "closed_count",
)


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
            text("solution_template_id", filterable=True),
            text("title", searchable=True),
            text("symptom", searchable=True),
            text("root_cause", searchable=True),
            text("steps"),
            text("error_code", filterable=True),
            text("closure_code", filterable=True),
            text("sub_closure_code"),
            text("department_id", filterable=True),
            {"name": "closed_count", "type": "Edm.Int32"},
            text("user_notes", searchable=True),
            text("content", searchable=True),
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
            # Varsayılan ölçü cosine: puan (@search.score) cosine benzerliğinden türetilir.
            "algorithms": [{"name": "hnsw", "kind": "hnsw"}],
            "profiles": [{"name": "vektor", "algorithm": "hnsw", "vectorizer": "foundry"}],
            "vectorizers": [
                {
                    "name": "foundry",
                    "kind": "azureOpenAI",
                    "azureOpenAIParameters": foundry_params(settings),
                }
            ],
        },
    }


def search_body(text: str, top: int) -> dict[str, Any]:
    """Yalnızca vektör araması: puan cosine'e geri çevrilebilsin (hibrit RRF puanı yüzde değil)."""
    return {
        "vectorQueries": [{"kind": "text", "text": text, "fields": VECTOR_FIELD, "k": top}],
        "select": ",".join(RESULT_FIELDS),
        "top": top,
    }


def cosine_from_score(score: float) -> float:
    """AI Search cosine puanı: score = 1 / (1 + (1 - cos)) → cos = 2 - 1/score."""
    if score <= 0:
        return 0.0
    return max(-1.0, min(1.0, 2 - 1 / score))


def match_score(cosine: float, query_error_code: str | None, doc_error_code: str | None) -> float:
    """0–1 eşleşme: anlam benzerliği ölçeklenir, hata kodu aynıysa ek puan."""
    span = SIMILARITY_CEIL - SIMILARITY_FLOOR
    semantic = min(1.0, max(0.0, (cosine - SIMILARITY_FLOOR) / span))
    same_code = bool(query_error_code) and query_error_code == doc_error_code
    return min(1.0, semantic + (ERROR_CODE_BONUS if same_code else 0.0))


def parse_steps(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if not isinstance(value, str) or not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return [value]
    return [str(item) for item in parsed] if isinstance(parsed, list) else [value]


@dataclass
class SolutionSearch:
    client: AzureSearchClient
    index: str

    def __call__(self, text: str, top: int) -> list[dict[str, Any]]:
        return self.client.search(self.index, search_body(text, top))
