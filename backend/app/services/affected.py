"""Etkilenen müşteri listesi (bilgilendirme araması için). Modele hiç gitmez; yalnızca yetkili
kullanıcıya (L2) kod tarafından gösterilir. Veri en aza indirilir: ad, telefon, iletişim izni,
son hata zamanı ve kurum. Telefon izni olmayanın numarası maskelenir.
"""

from typing import Any

from app.repositories.datav2 import Customer, LogEntry
from app.services.tools import ToolContext, filter_logs

MAX_ROWS = 500


def mask_phone(phone: str) -> str:
    """+90 532 000 85 64 → +90 5•• ••• •• 64 (yalnızca son iki rakam görünür)."""
    digits = [index for index, char in enumerate(phone) if char.isdigit()]
    keep = set(digits[:3] + digits[-2:])  # ülke kodu (90), operatörün ilk rakamı, son iki rakam
    return "".join(
        char if not char.isdigit() or index in keep else "•" for index, char in enumerate(phone)
    )


def _channel(customer: Customer | None) -> str:
    if customer is None:
        return "Kayıt yok"
    if customer.perm_phone:
        return "Telefon"
    if customer.perm_sms:
        return "SMS"
    if customer.perm_email:
        return "E-posta"
    return "İzin yok"


def affected_customers(
    query: dict[str, Any], context: ToolContext, customers: dict[str, Customer]
) -> dict[str, Any]:
    found, normalized = filter_logs(query, context)
    latest: dict[str, LogEntry] = {}
    for entry in found:  # loglar zamana göre sıralı: sonuncu en yenidir
        if entry.customer_id:
            latest[entry.customer_id] = entry
    ordered = sorted(latest.values(), key=lambda entry: entry.log_time, reverse=True)

    rows = []
    for entry in ordered[:MAX_ROWS]:
        customer = customers.get(entry.customer_id or "")
        can_call = bool(customer and customer.perm_phone)
        rows.append(
            {
                "customer_number": entry.customer_id,
                "full_name": customer.full_name if customer else None,
                "phone": (customer.phone if can_call else mask_phone(customer.phone))
                if customer
                else None,
                "can_call": can_call,
                "channel": _channel(customer),
                "last_error_time": entry.log_time.strftime("%Y-%m-%dT%H:%M"),
                "screen_code": entry.screen_code,
                "error_number": entry.error_number,
                "institution_code": entry.institution_code,
            }
        )
    return {
        "query": normalized,
        "total_customers": len(ordered),
        "callable_customers": sum(
            1 for entry in ordered if (c := customers.get(entry.customer_id or "")) and c.perm_phone
        ),
        "truncated": len(ordered) > MAX_ROWS,
        "rows": rows,
    }
