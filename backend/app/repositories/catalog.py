"""Sohbet kataloğunun kaynağını seçer: SQL_SERVER tanımlıysa Azure SQL, değilse datav2 JSON."""

import logging
import threading
from functools import lru_cache

from app.config import get_settings
from app.repositories import sql
from app.repositories.datav2 import Catalog, build_catalog, json_catalog

logger = logging.getLogger(__name__)

# Açılıştaki ön yükleme ile ilk istek aynı anda gelirse veri iki kez okunmasın.
_lock = threading.Lock()


def get_catalog() -> Catalog:
    with _lock:
        return _load()


@lru_cache
def _load() -> Catalog:
    """İlk çağrıda bir kez yüklenir. SQL'e ulaşılamazsa demo durmasın diye JSON'a düşer."""
    settings = get_settings()
    if not settings.sql_server:
        logger.info("Veri kaynağı: JSON (%s)", settings.data_dir)
        return json_catalog(settings.data_dir)
    try:
        with sql.connect(settings) as connection:
            catalog = build_catalog(sql.read_raw(connection))
    except Exception:
        logger.exception("Azure SQL okunamadı; JSON verisine geçildi")
        return json_catalog(settings.data_dir)
    logger.info(
        "Veri kaynağı: Azure SQL (%s) · %d hata logu · %d çağrı",
        settings.sql_database,
        len(catalog.logs),
        len(catalog.incidents),
    )
    return catalog
