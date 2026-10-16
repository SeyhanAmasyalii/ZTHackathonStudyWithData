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
class Incident:
    incident_id: str
    created_at: datetime
    status: str  # acik / kapali
    screen_code: str
    error_number: int | None  # bağlı logdan
    error_code: str | None
    institution_code: str | None
    note: str
    resolution_note: str
    closure_code: str | None
    sub_closure_code: str | None
    solution_template_id: str | None
    solution_title: str
    solution_text: str


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


def _read(data_dir: Path, name: str) -> list[dict]:
    return json.loads((data_dir / name).read_text(encoding="utf-8"))


@lru_cache
def _kibana_rows(data_dir: Path) -> tuple[dict, ...]:
    return tuple(_read(data_dir, "kibana_logs.json"))


@lru_cache
def load_error_logs(data_dir: Path) -> tuple[LogEntry, ...]:
    """kibana_logs.json içinden yalnızca Warning/Error kayıtları, zamana göre sıralı."""
    rows = _kibana_rows(data_dir)
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


@lru_cache
def load_incidents(data_dir: Path) -> tuple[Incident, ...]:
    """Çağrılar; hata numarası bağlı logdan, çözüm metni hazır çözüm şablonundan."""
    log_errors = {
        row["correlation_id"]: (
            row.get("app_exception_value"),
            _json_field(row.get("message_response")).get("errorCode"),
        )
        for row in _kibana_rows(data_dir)
    }
    templates = {
        row["solution_template_id"]: row for row in _read(data_dir, "solution_templates.json")
    }
    incidents = []
    for row in _read(data_dir, "incidents.json"):
        error_number, error_code = log_errors.get(row.get("kibana_correlation_id"), (None, None))
        template = templates.get(row.get("solution_template_id") or "", {})
        incidents.append(
            Incident(
                incident_id=row["incident_id"],
                created_at=datetime.fromisoformat(row["created_at"]),
                status=row["status"],
                screen_code=row.get("screen_code") or "",
                error_number=error_number,
                error_code=error_code or row.get("mercek_assigned_error_code"),
                institution_code=row.get("institution_code"),
                note=row.get("note") or "",
                resolution_note=row.get("resolution_note") or "",
                closure_code=row.get("closure_code"),
                sub_closure_code=row.get("sub_closure_code"),
                solution_template_id=row.get("solution_template_id"),
                solution_title=template.get("mercek_assigned_title") or "",
                solution_text=template.get("solution_text") or "",
            )
        )
    return tuple(sorted(incidents, key=lambda incident: incident.created_at))
