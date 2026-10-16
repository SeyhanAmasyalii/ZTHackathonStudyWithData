#!/usr/bin/env python3
"""Mercek verisini veritabanına ve AI Search'e yükler (V7). docs/mercek-sentetik-veri-uretimi.md §10.

Kullanım:
  python3 tools/mercek_data/load_all.py --sqlite                 # yerel: data/out/mercek.db
  python3 tools/mercek_data/load_all.py --sql                    # Azure SQL (SQL_SERVER, SQL_DATABASE, ...)
  python3 tools/mercek_data/load_all.py --search                 # AI Search: indexer'ları kurar (SQL'den otomatik eşitleme)
  python3 tools/mercek_data/load_all.py --search --search-mode push   # yedek: belgeleri betik yükler
  python3 tools/mercek_data/load_all.py --sync                   # indexer'ları hemen çalıştır (5 dk beklemeden)
  python3 tools/mercek_data/load_all.py --all                    # --sql + --search
  python3 tools/mercek_data/load_all.py --write-schema           # yalnızca data/schema.sql'i yeniden üretir

Girdiler: data/seed/catalog.json, announcements.json · tools/output/mercek-logs.ndjson · data/out/*.csv
Sıra: şema → katalog → duyurular → müşteri/kredi → loglar → temas → çözüm → çağrı → talep. Tek transaction.
Değerlendirme seti (eval_cases.json) indekse yüklenmez.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402
import search as srch  # noqa: E402

ROOT = db.ROOT
SEED = ROOT / "data" / "seed"
OUT = ROOT / "data" / "out"
LOGS = ROOT / "tools" / "output" / "mercek-logs.ndjson"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_csv(path: Path) -> List[Dict]:
    if not path.exists():
        raise SystemExit(f"{rel(path)} yok: önce V5/V6 betiklerini çalıştırın (tools/README.md)")
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_logs(path: Path) -> Iterable[Dict]:
    if not path.exists():
        raise SystemExit(f"{rel(path)} yok: önce V3 (inject_log_scenarios.py) çalıştırın")
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield db.flatten_log(json.loads(line))


def catalog_rows(catalog: Dict) -> Dict[str, List[Dict]]:
    screens = [{**{k: v for k, v in s.items() if k not in ("components", "flow", "files")},
                "components_json": s.get("components"), "flow_json": s.get("flow"), "files_json": s.get("files")}
               for s in catalog["screens"]]
    return {"services": catalog["services"], "screens": screens, "screen_services": catalog["screen_services"],
            "error_rules": catalog["error_rules"], "service_calendar": catalog["service_calendar"],
            "scope_addons": catalog["scope_addons"]}


def load_sql(database: db.Database, seed: Path = SEED, out: Path = OUT, logs: Path = LOGS) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    try:
        for stmt in db.ddl(database.dialect):
            database.execute(stmt)
        for table, rows in catalog_rows(load_json(seed / "catalog.json")).items():
            counts[table] = database.insert_many(table, rows)
        counts["announcements"] = database.insert_many("announcements", load_json(seed / "announcements.json"))
        for table in ("customers", "loans"):
            counts[table] = database.insert_many(table, read_csv(out / f"{table}.csv"))
        counts["banking_logs"] = database.insert_many("banking_logs", read_logs(logs))
        for table in ("contacts", "solutions", "incidents", "requests"):
            counts[table] = database.insert_many(table, read_csv(out / f"{table}.csv"))
        counts["mercek_events"] = 0
        database.commit()
    except BaseException:
        database.rollback()
        raise
    db.enable_change_tracking(database)  # tablolar yeniden yaratıldı: indexer takibi yeniden açılır
    return counts


def search_documents(seed: Path = SEED, out: Path = OUT) -> Dict[str, List[Dict]]:
    return {"solutions": [srch.solution_doc(r) for r in read_csv(out / "solutions.csv")],
            "requests": [srch.request_doc(r) for r in read_csv(out / "requests.csv")],
            "announcements": [srch.announcement_doc(r) for r in load_json(seed / "announcements.json")]}


def load_search(search, embedder, dim: int, seed: Path = SEED, out: Path = OUT) -> Dict[str, int]:
    return {name: srch.load_index(search, embedder, name, docs, dim)
            for name, docs in search_documents(seed, out).items()}


def sync_search(search, dim: int, wait: bool = True) -> Dict[str, int]:
    """Indexer modu: SQL'deki tablolar AI Search'e kendiliğinden akar. Önce --sql yüklenmiş olmalı."""
    names = srch.setup_indexers(search, dim)
    if wait:
        status = srch.wait_indexers(search, names)
        return {n: s["items"] for n, s in status.items()}
    return {n: 0 for n in names}


def print_counts(title: str, counts: Dict[str, int]) -> None:
    print(f"\n{title}")
    for k, v in counts.items():
        print(f"  {k:<18} {v:>7,}".replace(",", "."))


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sql", action="store_true", help="Azure SQL'e yükle")
    p.add_argument("--sqlite", nargs="?", const=str(db.DEFAULT_SQLITE), metavar="DOSYA", help="yerel SQLite'a yükle")
    p.add_argument("--search", action="store_true", help="AI Search indekslerini oluştur ve yükle")
    p.add_argument("--all", action="store_true", help="--sql ve --search")
    p.add_argument("--search-mode", choices=["indexer", "push"], default="indexer",
                   help="indexer: AI Search SQL'den kendisi çeker (varsayılan) · push: betik yükler (yedek)")
    p.add_argument("--sync", action="store_true", help="indexer'ları hemen çalıştır (uygulama SQL'e yazdıktan sonra)")
    p.add_argument("--write-schema", action="store_true", help="data/schema.sql'i üret")
    a = p.parse_args(argv)
    if not (a.sql or a.sqlite or a.search or a.all or a.write_schema or a.sync):
        p.error("en az bir hedef seçin: --sqlite, --sql, --search, --all, --sync, --write-schema")

    if a.write_schema:
        print(f"Şema yazıldı: {db.write_schema_file().relative_to(ROOT)}")
    if a.sqlite:
        database = db.Database.sqlite(Path(a.sqlite))
        print_counts(f"SQLite · {a.sqlite}", load_sql(database))
        database.close()
    if a.sql or a.all:
        database = db.Database.azure()
        print_counts(f"Azure SQL · {os.environ.get('SQL_DATABASE')}", load_sql(database))
        database.close()
    if a.search or a.all:
        dim = int(os.environ.get("EMBEDDING_DIM", "1536"))
        service = srch.AzureSearch()
        if a.search_mode == "push":
            counts = load_search(service, srch.FoundryEmbedder(), dim)
        else:
            print_counts("AI Search indexer (işlenen)", sync_search(service, dim))
            counts = dict.fromkeys(srch.SEARCH_SOURCES, 0)
        print_counts(f"AI Search · {a.search_mode}", {k: service.count(k) for k in counts})
    if a.sync and not (a.search or a.all):
        print("Indexer'lar tetiklendi:", ", ".join(srch.sync_now(srch.AzureSearch())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
