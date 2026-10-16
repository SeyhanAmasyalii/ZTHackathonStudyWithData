"""datav2/*.json dosyalarını ilk erişimde bir kez belleğe alır (salt okunur)."""

import json
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path

ERROR_LEVELS = {"Warning", "Error"}


@dataclass(frozen=True)
class LogEntry:
    log_time: datetime
    log_level: str
    user_name: str
    customer_id: str | None
    screen_code: str
    error_number: int | None
    error_code: str | None
    institution_code: str | None
    message: str


@dataclass(frozen=True)
class Screen:
    code: str
    name: str


def _json_field(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _to_entry(row: dict) -> LogEntry:
    fields = _json_field(row.get("message_fields"))
    response = _json_field(row.get("message_response"))
    return LogEntry(
        log_time=datetime.fromisoformat(row["log_time"]),
        log_level=row["log_level"],
        user_name=row.get("user_name") or "",
        customer_id=row.get("customer_id"),
        screen_code=row.get("screen_id") or "",
        error_number=row.get("app_exception_value"),
        error_code=response.get("errorCode"),
        institution_code=fields.get("institutionCode"),
        message=row.get("exception_message") or row.get("message") or "",
    )


@lru_cache
def load_error_logs(data_dir: Path) -> tuple[LogEntry, ...]:
    """kibana_logs.json içinden yalnızca Warning/Error kayıtları, zamana göre sıralı."""
    rows = json.loads((data_dir / "kibana_logs.json").read_text(encoding="utf-8"))
    entries = [_to_entry(row) for row in rows if row.get("log_level") in ERROR_LEVELS]
    return tuple(sorted(entries, key=lambda entry: entry.log_time))


@lru_cache
def load_screens(data_dir: Path) -> tuple[Screen, ...]:
    rows = json.loads((data_dir / "screens.json").read_text(encoding="utf-8"))
    return tuple(sorted((Screen(row["code"], row["name"]) for row in rows), key=lambda s: s.code))
