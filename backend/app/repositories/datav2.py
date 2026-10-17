"""datav2 verisini (JSON ya da Azure SQL'den gelen ham satırlar) sohbet kataloğuna dönüştürür."""

import json
from dataclasses import dataclass, field
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
    # Çözümün ekran akışı (tur) adresi; kullanıcıya "Akışı izle" bağlantısı olarak gösterilir.
    scenario_path: str | None = None


@dataclass(frozen=True)
class Screen:
    code: str
    name: str
    description: str


@dataclass(frozen=True)
class Customer:
    """Bilgilendirme için gereken en az alan: ad, telefon, iletişim izinleri."""

    customer_number: str
    full_name: str
    phone: str
    perm_phone: bool
    perm_sms: bool
    perm_email: bool


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


# Ham tablolar: JSON dosya adı = SQL tablo adı (db/schema.sql).
TABLES = (
    "screens",
    "institutions",
    "institution_screens",
    "solution_templates",
    "incidents",
    "kibana_logs",
    "customers",
)


@dataclass(frozen=True)
class RawData:
    """Kaynaktan (JSON ya da Azure SQL) okunan ham satırlar; alan adları datav2 şemasıyla aynı."""

    screens: tuple[dict, ...]
    institutions: tuple[dict, ...]
    institution_screens: tuple[dict, ...]
    solution_templates: tuple[dict, ...]
    incidents: tuple[dict, ...]
    kibana_logs: tuple[dict, ...]
    customers: tuple[dict, ...] = ()


@dataclass(frozen=True)
class Catalog:
    """Sohbetin kullandığı veri: hata logları, çağrılar, ekranlar, kurumlar."""

    logs: tuple[LogEntry, ...]
    incidents: tuple[Incident, ...]
    screens: tuple[Screen, ...]
    institutions: tuple[Institution, ...]
    # Modele hiç gitmez; yalnızca yetkili kullanıcıya etkilenen müşteri listesi için (kod).
    customers: dict[str, Customer] = field(default_factory=dict)


def read_json(data_dir: Path) -> RawData:
    def read(name: str) -> tuple[dict, ...]:
        return tuple(json.loads((data_dir / f"{name}.json").read_text(encoding="utf-8")))

    return RawData(**{name: read(name) for name in TABLES})


def build_screens(raw: RawData) -> tuple[Screen, ...]:
    screens = (
        Screen(row["code"], row["name"], row.get("description") or "") for row in raw.screens
    )
    return tuple(sorted(screens, key=lambda screen: screen.code))


def build_institutions(raw: RawData) -> tuple[Institution, ...]:
    """Fatura kurumları ve işlem gördükleri ekranlar (institution_screens)."""
    screens_by_code: dict[str, list[str]] = {}
    for link in raw.institution_screens:
        screens_by_code.setdefault(link["institution_code"], []).append(link["screen_code"])
    institutions = (
        Institution(
            code=row["institution_code"],
            name=row["name"],
            bill_type=row.get("bill_type") or "",
            screen_codes=tuple(sorted(set(screens_by_code.get(row["institution_code"], [])))),
        )
        for row in raw.institutions
    )
    return tuple(sorted(institutions, key=lambda institution: institution.code))


def build_error_logs(
    raw: RawData, screens: tuple[Screen, ...], institutions: tuple[Institution, ...]
) -> tuple[LogEntry, ...]:
    """Yalnızca Warning/Error kayıtları, zamana göre sıralı."""
    screen_names = {screen.code: screen.name for screen in screens}
    institution_names = {inst.code: inst.name for inst in institutions}
    entries = [
        _to_entry(row, screen_names, institution_names)
        for row in raw.kibana_logs
        if row.get("log_level") in ERROR_LEVELS
    ]
    return tuple(sorted(entries, key=lambda entry: entry.log_time))


def build_incidents(raw: RawData) -> tuple[Incident, ...]:
    """Çağrılar; hata numarası bağlı logdan, çözüm metni hazır çözüm şablonundan."""
    log_errors = {
        row["correlation_id"]: (
            row.get("app_exception_value"),
            _json_field(row.get("message_response")).get("errorCode"),
        )
        for row in raw.kibana_logs
    }
    templates = {row["solution_template_id"]: row for row in raw.solution_templates}
    incidents = []
    for row in raw.incidents:
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
                scenario_path=row.get("scenario_path") or None,
            )
        )
    return tuple(sorted(incidents, key=lambda incident: incident.created_at))


def build_customers(raw: RawData) -> dict[str, Customer]:
    return {
        row["customer_number"]: Customer(
            customer_number=row["customer_number"],
            full_name=row.get("full_name") or "",
            phone=row.get("phone") or "",
            perm_phone=bool(row.get("perm_phone")),
            perm_sms=bool(row.get("perm_sms")),
            perm_email=bool(row.get("perm_email")),
        )
        for row in raw.customers
    }


def build_catalog(raw: RawData) -> Catalog:
    screens = build_screens(raw)
    institutions = build_institutions(raw)
    return Catalog(
        logs=build_error_logs(raw, screens, institutions),
        incidents=build_incidents(raw),
        screens=screens,
        institutions=institutions,
        customers=build_customers(raw),
    )


@lru_cache
def json_catalog(data_dir: Path) -> Catalog:
    """datav2/*.json dosyalarından katalog (ilk erişimde bir kez okunur)."""
    return build_catalog(read_json(data_dir))


def load_error_logs(data_dir: Path) -> tuple[LogEntry, ...]:
    return json_catalog(data_dir).logs


def load_screens(data_dir: Path) -> tuple[Screen, ...]:
    return json_catalog(data_dir).screens


def load_institutions(data_dir: Path) -> tuple[Institution, ...]:
    return json_catalog(data_dir).institutions


def load_incidents(data_dir: Path) -> tuple[Incident, ...]:
    return json_catalog(data_dir).incidents
