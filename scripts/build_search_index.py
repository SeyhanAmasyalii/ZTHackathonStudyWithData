"""Azure AI Search'ü Azure SQL'e bağlar: hata türleri ve hazır çözüm indeksleri + 5 dk indexer.

Kullanım (repo kökünden):
    uv run --directory backend python ../scripts/build_search_index.py                    # loglar
    uv run --directory backend python ../scripts/build_search_index.py --indeks cozumler
    uv run --directory backend python ../scripts/build_search_index.py --indeks hepsi
    uv run --directory backend python ../scripts/build_search_index.py --dene "adres kaydetmiyor"

1. SQL'de db/search_views.sql çalışır: `dbo.v_hata_turleri` ve `dbo.v_cozum_sablonlari` (+ row_ver).
2. AI Search'te her indeks için kurulur: veri kaynağı (SQL, yüksek su işareti), indeks (kelime +
   vektör, Foundry vektörleştiricisi), beceri kümesi (Foundry embedding), indexer (5 dakikada bir).
3. Indexer hemen bir kez çalıştırılır, bitmesi beklenir, örnek bir arama yapılır.
Sonrasında AI Search SQL'deki değişiklikleri kendisi alır; betiği tekrar çalıştırmak gerekmez
(tekrar çalıştırmak güvenlidir: indeks baştan kurulur). `--zamanlamasiz`: 5 dk zamanlaması olmadan
kur (ücretsiz SQL'i sürekli uyanık tutmamak için, prova sonrası). `--dene METİN`: kurulum yapmadan
hazır çözüm indeksinde arar, ham benzerliği ve kodun hesapladığı eşleşme yüzdesini yazar
(eşik ayarı: app/services/solution_index.py).

Ayarlar backend/.env'den: SQL_SERVER, SQL_DATABASE, SQL_USER, SQL_PASSWORD (indexer bunlarla
bağlanır), SEARCH_ENDPOINT, SEARCH_API_KEY (yönetici anahtarı), SEARCH_LOG_INDEX,
SEARCH_SOLUTION_INDEX (boşsa mercek-cozumler), AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY,
EMBEDDING_DEPLOYMENT. Bağlantı bilgileri yalnızca Azure'a (AI Search) gönderilir; ekrana ve repoya
yazılmaz.
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
from app.services import log_index, solution_index  # noqa: E402
from app.services.log_index import (  # noqa: E402
    SCHEDULE,
    LogSearch,
    SearchNames,
    datasource_definition,
    indexer_connection_string,
    indexer_definition,
    skillset_definition,
)
from app.services.solution_index import (  # noqa: E402
    MATCH_THRESHOLD,
    SolutionSearch,
    cosine_from_score,
    match_score,
)

LOG_SAMPLE = "abone numarası kabul edilmiyor"
SOLUTION_SAMPLE = "müşteri adres bilgisini kaydedemiyorum"
DEFAULT_SOLUTION_INDEX = "mercek-cozumler"
WAIT_SECONDS = 300


def create_views(settings) -> dict[str, int]:
    text = (ROOT / "db" / "search_views.sql").read_text(encoding="utf-8")
    with sql.connect(settings) as connection:
        cursor = connection.cursor()
        for batch in schema_batches(text):
            cursor.execute(batch)
        connection.commit()
        counts = {}
        for view in (log_index.SQL_VIEW, solution_index.SQL_VIEW):
            cursor.execute(f"SELECT COUNT(*) FROM dbo.{view}")
            counts[view] = cursor.fetchone()[0]
        return counts


def solution_index_name(settings) -> str:
    return settings.search_solution_index or DEFAULT_SOLUTION_INDEX


def print_log_hits(client: AzureSearchClient, index: str) -> None:
    print(f"Örnek arama: '{LOG_SAMPLE}'")
    for hit in LogSearch(client, index)(LOG_SAMPLE, None, 3):
        print(
            f"  {hit['screen_code']} {hit['error_number']} {hit['error_code']} "
            f"{hit.get('institution_code') or ''} · {hit['log_count']} log · {hit['message'][:60]}"
        )


def print_solution_hits(client: AzureSearchClient, index: str, text: str) -> None:
    print(f"Arama: '{text}' (eşik %{round(MATCH_THRESHOLD * 100)})")
    for hit in SolutionSearch(client, index)(text, 5):
        cosine = cosine_from_score(hit.get("@search.score") or 0)
        percent = round(match_score(cosine, None, hit.get("error_code")) * 100)
        mark = "✓" if percent >= MATCH_THRESHOLD * 100 else " "
        print(
            f"  {mark} {hit['solution_template_id']} %{percent:<3} (benzerlik {cosine:.3f}) "
            f"{hit.get('title') or ''}"
        )


def build(
    client: AzureSearchClient,
    names: SearchNames,
    view: str,
    index: dict,
    what: str,
    connection_string: str,
    settings,
    schedule: str | None,
) -> None:
    client.delete("indexers", names.indexer)
    client.delete("indexes", names.index)
    client.put("datasources", datasource_definition(names, connection_string, view))
    client.put("indexes", index)
    client.put("skillsets", skillset_definition(names, settings, what))
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
        "--indeks",
        choices=("loglar", "cozumler", "hepsi"),
        default="loglar",
        help="Kurulacak indeks: loglar (hata_ara), cozumler (benzer_cozum_ara) ya da hepsi",
    )
    parser.add_argument(
        "--zamanlamasiz",
        action="store_true",
        help="Indexer'ı 5 dk zamanlaması olmadan kur (yalnızca bu çalıştırmada bir kez çalışır)",
    )
    parser.add_argument(
        "--dene",
        metavar="METIN",
        help="Kurulum yapmadan hazır çözüm indeksinde ara (benzerlik ve eşleşme yüzdesi)",
    )
    args = parser.parse_args()
    settings = get_settings()
    if args.dene:
        if not settings.search_endpoint:
            sys.exit("backend/.env'de eksik: SEARCH_ENDPOINT")
        client = AzureSearchClient(settings)
        print_solution_hits(client, solution_index_name(settings), args.dene)
        return

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

    counts = create_views(settings)
    print(
        f"✓ SQL görünümleri: dbo.{log_index.SQL_VIEW} {counts[log_index.SQL_VIEW]} hata türü · "
        f"dbo.{solution_index.SQL_VIEW} {counts[solution_index.SQL_VIEW]} hazır çözüm"
    )

    client = AzureSearchClient(settings)
    schedule = None if args.zamanlamasiz else SCHEDULE
    if args.indeks in ("loglar", "hepsi"):
        names = SearchNames(settings.search_log_index)
        index = log_index.index_definition(names.index, settings)
        build(
            client,
            names,
            log_index.SQL_VIEW,
            index,
            "Hata türü",
            connection_string,
            settings,
            schedule,
        )
        print_log_hits(client, names.index)
    if args.indeks in ("cozumler", "hepsi"):
        names = SearchNames(solution_index_name(settings))
        index = solution_index.index_definition(names.index, settings)
        build(
            client,
            names,
            solution_index.SQL_VIEW,
            index,
            "Hazır çözüm",
            connection_string,
            settings,
            schedule,
        )
        print_solution_hits(client, names.index, SOLUTION_SAMPLE)


if __name__ == "__main__":
    try:
        main()
    except (SearchError, ValueError) as exc:
        sys.exit(f"✗ {exc}")
