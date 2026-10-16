"""customers.json üreticisi (datav2 nihai şeması).

Kaynak: onaylı eski veri `data/out/customers.csv` (40.000) + `data/seed/catalog.json` demo_users (5).
Müşteri numaraları korunur; böylece loans ile bağ ve D/E sayıları değişmez.

Şema değişiklikleri:
- age -> birth_date (deterministik; bugünkü yaş eski age ile aynı kalır)
- region_affected kalkar (bölge = city ∈ catalog.affected_region.provinces)
- address_changed_at kalkar; E'nin 10.10.2026 sonrası 37 adres değişikliği
  kibana_logs (MUSTGUNC) üretimi için customers.stats.json'a yazılır
- in_logs kalkar

Çalıştırma (repo kökünden):  python datav2/generators/customers.py
"""

from __future__ import annotations

import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC_CUSTOMERS = ROOT / "data" / "out" / "customers.csv"
SRC_LOANS = ROOT / "data" / "out" / "loans.csv"
SRC_CATALOG = ROOT / "data" / "seed" / "catalog.json"
OUT_DIR = ROOT / "datav2"

TODAY = date(2026, 10, 17)
SEED = 42
E_ADDRESS_CHANGE_FROM = "2026-10-10"

# Demo kullanıcılarında catalog'da olmayan alanlar (sentetik)
DEMO_EXTRA = {
    "10000004": {"segment": "Bireysel", "birth_date": "1994-05-12"},
    "10000005": {"segment": "Bireysel", "birth_date": "1997-11-03"},
    "10000006": {"segment": "Premium", "birth_date": "1988-02-21"},
    "10000007": {"segment": "Premium", "birth_date": "1979-08-30"},
    "10000008": {"segment": "Premium", "birth_date": "1981-01-17"},
}


def age_on(birth: date, today: date) -> int:
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def birth_date_for(customer_number: str, age: int) -> str:
    """Bugün tam olarak `age` yaşında olan, müşteri numarasına göre sabit bir doğum tarihi."""
    rng = random.Random(f"{SEED}:{customer_number}")
    latest = TODAY.replace(year=TODAY.year - age)  # bugün doğum günü
    birth = latest - timedelta(days=rng.randint(0, 364))
    assert age_on(birth, TODAY) == age, (customer_number, age, birth)
    return birth.isoformat()


def to_bit(value: str | bool) -> int:
    return 1 if value in ("1", True) else 0


def convert(row: dict[str, str]) -> dict:
    return {
        "customer_number": row["customer_number"],
        "full_name": row["full_name"],
        "segment": row["segment"],
        "birth_date": birth_date_for(row["customer_number"], int(row["age"])),
        "monthly_income": int(row["monthly_income"]),
        "city": row["city"],
        "district": row["district"],
        "email": row["email"] or None,
        "phone": row["phone"],
        "perm_email": to_bit(row["perm_email"]),
        "perm_sms": to_bit(row["perm_sms"]),
        "perm_phone": to_bit(row["perm_phone"]),
    }


def demo_customer(user: dict) -> dict:
    extra = DEMO_EXTRA[user["customerNo"]]
    perms = user["permissions"]
    return {
        "customer_number": user["customerNo"],
        "full_name": user["name"],
        "segment": extra["segment"],
        "birth_date": extra["birth_date"],
        "monthly_income": user["monthlyIncome"],
        "city": user["address"]["city"],
        "district": user["address"]["district"],
        "email": user["email"],
        "phone": user["phone"],
        "perm_email": to_bit(perms["email"]),
        "perm_sms": to_bit(perms["sms"]),
        "perm_phone": to_bit(perms["phone"]),
    }


def scenario_stats(customers: list[dict], src_rows: list[dict], provinces: set[str]) -> dict:
    by_no = {c["customer_number"]: c for c in customers}
    with SRC_LOANS.open(encoding="utf-8") as f:
        loans = list(csv.DictReader(f))
    borrowers = {ln["customer_number"] for ln in loans}

    region = [by_no[n] for n in borrowers if by_no[n]["city"] in provinces]
    delinquent = {ln["customer_number"] for ln in loans if ln["delinquent_12m"] == "1"}
    no_email = [n for n in delinquent if not by_no[n]["email"] or by_no[n]["perm_email"] != 1]

    address_changes = sorted(
        (
            {"customer_number": r["customer_number"], "changed_at": r["address_changed_at"]}
            for r in src_rows
            if r["address_changed_at"] >= E_ADDRESS_CHANGE_FROM
        ),
        key=lambda x: (x["changed_at"], x["customer_number"]),
    )
    return {
        "total_customers": len(customers),
        "generated_customers": len(src_rows),
        "demo_customers": len(DEMO_EXTRA),
        "D": {
            "delinquent_12m_customers": len(delinquent),
            "delinquent_12m_loans": sum(ln["delinquent_12m"] == "1" for ln in loans),
            "no_email_or_no_email_permission": len(no_email),
            "no_email_pct": round(100 * len(no_email) / len(delinquent), 1),
            "delinquent_today_loans": sum(ln["status"] == "gecikmede" for ln in loans),
        },
        "E": {
            "region_borrowers": len(region),
            "region_sms_permitted": sum(c["perm_sms"] for c in region),
            "region_sms_or_email_permitted": sum(1 for c in region if c["perm_sms"] or c["perm_email"]),
            "address_changes_since_2026_10_10": len(address_changes),
            "address_changes": address_changes,
        },
    }


def main() -> None:
    catalog = json.loads(SRC_CATALOG.read_text(encoding="utf-8"))
    provinces = set(catalog["affected_region"]["provinces"])
    with SRC_CUSTOMERS.open(encoding="utf-8") as f:
        src_rows = list(csv.DictReader(f))

    customers = [demo_customer(u) for u in catalog["demo_users"]]
    customers += [convert(r) for r in src_rows]
    numbers = [c["customer_number"] for c in customers]
    assert len(numbers) == len(set(numbers)), "müşteri numarası tekrarı"

    (OUT_DIR / "customers.json").write_text(
        json.dumps(customers, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    stats = scenario_stats(customers, src_rows, provinces)
    (OUT_DIR / "customers.stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in stats.items() if k != "E"}, ensure_ascii=False))
    print({k: v for k, v in stats["E"].items() if k != "address_changes"})


if __name__ == "__main__":
    main()
