"""Kibana hata türlerini Azure AI Search'e yükler (`mercek-loglar` indeksi, hibrit arama).

Kullanım (repo kökünden):
    uv run --directory backend python ../scripts/build_search_index.py

1. 2002 Warning/Error logu hata türüne göre gruplanır (ekran + hata no + hata kodu + kurum).
2. Her belgenin metni Foundry'deki embedding deploy'uyla vektöre çevrilir.
3. İndeks silinip yeniden oluşturulur, belgeler yüklenir, örnek bir arama yapılır.

Ayarlar backend/.env'den: SEARCH_ENDPOINT, SEARCH_API_KEY (yönetici anahtarı; boşsa Entra ile),
SEARCH_LOG_INDEX, EMBEDDING_DEPLOYMENT, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY.
Veri sentetiktir (datav2); kişisel veri içermez. Anahtarlar ekrana yazılmaz.
"""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.clients.embeddings import AzureEmbedder  # noqa: E402
from app.clients.search import AzureSearchClient, SearchError  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.repositories.datav2 import json_catalog  # noqa: E402
from app.services.log_index import (  # noqa: E402
    VECTOR_FIELD,
    LogSearch,
    log_documents,
    log_index_definition,
)

EMBED_BATCH = 100
SAMPLE_QUERY = "abone numarası kabul edilmiyor"


def main() -> None:
    settings = get_settings()
    if not settings.search_endpoint:
        sys.exit(
            "SEARCH_ENDPOINT tanımlı değil: backend/.env dosyasına SEARCH_ENDPOINT=... ekleyin"
        )
    data_dir = ROOT / "datav2"
    rules = json.loads((data_dir / "error_handling_rules.json").read_text(encoding="utf-8"))
    documents = log_documents(json_catalog(data_dir), rules)
    print(f"✓ {len(documents)} hata türü ({sum(d['log_count'] for d in documents)} log)")

    embedder = AzureEmbedder(settings)
    contents = [doc["content"] for doc in documents]
    vectors: list[list[float]] = []
    for start in range(0, len(contents), EMBED_BATCH):
        vectors += embedder.embed(contents[start : start + EMBED_BATCH])
    for doc, vector in zip(documents, vectors, strict=True):
        doc[VECTOR_FIELD] = vector
    print(f"✓ Vektörler hazır ({settings.embedding_deployment}, {len(vectors[0])} boyut)")

    client = AzureSearchClient(settings)
    index = settings.search_log_index
    client.delete_index(index)
    client.put_index(log_index_definition(index, len(vectors[0])))
    client.upload(index, documents)
    for _ in range(10):  # yüklenen belgeler birkaç saniyede sayılır
        if client.count(index) == len(documents):
            break
        time.sleep(2)
    count = client.count(index)
    if count != len(documents):
        sys.exit(f"✗ İndekste {count} belge var, beklenen {len(documents)}")
    print(f"✓ İndeks '{index}': {count} belge")

    hits = LogSearch(client, embedder, index)(SAMPLE_QUERY, None, 3)
    print(f"Örnek arama: '{SAMPLE_QUERY}'")
    for hit in hits:
        print(
            f"  {hit['screen_code']} {hit['error_number']} {hit['error_code']} "
            f"{hit.get('institution_code') or ''} · {hit['log_count']} log · {hit['message'][:60]}"
        )


if __name__ == "__main__":
    try:
        main()
    except SearchError as exc:
        sys.exit(f"✗ {exc}")
