"""Azure AI Search ve Foundry embedding istemcileri (V7, V8). Yalnızca standart kütüphane (urllib).

Ortam değişkenleri:
  SEARCH_ENDPOINT, SEARCH_API_KEY (yoksa azure-identity ile Entra token)
  AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY (yoksa Entra token), EMBEDDING_DEPLOYMENT (varsayılan embedding),
  EMBEDDING_DIM (varsayılan 1536), AZURE_OPENAI_API_VERSION (varsayılan 2024-10-21)

Eşitleme iki yolla yapılır (load_all.py --search-mode):
  indexer (varsayılan) · AI Search, Azure SQL'deki 3 tabloyu kendisi okur (değişiklik takibiyle, 5 dakikada bir ya da
                         run_indexer ile hemen); embedding'i skillset içinde Foundry'ye kendisi ürettirir.
                         Ek ortam değişkenleri: SQL_RESOURCE_ID (Search'ün Managed Identity'siyle) ya da
                         SEARCH_SQL_CONNECTION (tam bağlantı metni; yalnızca ortamda), EMBEDDING_MODEL.
  push                 · Betik CSV'leri okur, embedding'i kendisi üretir, belgeleri yükler (yetki çıkmazsa yedek).
Ayrıntı: docs/mercek-sql-search-esitleme.md

Skor: vektör sorgusunda Azure AI Search cosine için @search.score = 1 / (1 + (1 − cos)) döner.
similarity() bunu 0–1 aralığındaki benzerliğe (cos) çevirir; eşik (MATCH_THRESHOLD, 0,75) bu değerle karşılaştırılır.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Dict, Iterable, List, Optional

from db import SEARCH_SOURCES

SEARCH_API_VERSION = "2024-07-01"
EMBED_BATCH = 50
MAX_RETRIES = 4

# §10: indeks alanları. (ad, tür, özellikler) · özellikler: k=key, s=searchable, f=filterable, r=retrievable
INDEXES: Dict[str, List] = {
    "solutions": [("id", "s", "kfr"), ("title", "s", "sr"), ("symptom", "s", "sr"), ("root_cause", "s", "sr"),
                  ("steps", "s", "sr"), ("error_code", "s", "fr"), ("service_id", "s", "fr")],
    "requests": [("id", "s", "kfr"), ("title", "s", "sr"), ("description", "s", "sr"), ("type", "s", "fr"),
                 ("components", "s", "sr"), ("services", "s", "sr"), ("effort_md", "i", "fr"), ("status", "s", "fr")],
    "announcements": [("id", "s", "kfr"), ("institution", "s", "sfr"), ("published_at", "d", "fr"),
                      ("effective_at", "d", "fr"), ("title", "s", "sr"), ("body", "s", "sr")],
}
TEXT_FIELDS = {"solutions": ["title", "symptom", "root_cause", "steps"], "requests": ["title", "description"],
               "announcements": ["institution", "title", "body"]}
# SQL kolonu → indeks alanı (indexer fieldMappings). Aynı adlı alanlar kendiliğinden eşlenir.
FIELD_MAPPINGS = {"solutions": {"solution_id": "id"},
                  "requests": {"request_id": "id", "components_json": "components", "services_json": "services"},
                  "announcements": {"ann_id": "id"}}
SKILLSET = "mercek-embedding"
VECTORIZER = "mercek-aoai"
SCHEDULE = "PT5M"  # AI Search'ün izin verdiği en kısa aralık
COMPLETED_REQUESTS = "status eq 'tamamlandi'"  # efor tahmini ve benzer talep yalnızca biten işlerden


def similarity(search_score: float) -> float:
    """Azure cosine skorunu (1/(2−cos)) benzerliğe çevirir."""
    return round(2 - 1 / search_score, 4) if search_score > 0 else 0.0


def aoai_parameters() -> Dict:
    """Foundry embedding bağlantısı (skillset ve vektörleştirici). Anahtar yoksa Search'ün Managed Identity'si kullanılır.
    Anahtar yalnızca Azure'daki tanıma yazılır; repoya ve loga girmez."""
    params = {"resourceUri": os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/"),
              "deploymentId": os.environ.get("EMBEDDING_DEPLOYMENT", "embedding"),
              "modelName": os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")}
    if os.environ.get("AZURE_OPENAI_API_KEY"):
        params["apiKey"] = os.environ["AZURE_OPENAI_API_KEY"]
    return params


def index_definition(name: str, dim: int, vectorizer: bool = False) -> Dict:
    types = {"s": "Edm.String", "i": "Edm.Int32", "d": "Edm.DateTimeOffset"}
    fields = []
    for fname, ftype, flags in INDEXES[name]:
        field = {"name": fname, "type": types[ftype], "key": "k" in flags, "filterable": "f" in flags,
                 "retrievable": True, "searchable": "s" in flags and ftype == "s"}
        if field["searchable"]:
            field["analyzer"] = "tr.microsoft"
        fields.append(field)
    fields.append({"name": "content_vector", "type": "Collection(Edm.Single)", "searchable": True,
                   "retrievable": False, "dimensions": dim, "vectorSearchProfile": "mercek-hnsw"})
    profile = {"name": "mercek-hnsw", "algorithm": "hnsw"}
    vector_search = {"algorithms": [{"name": "hnsw", "kind": "hnsw",
                                     "hnswParameters": {"metric": "cosine", "m": 4, "efConstruction": 400}}],
                     "profiles": [profile]}
    if vectorizer:  # sorgu metnini de Search kendisi vektöre çevirebilsin (kind: text)
        profile["vectorizer"] = VECTORIZER
        vector_search["vectorizers"] = [{"name": VECTORIZER, "kind": "azureOpenAI",
                                         "azureOpenAIParameters": aoai_parameters()}]
    return {"name": name, "fields": fields, "vectorSearch": vector_search}


# ---------------------------------------------------------------------------
# Otomatik eşitleme: veri kaynağı → skillset (embedding) → indexer
# ---------------------------------------------------------------------------
def sql_connection_string() -> str:
    full = os.environ.get("SEARCH_SQL_CONNECTION")
    if full:
        return full
    resource, database = os.environ.get("SQL_RESOURCE_ID"), os.environ.get("SQL_DATABASE")
    if resource and database:  # Search'ün Managed Identity'si SQL'de kullanıcı olarak tanımlı olmalı
        return f"Database={database};ResourceId={resource};Connection Timeout=30;"
    raise SystemExit("indexer modu için SQL_RESOURCE_ID + SQL_DATABASE ya da SEARCH_SQL_CONNECTION gerekli "
                     "(yetki yoksa: --search-mode push)")


def datasource_definition(table: str, connection: str) -> Dict:
    return {"name": f"mercek-sql-{table}", "type": "azuresql", "credentials": {"connectionString": connection},
            "container": {"name": table},
            "dataChangeDetectionPolicy": {"@odata.type": "#Microsoft.Azure.Search.SqlIntegratedChangeTrackingPolicy"}}


def skillset_definition(dim: int) -> Dict:
    skill = {"@odata.type": "#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill", "name": "embed", "context": "/document",
             "dimensions": dim, "inputs": [{"name": "text", "source": "/document/search_text"}],
             "outputs": [{"name": "embedding", "targetName": "content_vector"}], **aoai_parameters()}
    return {"name": SKILLSET, "description": "search_text → content_vector (Foundry embedding)", "skills": [skill]}


def indexer_definition(table: str) -> Dict:
    return {"name": f"mercek-ix-{table}", "dataSourceName": f"mercek-sql-{table}", "targetIndexName": table,
            "skillsetName": SKILLSET, "schedule": {"interval": SCHEDULE},
            "parameters": {"batchSize": 50, "maxFailedItems": 0},
            "fieldMappings": [{"sourceFieldName": a, "targetFieldName": b} for a, b in FIELD_MAPPINGS[table].items()],
            "outputFieldMappings": [{"sourceFieldName": "/document/content_vector", "targetFieldName": "content_vector"}]}


def content_text(index: str, doc: Dict) -> str:
    return "\n".join(str(doc[f]) for f in TEXT_FIELDS[index] if doc.get(f))


# ---------------------------------------------------------------------------
# Belge üreticileri (CSV/JSON satırı → indeks belgesi)
# ---------------------------------------------------------------------------
def solution_doc(r: Dict) -> Dict:
    steps = json.loads(r["steps"]) if r.get("steps") else []
    return {"id": r["solution_id"], "title": r["title"], "symptom": r.get("symptom") or "",
            "root_cause": r.get("root_cause") or "", "steps": " ".join(steps), "error_code": r.get("error_code") or "",
            "service_id": r.get("service_id") or ""}


def request_doc(r: Dict) -> Dict:
    comps = ", ".join(c["kind"] for c in json.loads(r["components_json"] or "[]"))
    services = ", ".join(s["service_id"] for s in json.loads(r["services_json"] or "[]"))
    return {"id": r["request_id"], "title": r["title"], "description": r.get("description") or "", "type": r["type"],
            "components": comps, "services": services, "effort_md": int(r["effort_md"]) if r.get("effort_md") else None,
            "status": r.get("status") or ""}


def announcement_doc(r: Dict) -> Dict:
    return {"id": r["ann_id"], "institution": r["institution"], "published_at": f"{r['published_at']}T00:00:00+03:00",
            "effective_at": f"{r['effective_at']}T00:00:00+03:00", "title": r["title"], "body": r["body"]}


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
def _entra(scope: str) -> str:  # pragma: no cover - Azure gerektirir
    try:
        from azure.identity import DefaultAzureCredential
    except ImportError as exc:
        raise SystemExit("API anahtarı yok ve azure-identity kurulu değil") from exc
    return DefaultAzureCredential().get_token(scope).token


def _request(method: str, url: str, headers: Dict[str, str], body: Optional[Dict] = None) -> Dict:  # pragma: no cover
    data = json.dumps(body).encode("utf-8") if body is not None else None
    for attempt in range(1, MAX_RETRIES + 1):
        req = urllib.request.Request(url, data=data, method=method,
                                     headers={"Content-Type": "application/json", **headers})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as err:
            if err.code in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES:
                time.sleep(2 * attempt)
                continue
            detail = err.read().decode("utf-8", "replace")[:500]
            raise RuntimeError(f"{method} {url.split('?')[0]} → {err.code}: {detail}") from err
    raise RuntimeError("istek başarısız")


class FoundryEmbedder:  # pragma: no cover - Azure gerektirir
    def __init__(self):
        self.endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
        if not self.endpoint:
            raise SystemExit("AZURE_OPENAI_ENDPOINT tanımlı değil")
        self.deployment = os.environ.get("EMBEDDING_DEPLOYMENT", "embedding")
        self.version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21")
        key = os.environ.get("AZURE_OPENAI_API_KEY")
        self.headers = {"api-key": key} if key else {
            "Authorization": f"Bearer {_entra('https://cognitiveservices.azure.com/.default')}"}

    def embed(self, texts: List[str]) -> List[List[float]]:
        url = f"{self.endpoint}/openai/deployments/{self.deployment}/embeddings?api-version={self.version}"
        data = _request("POST", url, self.headers, {"input": texts})
        return [d["embedding"] for d in sorted(data["data"], key=lambda d: d["index"])]


class AzureSearch:  # pragma: no cover - Azure gerektirir
    def __init__(self):
        self.endpoint = os.environ.get("SEARCH_ENDPOINT", "").rstrip("/")
        if not self.endpoint:
            raise SystemExit("SEARCH_ENDPOINT tanımlı değil")
        key = os.environ.get("SEARCH_API_KEY")
        self.headers = {"api-key": key} if key else {"Authorization": f"Bearer {_entra('https://search.azure.com/.default')}"}

    def _url(self, path: str) -> str:
        return f"{self.endpoint}{path}?api-version={SEARCH_API_VERSION}"

    def create_index(self, definition: Dict) -> None:
        name = definition["name"]
        try:
            _request("DELETE", self._url(f"/indexes/{name}"), self.headers)
        except RuntimeError as err:
            if "404" not in str(err):
                raise
        _request("PUT", self._url(f"/indexes/{name}"), self.headers, definition)

    def put(self, kind: str, definition: Dict) -> None:
        """kind: datasources | skillsets | indexers (oluştur ya da güncelle)."""
        _request("PUT", self._url(f"/{kind}/{definition['name']}"), self.headers, definition)

    def reset_indexer(self, name: str) -> None:
        _request("POST", self._url(f"/indexers/{name}/reset"), self.headers)

    def run_indexer(self, name: str) -> None:
        _request("POST", self._url(f"/indexers/{name}/run"), self.headers)

    def indexer_status(self, name: str) -> Dict:
        last = _request("GET", self._url(f"/indexers/{name}/status"), self.headers).get("lastResult") or {}
        return {"status": last.get("status"), "items": last.get("itemsProcessed", 0),
                "failed": last.get("itemsFailed", 0), "error": last.get("errorMessage")}

    def upload(self, index: str, docs: List[Dict]) -> None:
        payload = {"value": [{"@search.action": "mergeOrUpload", **d} for d in docs]}
        _request("POST", self._url(f"/indexes/{index}/docs/index"), self.headers, payload)

    def count(self, index: str) -> int:
        url = f"{self.endpoint}/indexes/{index}/docs/$count?api-version={SEARCH_API_VERSION}"
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return int(resp.read().decode("utf-8-sig"))

    def vector_search(self, index: str, vector: List[float], top: int = 5, filter: Optional[str] = None) -> List[Dict]:
        body = {"select": "id", "top": top,
                "vectorQueries": [{"kind": "vector", "vector": vector, "fields": "content_vector", "k": top}]}
        if filter:
            body["filter"] = filter
        data = _request("POST", self._url(f"/indexes/{index}/docs/search"), self.headers, body)
        return [{"id": d["id"], "score": similarity(d["@search.score"])} for d in data.get("value", [])]


# ---------------------------------------------------------------------------
# Yüksek seviye
# ---------------------------------------------------------------------------
def batched(items: List, size: int) -> Iterable[List]:
    for i in range(0, len(items), size):
        yield items[i:i + size]


def load_index(search, embedder, name: str, docs: List[Dict], dim: int) -> int:
    search.create_index(index_definition(name, dim))
    for batch in batched(docs, EMBED_BATCH):
        vectors = embedder.embed([content_text(name, d) for d in batch])
        for d, v in zip(batch, vectors):
            if len(v) != dim:
                raise SystemExit(f"EMBEDDING_DIM={dim} ama model {len(v)} boyut döndürdü")
            d["content_vector"] = v
        search.upload(name, batch)
    return len(docs)


def query(search, embedder, index: str, text: str, top: int = 5, filter: Optional[str] = None) -> List[Dict]:
    vector = embedder.embed([text])[0]
    return search.vector_search(index, vector, top, filter) if filter else search.vector_search(index, vector, top)


def setup_indexers(search, dim: int, connection: Optional[str] = None, reset: bool = True) -> List[str]:
    """Veri kaynağı, skillset, indeks (vektörleştiricili) ve indexer'ları kurar; ilk çalıştırmayı tetikler."""
    connection = connection or sql_connection_string()
    search.put("skillsets", skillset_definition(dim))
    names = []
    for table in SEARCH_SOURCES:
        search.put("datasources", datasource_definition(table, connection))
        search.create_index(index_definition(table, dim, vectorizer=True))
        ix = indexer_definition(table)
        search.put("indexers", ix)
        if reset:  # tablolar yeniden yüklendiyse değişiklik takibi baştan başlar
            search.reset_indexer(ix["name"])
        search.run_indexer(ix["name"])
        names.append(ix["name"])
    return names


def wait_indexers(search, names: List[str], timeout_s: int = 600, poll_s: float = 5, sleep=time.sleep) -> Dict[str, Dict]:
    """Tüm indexer'lar bitene kadar bekler; hata olursa durur."""
    waited, result = 0.0, {}
    while True:
        result = {n: search.indexer_status(n) for n in names}
        failed = {n: r for n, r in result.items() if r["status"] in ("transientFailure", "persistentFailure")}
        if failed:
            raise SystemExit(f"indexer hatası: {failed}")
        if all(r["status"] == "success" for r in result.values()):
            return result
        if waited >= timeout_s:
            raise SystemExit(f"indexer'lar {timeout_s} sn'de bitmedi: {result}")
        sleep(poll_s)
        waited += poll_s


def sync_now(search) -> List[str]:
    """Uygulama ya da demo_reset SQL'e yazdıktan sonra: 5 dakikayı beklemeden eşitle."""
    names = [f"mercek-ix-{t}" for t in SEARCH_SOURCES]
    for n in names:
        try:
            search.run_indexer(n)
        except RuntimeError as err:  # zaten çalışıyorsa (409) sorun değil
            if "409" not in str(err):
                raise
    return names
