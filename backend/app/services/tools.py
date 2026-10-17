"""Mercek'in kullanabildiği araçlar. Model parametreleri seçer, sorguyu kod çalıştırır."""

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app.config import TURKEY_TZ
from app.repositories.datav2 import Incident, LogEntry, normalize

MAX_RANGE = timedelta(days=7)
MAX_SAMPLES = 20
MAX_GROUPS = 10

KIBANA_SORGULA = {
    "type": "function",
    "function": {
        "name": "kibana_sorgula",
        "description": (
            "Kibana hata loglarını (yalnızca Warning/Error) sorgular. Toplam sayı, hata "
            "türlerine göre sayılar ve en yeni en fazla 20 örnek satır döner."
        ),
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "required": ["start_time", "end_time", "only_mine"],
            "properties": {
                "screen_code": {"type": "string", "description": "Ekran kodu, ör. ODMTTLMT"},
                "institution_code": {"type": "string", "description": "Kurum kodu, ör. GAZ02"},
                "error_number": {"type": "integer", "description": "Hata numarası, ör. 110731"},
                "start_time": {
                    "type": "string",
                    "description": "Başlangıç, YYYY-MM-DDTHH:MM (Türkiye saati)",
                },
                "end_time": {
                    "type": "string",
                    "description": "Bitiş, YYYY-MM-DDTHH:MM (Türkiye saati)",
                },
                "only_mine": {
                    "type": "boolean",
                    "description": "true: yalnızca sohbeti yapan kullanıcının logları",
                },
                "keyword": {
                    "type": "string",
                    "description": (
                        "Log mesajı, ekran adı, hata kodu, kurum adı ve fatura türünde aranacak "
                        "ayırt edici kelime(ler), ör. '13 hane', 'doğalgaz'. "
                        "Tüm kelimeler geçmeli; kullanıcının cümlesinin tamamını yazma."
                    ),
                },
            },
        },
    },
}

CAGRI_ARA = {
    "type": "function",
    "function": {
        "name": "cagri_ara",
        "description": (
            "Aynı ekran ve hata numarasıyla geçmişte açılmış çağrıları döner: kapanan çağrıların "
            "hangi hazır çözümle kapatıldığı (çözüm metniyle), açık çağrı sayısı ve en yeni 5 "
            "örnek çağrı."
        ),
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "required": ["screen_code", "error_number"],
            "properties": {
                "screen_code": {"type": "string", "description": "Ekran kodu, ör. ODMTTLMT"},
                "error_number": {"type": "integer", "description": "Hata numarası, ör. 110731"},
                "institution_code": {
                    "type": "string",
                    "description": "İsteğe bağlı kurum filtresi; önce bunsuz arayın",
                },
            },
        },
    },
}

TOOLS = [KIBANA_SORGULA, CAGRI_ARA]
MAX_INCIDENT_SAMPLES = 5


class ToolInputError(ValueError):
    """Model araca geçersiz parametre verdi."""


@dataclass(frozen=True)
class ToolContext:
    user_name: str
    now: datetime
    logs: tuple[LogEntry, ...]
    incidents: tuple[Incident, ...] = ()
    # Prompt'a giden görev bilgisi (ör. "L2 Destek · 9010 BT Destek (L2)"); kullanıcı kodu değil.
    user_role: str = ""


def _parse_time(value: Any, name: str) -> datetime:
    if not isinstance(value, str):
        raise ToolInputError(f"{name} metin olmalı (YYYY-MM-DDTHH:MM)")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ToolInputError(f"{name} biçimi geçersiz: {value!r}") from exc
    return parsed.replace(tzinfo=TURKEY_TZ) if parsed.tzinfo is None else parsed


def _optional_str(args: dict[str, Any], name: str) -> str | None:
    value = args.get(name)
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ToolInputError(f"{name} metin olmalı")
    return value.strip()


