"""loans.json üreticisi (datav2 nihai şeması; şema eskisiyle aynı).

Kaynak: onaylı eski veri `data/out/loans.csv` (33.000). Kayıtlar tiplenerek aktarılır.
- collection_account kaldırıldı (senaryolarda kullanılmıyor; IBAN KVKK taramasına takılır).
- Demo kredileri: D/E sayıları değişmesin diye yeni kredi eklenmez; tek kredisi olan, bölge dışı
  sentetik müşterilerden birer kredi demo kullanıcılarına aktarılır. Elif'e kredi verilmez
  (A senaryosu mevcut kredisi olmamasına dayanır).

Çalıştırma (repo kökünden):  python datav2/generators/loans.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC_LOANS = ROOT / "data" / "out" / "loans.csv"
OUT_DIR = ROOT / "datav2"

DROPPED_FIELDS = ("collection_account",)
INT_FIELDS = ("term", "paid_installments", "delinquent_12m")
FLOAT_FIELDS = ("principal", "remaining_principal", "monthly_rate", "installment")


def to_number(value: str) -> int | float:
    number = float(value)
    return int(number) if number.is_integer() else number


def convert(row: dict[str, str]) -> dict:
    loan = dict(row)
    for field in INT_FIELDS:
        loan[field] = int(row[field])
    for field in FLOAT_FIELDS:
        loan[field] = to_number(row[field])
    loan["next_due_date"] = row["next_due_date"] or None
    for field in DROPPED_FIELDS:
        loan.pop(field)
    return loan


def no_email(customer: dict) -> bool:
    return not customer["email"] or customer["perm_email"] != 1


def pick_donor(loans: list[dict], by_no: dict, provinces: set[str], target: dict, delinquent: bool) -> dict:
    """Hedef demo müşterisiyle aynı sayım sınıfında olan tek kredili bir sentetik müşterinin kredisi."""
    per_customer: dict[str, int] = {}
    for ln in loans:
        per_customer[ln["customer_number"]] = per_customer.get(ln["customer_number"], 0) + 1
    for ln in loans:
        donor = by_no[ln["customer_number"]]
        if (
            per_customer[donor["customer_number"]] == 1
            and donor["city"] not in provinces
            and target["city"] not in provinces
            and (ln["status"] == "gecikmede") == delinquent
            and ln["delinquent_12m"] == int(delinquent)
            and (not delinquent or no_email(donor) == no_email(target))
        ):
            return ln
    raise LookupError("uygun kredi bulunamadı")


# demo müşteri -> gecikmede mi (Zeynep: D/KRDTTAHS demosu, Kerem: normal kredi)
DEMO_LOANS = {"10000005": True, "10000006": False}


def main() -> None:
    with SRC_LOANS.open(encoding="utf-8") as f:
        loans = [convert(r) for r in csv.DictReader(f)]

    customers = json.loads((OUT_DIR / "customers.json").read_text(encoding="utf-8"))
    catalog = json.loads((ROOT / "data" / "seed" / "catalog.json").read_text(encoding="utf-8"))
    provinces = set(catalog["affected_region"]["provinces"])
    by_no = {c["customer_number"]: c for c in customers}
    for customer_number, delinquent in DEMO_LOANS.items():
        loan = pick_donor(loans, by_no, provinces, by_no[customer_number], delinquent)
        print("demo kredisi:", loan["loan_id"], loan["customer_number"], "->", customer_number)
        loan["customer_number"] = customer_number
    known = set(by_no)
    orphans = [ln["loan_id"] for ln in loans if ln["customer_number"] not in known]
    assert not orphans, f"müşterisi olmayan kredi: {orphans[:5]}"
    ids = [ln["loan_id"] for ln in loans]
    assert len(ids) == len(set(ids)), "kredi numarası tekrarı"

    (OUT_DIR / "loans.json").write_text(
        json.dumps(loans, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(len(loans), "kredi ·", len({ln["customer_number"] for ln in loans}), "kredili müşteri")


if __name__ == "__main__":
    main()
