"""datav2/*.json dosyalarını ilk erişimde bir kez belleğe alır (salt okunur)."""

import json
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path

ERROR_LEVELS = {"Warning", "Error"}

_TR_ASCII = str.maketrans("ıİğĞüÜşŞöÖçÇ", "iigguussoocc")


def normalize(text: str) -> str:
    """Arama için: küçük harf, Türkçe karakterler sadeleşmiş ("Doğalgaz" → "dogalgaz")."""
    return text.translate(_TR_ASCII).casefold()


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
    search_text: str  # normalize edilmiş: mesaj + ekran + hata kodu + kurum + fatura türü


@dataclass(frozen=True)
class Screen:
    code: str
    name: str
    description: str


@dataclass(frozen=True)
class Institution:
    code: str
    name: str
    bill_type: str
    screen_codes: tuple[str, ...]


def _json_field(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _to_entry(
    row: dict, screen_names: dict[str, str], institution_names: dict[str, str]
) -> LogEntry:
    fields = _json_field(row.get("message_fields"))
    response = _json_field(row.get("message_response"))
    screen_code = row.get("screen_id") or ""
    institution_code = fields.get("institutionCode")
    message = row.get("exception_message") or row.get("message") or ""
    searchable = [
        message,
        screen_code,
        screen_names.get(screen_code, ""),
        response.get("errorCode") or "",
        institution_code or "",
        institution_names.get(institution_code or "", ""),
        fields.get("billType") or "",
    ]
    return LogEntry(
        log_time=datetime.fromisoformat(row["log_time"]),
        log_level=row["log_level"],
        user_name=row.get("user_name") or "",
        customer_id=row.get("customer_id"),
        screen_code=screen_code,
        error_number=row.get("app_exception_value"),
        error_code=response.get("errorCode"),
        institution_code=institution_code,
        message=message,
        search_text=normalize(" ".join(searchable)),
    )


@lru_cache
def load_error_logs(data_dir: Path) -> tuple[LogEntry, ...]:
    """kibana_logs.json içinden yalnızca Warning/Error kayıtları, zamana göre sıralı."""
    rows = json.loads((data_dir / "kibana_logs.json").read_text(encoding="utf-8"))
    screen_names = {screen.code: screen.name for screen in load_screens(data_dir)}
    institution_names = {inst.code: inst.name for inst in load_institutions(data_dir)}
    entries = [
        _to_entry(row, screen_names, institution_names)
        for row in rows
        if row.get("log_level") in ERROR_LEVELS
    ]
    return tuple(sorted(entries, key=lambda entry: entry.log_time))


@lru_cache
def load_screens(data_dir: Path) -> tuple[Screen, ...]:
    rows = json.loads((data_dir / "screens.json").read_text(encoding="utf-8"))
    screens = (Screen(row["code"], row["name"], row.get("description") or "") for row in rows)
    return tuple(sorted(screens, key=lambda screen: screen.code))


@lru_cache
def load_institutions(data_dir: Path) -> tuple[Institution, ...]:
    """Fatura kurumları ve işlem gördükleri ekranlar (institution_screens)."""
    rows = json.loads((data_dir / "institutions.json").read_text(encoding="utf-8"))
    links = json.loads((data_dir / "institution_screens.json").read_text(encoding="utf-8"))
    screens_by_code: dict[str, list[str]] = {}
    for link in links:
        screens_by_code.setdefault(link["institution_code"], []).append(link["screen_code"])
    institutions = (
        Institution(
            code=row["institution_code"],
            name=row["name"],
            bill_type=row.get("bill_type") or "",
            screen_codes=tuple(sorted(set(screens_by_code.get(row["institution_code"], [])))),
        )
        for row in rows
    )
    return tuple(sorted(institutions, key=lambda institution: institution.code))