def kibana_sorgula(args: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    start = _parse_time(args.get("start_time"), "start_time")
    end = min(_parse_time(args.get("end_time"), "end_time"), context.now)
    if start >= end:
        raise ToolInputError("start_time, end_time'dan (ve şu andan) önce olmalı")
    start = max(start, end - MAX_RANGE)

    only_mine = args.get("only_mine") is True
    screen_code = _optional_str(args, "screen_code")
    institution_code = _optional_str(args, "institution_code")
    keyword = _optional_str(args, "keyword")
    error_number = args.get("error_number")
    if error_number is not None and not isinstance(error_number, int):
        raise ToolInputError("error_number tam sayı olmalı")

    keyword_words = normalize(keyword).split() if keyword else []

    def matches(entry: LogEntry) -> bool:
        return (
            start <= entry.log_time <= end
            and (not only_mine or entry.user_name == context.user_name)
            and (screen_code is None or entry.screen_code == screen_code.upper())
            and (institution_code is None or entry.institution_code == institution_code.upper())
            and (error_number is None or entry.error_number == error_number)
            and all(word in entry.search_text for word in keyword_words)
        )

    found = [entry for entry in context.logs if matches(entry)]
    groups = Counter(
        (e.screen_code, e.error_number, e.error_code, e.institution_code) for e in found
    )
    return {
        "query": {
            "start_time": start.strftime("%Y-%m-%dT%H:%M"),
            "end_time": end.strftime("%Y-%m-%dT%H:%M"),
            "only_mine": only_mine,
            "screen_code": screen_code,
            "institution_code": institution_code,
            "error_number": error_number,
            "keyword": keyword,
        },
        "total": len(found),
        "distinct_customers": len({e.customer_id for e in found if e.customer_id}),
        "by_error": [
            {
                "screen_code": screen,
                "error_number": number,
                "error_code": code,
                "institution_code": institution,
                "count": count,
            }
            for (screen, number, code, institution), count in groups.most_common(MAX_GROUPS)
        ],
        "samples": [
            {
                "log_time": e.log_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "level": e.log_level,
                "screen_code": e.screen_code,
                "error_number": e.error_number,
                "error_code": e.error_code,
                "institution_code": e.institution_code,
                "message": e.message,
            }
            for e in reversed(found[-MAX_SAMPLES:])
        ],
    }


def cagri_ara(args: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    screen_code = _optional_str(args, "screen_code")
    if screen_code is None:
        raise ToolInputError("screen_code gerekli")
    error_number = args.get("error_number")
    if not isinstance(error_number, int) or isinstance(error_number, bool):
        raise ToolInputError("error_number tam sayı olmalı")
    institution_code = _optional_str(args, "institution_code")

    found = [
        incident
        for incident in context.incidents
        if incident.created_at <= context.now
        and incident.screen_code == screen_code.upper()
        and incident.error_number == error_number
        and (institution_code is None or incident.institution_code == institution_code.upper())
    ]
    closed = [incident for incident in found if incident.status == "kapali"]
    by_solution: dict[str | None, list[Incident]] = {}
    for incident in closed:
        by_solution.setdefault(incident.solution_template_id, []).append(incident)

    return {
        "query": {
            "screen_code": screen_code,
            "error_number": error_number,
            "institution_code": institution_code,
        },
        "total": len(found),
        "closed": len(closed),
        "open": len(found) - len(closed),
        "by_solution": [
            {
                "solution_template_id": template_id,
                "title": group[0].solution_title,
                "count": len(group),
                "institutions": sorted({i.institution_code for i in group if i.institution_code}),
                "closure_code": group[0].closure_code,
                "sub_closure_code": group[0].sub_closure_code,
                "solution_text": group[0].solution_text,
            }
            for template_id, group in sorted(
                by_solution.items(), key=lambda item: len(item[1]), reverse=True
            )
        ],
        "samples": [
            {
                "incident_id": incident.incident_id,
                "created_at": incident.created_at.strftime("%Y-%m-%d"),
                "status": incident.status,
                "institution_code": incident.institution_code,
                "note": incident.note,
                "solution_template_id": incident.solution_template_id,
                "resolution_note": incident.resolution_note,
            }
            for incident in reversed(found[-MAX_INCIDENT_SAMPLES:])
        ],
    }


_HANDLERS = {"kibana_sorgula": kibana_sorgula, "cagri_ara": cagri_ara}


def run_tool(name: str, arguments: str, context: ToolContext) -> dict[str, Any]:
    """Aracı çalıştırır; her durumda modele verilecek bir sözlük döner."""
    handler = _HANDLERS.get(name)
    if handler is None:
        return {"error": f"Bilinmeyen araç: {name}"}
    try:
        args = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return {"error": "Araç parametreleri geçerli JSON değil"}
    if not isinstance(args, dict):
        return {"error": "Araç parametreleri bir nesne olmalı"}
    try:
        return handler(args, context)
    except ToolInputError as exc:
        return {"error": str(exc)}
