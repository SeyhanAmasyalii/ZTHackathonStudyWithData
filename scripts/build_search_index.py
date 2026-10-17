"""Azure AI Search'ü Azure SQL'e bağlar: hata türleri indeksi + 5 dakikalık indexer (bir kez).

Kullanım (repo kökünden):
    uv run --directory backend python ../scripts/build_search_index.py

1. SQL'de db/search_views.sql çalışır: `dbo.v_hata_turleri` görünümü (+ kibana_logs.row_ver).
2. AI Search'te kurulur: veri kaynağı (SQL, yüksek su işareti), indeks (kelime + vektör, Foundry
   vektörleştiricisi), beceri kümesi (Foundry embedding), indexer (5 dakikada bir).
3. Indexer hemen bir kez çalıştırılır, bitmesi beklenir, örnek bir arama yapılır.
Sonrasında AI Search SQL'deki değişiklikleri kendisi alır; betiği tekrar çalıştırmak gerekmez
(tekrar çalıştırmak güvenlidir: indeks baştan kurulur). `--zamanlamasiz`: 5 dk zamanlaması olmadan
kur (ücretsiz SQL'i sürekli uyanık tutmamak için, prova sonrası).

Ayarlar backend/.env'den: SQL_SERVER, SQL_DATABASE, SQL_USER, SQL_PASSWORD (indexer bunlarla
bağlanır), SEARCH_ENDPOINT, SEARCH_API_KEY (yönetici anahtarı), SEARCH_LOG_INDEX,
AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, EMBEDDING_DEPLOYMENT.
Bağlantı bilgileri yalnızca Azure'a (AI Search) gönderilir; ekrana ve repoya yazılmaz.
"""

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from datav2_tables import schema_batches  # noqa: E402

from app.clients.search import AzureSearchClient, SearchError  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.repositories import sql  # noqa: E402
from app.services.log_index import (  # noqa: E402
    SCHEDULE,
    SQL_VIEW,
    LogSearch,
    SearchNames,
    datasource_definition,
    index_definition,
    indexer_connection_string,
    indexer_definition,
    skillset_definition,
)

SAMPLE_QUERY = "abone numarası kabul edilmiyor"
WAIT_SECONDS = 300


def create_view(settings) -> int:
    text = (ROOT / "db" / "search_views.sql").read_text(encoding="utf-8")
    with sql.connect(settings) as connection:
        cursor = connection.cursor()
        for batch in schema_batches(text):
            cursor.execute(batch)
        connection.commit()
        cursor.execute(f"SELECT COUNT(*) FROM dbo.{SQL_VIEW}")
        return cursor.fetchone()[0]


def wait_for_indexer(client: AzureSearchClient, name: str) -> dict:
    deadline = time.time() + WAIT_SECONDS
    while time.time() < deadline:
        result = client.get(f"/indexers/{name}/status").get("lastResult") or {}
        if result.get("status") in ("success", "transientFailure", "persistentFailure"):
            return result
        time.sleep(5)
    sys.exit(f"✗ Indexer {WAIT_SECONDS} sn içinde bitmedi; portalda {name} → Yürütme geçmişi")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--zamanlamasiz",
        action="store_true",
        help="Indexer'ı 5 dk zamanlaması olmadan kur (yalnızca bu çalıştırmada bir kez çalışır)",
    )
    args = parser.parse_args()
    settings = get_settings()
    missing = [
        name
        for name, value in (
            ("SQL_SERVER", settings.sql_server),
            ("SEARCH_ENDPOINT", settings.search_endpoint),
            ("AZURE_OPENAI_ENDPOINT", settings.azure_openai_endpoint),
            ("AZURE_OPENAI_API_KEY", settings.azure_openai_api_key),
        )
        if not value
    ]
    if missing:
        sys.exit(f"backend/.env'de eksik: {', '.join(missing)}")
    connection_string = indexer_connection_string(settings)

    rows = create_view(settings)
    print(f"✓ SQL görünümü dbo.{SQL_VIEW}: {rows} hata türü")

    client = AzureSearchClient(settings)
    names = SearchNames(settings.search_log_index)
    client.delete("indexers", names.indexer)
    client.delete("indexes", names.index)
    client.put("datasources", datasource_definition(names, connection_string))
    client.put("indexes", index_definition(names.index, settings))
    client.put("skillsets", skillset_definition(names, settings))
    schedule = None if args.zamanlamasiz else SCHEDULE
    # Indexer oluşturulunca bir kez kendiliğinden çalışır.
    client.put("indexers", indexer_definition(names, schedule))
    when = "zamanlamasız" if schedule is None else "5 dakikada bir"
    print(
        f"✓ AI Search: veri kaynağı, indeks '{names.index}', embedding becerisi, indexer ({when})"
    )

    result = wait_for_indexer(client, names.indexer)
    processed, failed = result.get("itemsProcessed", 0), result.get("itemsFailed", 0)
    if result.get("status") != "success" or failed:
        errors = "; ".join(e.get("errorMessage", "")[:200] for e in result.get("errors", [])[:3])
        sys.exit(
            f"✗ Indexer: {result.get('status')} · {processed} işlendi, {failed} hatalı. {errors}"
        )
    count = client.count(names.index)
    print(f"✓ Indexer çalıştı: {processed} belge işlendi · indekste {count} belge")

    hits = LogSearch(client, names.index)(SAMPLE_QUERY, None, 3)
    print(f"Örnek arama: '{SAMPLE_QUERY}'")
    for hit in hits:
        print(
            f"  {hit['screen_code']} {hit['error_number']} {hit['error_code']} "
            f"{hit.get('institution_code') or ''} · {hit['log_count']} log · {hit['message'][:60]}"
        )


if __name__ == "__main__":
    try:
        main()
    except (SearchError, ValueError) as exc:
        sys.exit(f"✗ {exc}")
