#!/usr/bin/env python3
"""Müşteri temasları, teknoloji çağrı kayıtları ve çözüm bilgi bankası (V6).

İki ayrı kayıt türü üretilir:
  contacts  · müşterinin çağrı merkezini araması ya da şubeye gelmesi (temsilci notu). ~7.600 kayıt, 90 gün.
              D ve E'nin köprü sayıları buradan sayılır.
  incidents · teknolojiye açılan destek kaydı (CAG-xxxx). 1.400 kayıt, son 90 gün, CAG-0651 … CAG-2050.
              B'nin geçmiş olayları ve C'nin açık çağrıları buradadır.
  solutions · çözüm bilgi bankası: V4'teki 36 çözüm + elle yazılmış SOL-031.

Kesin senaryo kayıtları (docs/mercek-sentetik-veri-uretimi.md §6–7):
  D · son 90 gün Kredi temasları: hatırlatma 71 · gecikme faizi 64 · taksit tarihi 51 = 186
  E · etkilenen illerden 12.10 sonrası 497 temas (418 erteleme); 12.09–11.10 arası günlük ortalama 16
  B · SOL-031 ile kapanmış 6 kurum zaman aşımı çağrısı
  C · 1 Ekim'den beri 23 açık İSKİ çağrısı (müşteriler V3'teki İSKİ müşterileri)

Girdi: catalog.json, texts.json, fixed_texts.json (data/seed), customers.csv (V5), mercek-logs.ndjson (V3)
Çıktı: data/out/contacts.csv, incidents.csv, solutions.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / "data" / "seed"
OUT = ROOT / "data" / "out"
LOGS = ROOT / "tools" / "output" / "mercek-logs.ndjson"

TR = timezone(timedelta(hours=3))
END = datetime(2026, 10, 17, 9, 0, tzinfo=TR)            # verinin bittiği an
START = datetime(2026, 7, 19, 0, 0, tzinfo=TR)           # son 90 gün
E_SURGE_START = datetime(2026, 10, 12, 0, 0, tzinfo=TR)  # son 5 gün
E_BASE_START = datetime(2026, 9, 12, 0, 0, tzinfo=TR)    # önceki 30 gün
ISKI_START = datetime(2026, 10, 1, 0, 0, tzinfo=TR)

# Kesin değerler
D_SUBCATS = {"hatırlatma almadım / tarihi unuttum": 71, "gecikme faizi itirazı": 64, "taksit tutarı / tarih sorusu": 51}
E_SUBCAT = "erteleme / ödeme güçlüğü"
E_SURGE_TOTAL, E_SURGE_TOPIC = 497, 418
E_BASE_DAILY, E_BASE_DAYS = 16, 30
C_SUBCAT = "abone numarası kabul edilmiyor"
C_INCIDENTS = 23
B_HISTORY = [(82, "Başkentgaz"), (64, "İGDAŞ"), (47, "Enerjisa Başkent"), (33, "Başkentgaz"), (19, "İGDAŞ"),
             (9, "CK Boğaziçi Elektrik")]
INCIDENTS = 1400
FIRST_INCIDENT_NO = 651  # CAG-0651 … CAG-2050 (daha eskileri arşivde)
BILL_TYPES = {"CK Boğaziçi Elektrik": "Elektrik", "Enerjisa Başkent": "Elektrik", "Gediz Elektrik": "Elektrik",
              "İSKİ": "Su", "ASKİ": "Su", "İZSU": "Su", "İGDAŞ": "Doğalgaz", "Başkentgaz": "Doğalgaz",
              "İzmirgaz": "Doğalgaz"}

# Arka plan dağılımları
NON_REGION_DAILY = 69
REGION_DAILY_OTHER = 16  # 12.09 öncesi bölge temasları
CATEGORY_WEIGHTS = {"Fatura ödeme": 24, "Kredi": 22, "Kart": 16, "Hesap": 14, "Müşteri bilgileri": 12, "Diğer": 12}
CONTACT_CHANNELS = [("cagri_merkezi", 75), ("sube", 25)]
INCIDENT_CHANNELS = [("sube", 45), ("cagri_merkezi", 40), ("dijital", 15)]
# Teknoloji çağrısı arka planı: (ekran, hata kodu, ağırlık). İş kuralı retleri için de geçmişte çağrı açılmıştır
# (Mercek'in önlediği durum budur).
INCIDENT_MIX = [
    ("ODMTFATR", "INSTITUTION_TIMEOUT", 6), ("ODMTFATR", "INSUFFICIENT_BALANCE", 6), ("ODMTFATR", "VALIDATION_ERROR", 4),
    ("KRDTKULL", "AFFORDABILITY_EXCEEDED", 12), ("KRDTKULL", "VALIDATION_ERROR", 3),
    ("KRTTBASV", "INSUFFICIENT_INCOME", 9), ("KRTTBASV", "VALIDATION_ERROR", 3),
    ("MUSTGUNC", "VALIDATION_ERROR", 5), ("MUSTGUNC", "KYC_CHECK_FAILED", 3),
    ("HSPTVDSZ", "KYC_CHECK_FAILED", 4), ("HSPTVDSZ", "VALIDATION_ERROR", 3), ("HSPTHVLE", "INSUFFICIENT_BALANCE", 4),
    ("*", "CORE_BANKING_TIMEOUT", 10), ("*", "SERVICE_UNAVAILABLE", 7), ("*", "DB_CONNECTION_ERROR", 4),
]
TECH_SCREENS = ["ODMTFATR", "KRDTKULL", "KRTTBASV", "MUSTGUNC", "HSPTVDSZ"]
SCREEN_CATEGORY = {"ODM": "Fatura ödeme", "KRD": "Kredi", "KRT": "Kart", "HSP": "Hesap", "MUS": "Müşteri bilgileri"}
SUBCAT_FOR = {
    ("Fatura ödeme", "INSTITUTION_TIMEOUT"): "kurumdan yanıt alınamadı",
    ("Fatura ödeme", "INSUFFICIENT_BALANCE"): "yetersiz bakiye",
    ("Fatura ödeme", "VALIDATION_ERROR"): "fatura bulunamadı",
    ("Kredi", "AFFORDABILITY_EXCEEDED"): "kullandırım yapılamadı",
    ("Kredi", "VALIDATION_ERROR"): "kullandırım yapılamadı",
    ("Kart", "INSUFFICIENT_INCOME"): "başvuru reddedildi",
    ("Kart", "VALIDATION_ERROR"): "başvuru tamamlanamadı",
    ("Müşteri bilgileri", "VALIDATION_ERROR"): ["telefon numarası hatalı", "adres güncellenemiyor",
                                                "iletişim izni değiştirilemiyor"],
    ("Müşteri bilgileri", "KYC_CHECK_FAILED"): "kimlik doğrulama başarısız",
    ("Hesap", "KYC_CHECK_FAILED"): "hesap açılamadı",
    ("Hesap", "VALIDATION_ERROR"): "hesap açılamadı",
    ("Hesap", "INSUFFICIENT_BALANCE"): "havale/EFT gerçekleşmedi",
}
TECH_SUBCAT = {"Fatura ödeme": "kurumdan yanıt alınamadı", "Kredi": "kullandırım yapılamadı", "Kart": "başvuru tamamlanamadı",
               "Hesap": "hesap açılamadı", "Müşteri bilgileri": "adres güncellenemiyor"}

# Yalnızca teknoloji çağrılarında kullanılan alt kategoriler (müşteri temaslarının dağılımı değişmesin)
INCIDENT_ONLY_SUBCATS = {"yetersiz bakiye", "başvuru tamamlanamadı"}

CONTACT_FIELDS = ["contact_id", "created_at", "channel", "customer_number", "city", "region_affected", "category",
                  "subcategory", "note", "incident_id"]
INCIDENT_FIELDS = ["incident_id", "created_at", "channel", "screen_code", "category", "subcategory", "note",
                   "customer_number", "subscriber_no", "trace_id", "city", "service_id", "error_code", "institution",
                   "master_incident_id", "status", "solution_id", "resolution_minutes"]
SOLUTION_FIELDS = ["solution_id", "title", "symptom", "root_cause", "steps", "error_code", "service_id"]


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------
def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_customers(path: Path) -> List[Dict]:
    if not path.exists():
        raise SystemExit(f"{path} yok. Önce V5'i çalıştırın (generate_portfolio.py).")
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def iski_customers(path: Path) -> List[Tuple[str, str, str]]:
    """V3 loglarındaki 13 haneli İSKİ denemeleri: (müşteri no, abone no, trace.id), müşteri başına ilk deneme."""
    if not path.exists():
        raise SystemExit(f"{path} yok. Önce V3'ü çalıştırın.")
    seen: Dict[str, Tuple[str, str, str]] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            bill = r.get("banking", {}).get("bill", {})
            if bill.get("institution") == "İSKİ" and r.get("error", {}).get("field") == "subscriber_no":
                no = r["customer"]["number"]
                seen.setdefault(no, (no, bill["subscriber_no"], r["trace"]["id"]))
    return [seen[k] for k in sorted(seen)]


def random_ts(rng: random.Random, start: datetime, end: datetime) -> datetime:
    """Gündüz ağırlıklı (08–22) rastgele zaman."""
    while True:
        ts = start + timedelta(seconds=rng.uniform(0, (end - start).total_seconds()))
        if 8 <= ts.hour < 22 or rng.random() < 0.08:
            return ts


def iso(ts: datetime) -> str:
    return ts.astimezone(TR).strftime("%Y-%m-%dT%H:%M:%S+03:00")


def pick_note(rng: random.Random, notes: Dict[str, List[str]], category: str, subcategory: str) -> str:
    pool = notes.get(f"{category}|{subcategory}") or ["Müşteri konu hakkında bilgi istedi."]
    return rng.choice(pool)


def weighted(rng: random.Random, items):
    return rng.choices([x for x, _ in items], weights=[w for _, w in items])[0]


# ---------------------------------------------------------------------------
# Temaslar
# ---------------------------------------------------------------------------
def background_subcategory(rng: random.Random, catalog: Dict, category: str, region: bool) -> str:
    subs = next(c["subcategories"] for c in catalog["incident_categories"] if c["category"] == category)
    banned = set(D_SUBCATS) | {C_SUBCAT}
    if region:
        banned.add(E_SUBCAT)  # bölgede erteleme yalnızca senaryodan gelir
    allowed = [s for s in subs if s not in banned and s not in INCIDENT_ONLY_SUBCATS]
    return rng.choice(allowed)


def contact_row(rng, ts, customer, category, subcategory, notes) -> Dict:
    return {"created_at": ts, "channel": weighted(rng, CONTACT_CHANNELS), "customer_number": customer["customer_number"],
            "city": customer["city"], "region_affected": customer["region_affected"], "category": category,
            "subcategory": subcategory, "note": pick_note(rng, notes, category, subcategory), "incident_id": ""}


def build_contacts(rng: random.Random, catalog: Dict, customers: List[Dict], notes: Dict, holders: set) -> List[Dict]:
    region = [c for c in customers if c["region_affected"] == "1"]
    region_loan = [c for c in region if c["customer_number"] in holders]  # erteleme arayanlar kredili müşteriler
    non_region = [c for c in customers if c["region_affected"] != "1"]
    cats = list(CATEGORY_WEIGHTS.items())
    rows: List[Dict] = []

    # Arka plan · bölge dışı (90 gün)
    days = (END - START).days + 1
    for _ in range(NON_REGION_DAILY * days):
        cat = weighted(rng, cats)
        rows.append(contact_row(rng, random_ts(rng, START, END), rng.choice(non_region), cat,
                                background_subcategory(rng, catalog, cat, False), notes))
    # Arka plan · bölge, 12.09 öncesi
    for _ in range(REGION_DAILY_OTHER * (E_BASE_START - START).days):
        cat = weighted(rng, cats)
        rows.append(contact_row(rng, random_ts(rng, START, E_BASE_START), rng.choice(region), cat,
                                background_subcategory(rng, catalog, cat, True), notes))
    # E · normal seviye: 12.09–11.10 arası tam 480 (günde 16)
    for _ in range(E_BASE_DAILY * E_BASE_DAYS):
        cat = weighted(rng, cats)
        rows.append(contact_row(rng, random_ts(rng, E_BASE_START, E_SURGE_START), rng.choice(region), cat,
                                background_subcategory(rng, catalog, cat, True), notes))
    # E · artış: 12.10 sonrası tam 497, 418'i erteleme
    for i in range(E_SURGE_TOTAL):
        if i < E_SURGE_TOPIC:
            cat, sub = "Kredi", E_SUBCAT
        else:
            cat = weighted(rng, cats)
            sub = background_subcategory(rng, catalog, cat, True)
        rows.append(contact_row(rng, random_ts(rng, E_SURGE_START, END), rng.choice(region_loan), cat, sub, notes))
    # D · son 90 gün, kesin sayılar (bölge dışı müşterilerden; bölge sayılarını bozmasın)
    for sub, n in D_SUBCATS.items():
        for _ in range(n):
            rows.append(contact_row(rng, random_ts(rng, START, END), rng.choice(non_region), "Kredi", sub, notes))

    rows.sort(key=lambda r: r["created_at"])
    for i, r in enumerate(rows, 1):
        r["contact_id"] = f"TMS-{i:06d}"
        r["created_at"] = iso(r["created_at"])
    return rows


# ---------------------------------------------------------------------------
# Çözümler
# ---------------------------------------------------------------------------
def build_solutions(catalog: Dict, texts: Dict, fixed: Dict) -> List[Dict]:
    service_of = {}
    for r in catalog["error_rules"]:
        service_of.setdefault(r["error_code"], r["service_id"] or "")
    rows: List[Dict] = []
    n = 0
    for code, items in texts["solutions"].items():
        for item in items:
            n += 1
            if n == 31:
                n += 1  # SOL-031 elle yazılmış kayda ayrılmıştır
            rows.append({"solution_id": f"SOL-{n:03d}", "title": item["title"], "symptom": item["symptom"],
                         "root_cause": item["root_cause"], "steps": json.dumps(item["steps"], ensure_ascii=False),
                         "error_code": code, "service_id": service_of.get(code, "")})
    for s in fixed["solutions"]:
        rows.append({"solution_id": s["solution_id"], "title": s["title"], "symptom": s["symptom"],
                     "root_cause": s["root_cause"], "steps": json.dumps(s["steps"], ensure_ascii=False),
                     "error_code": s["error_code"], "service_id": s["service_id"]})
    rows.sort(key=lambda r: r["solution_id"])
    return rows


# ---------------------------------------------------------------------------
# Teknoloji çağrı kayıtları
# ---------------------------------------------------------------------------
def rule_service(catalog: Dict, screen: str, error: str) -> str:
    for r in catalog["error_rules"]:
        if r["screen_code"] in (screen, "*") and r["error_code"] == error and r["service_id"]:
            if r["screen_code"] == screen or not any(x["screen_code"] == screen and x["error_code"] == error
                                                     for x in catalog["error_rules"]):
                return r["service_id"]
    main = next(s["service_id"] for s in catalog["screen_services"] if s["screen_code"] == screen and s["role"] == "ana")
    return main


def build_incidents(rng: random.Random, catalog: Dict, customers: List[Dict], notes: Dict, solutions: List[Dict],
                    iski: List[Tuple[str, str, str]]) -> List[Dict]:
    by_no = {c["customer_number"]: c for c in customers}
    sol_by_code: Dict[str, List[str]] = {}
    for s in solutions:
        if s["solution_id"] != "SOL-031":
            sol_by_code.setdefault(s["error_code"], []).append(s["solution_id"])
    institutions = [x["institution"] for x in catalog["institutions"]]
    rows: List[Dict] = []

    def base(ts, screen, error, customer, institution="", subscriber="", subcat=None, status=None, solution=None):
        category = SCREEN_CATEGORY[screen[:3]]
        error_type = "technical" if error in ("CORE_BANKING_TIMEOUT", "SERVICE_UNAVAILABLE", "DB_CONNECTION_ERROR") else "business"
        sub = subcat or (TECH_SUBCAT[category] if error_type == "technical" else SUBCAT_FOR.get((category, error),
                                                                                                TECH_SUBCAT[category]))
        if isinstance(sub, list):
            sub = rng.choice(sub)
        if status is None:
            status = "acik" if (END - ts).days < 3 and rng.random() < 0.4 else "kapali"
        if solution is None and status == "kapali" and rng.random() < 0.6:
            pool = sol_by_code.get(error, [])
            solution = rng.choice(pool) if pool else ""
        return {"created_at": ts, "channel": weighted(rng, INCIDENT_CHANNELS), "screen_code": screen,
                "category": category, "subcategory": sub, "note": pick_note(rng, notes, category, sub),
                "customer_number": customer["customer_number"], "subscriber_no": subscriber,
                "trace_id": f"{rng.getrandbits(128):032x}", "city": customer["city"],
                "service_id": rule_service(catalog, screen, error), "error_code": error, "institution": institution,
                "master_incident_id": "", "status": status, "solution_id": solution or "",
                "resolution_minutes": rng.randint(20, 600) if status == "kapali" else ""}

    # B · geçmiş 6 olay (SOL-031)
    for days_ago, inst in B_HISTORY:
        ts = (END - timedelta(days=days_ago)).replace(hour=rng.randint(9, 18), minute=rng.randint(0, 59))
        row = base(ts, "ODMTFATR", "INSTITUTION_TIMEOUT", rng.choice(customers), institution=inst,
                   subscriber=str(rng.randint(10**9, 10**10 - 1)), subcat="kurumdan yanıt alınamadı",
                   status="kapali", solution="SOL-031")
        row["resolution_minutes"] = rng.randint(45, 120)
        rows.append(row)
    # C · 23 açık İSKİ çağrısı (V3 log müşterileri)
    for no, subscriber, trace in rng.sample(iski, C_INCIDENTS):
        row = base(random_ts(rng, ISKI_START, END), "ODMTFATR", "VALIDATION_ERROR", by_no[no], institution="İSKİ",
                   subscriber=subscriber, subcat=C_SUBCAT, status="acik", solution="")
        row["trace_id"] = trace
        rows.append(row)
    # Arka plan
    mix = [((s, e), w) for s, e, w in INCIDENT_MIX]
    while len(rows) < INCIDENTS:
        screen, error = weighted(rng, mix)
        if screen == "*":
            screen = rng.choice(TECH_SCREENS)
        if screen == "HSPTHVLE":
            screen = "HSPTVDSZ" if rng.random() < 0.3 else screen
        ts = random_ts(rng, START, END)
        inst, sub = "", ""
        if screen == "ODMTFATR":
            inst = rng.choice([i for i in institutions if i != "İSKİ"] if error == "VALIDATION_ERROR" else institutions)
            sub = str(rng.randint(10**9, 10**11 - 1))
            if error == "INSTITUTION_TIMEOUT" and inst == "Başkentgaz" and (END - ts) < timedelta(hours=2):
                continue  # B'nin demo penceresine yakın Başkentgaz kaydı olmasın
        status = "kapali" if inst == "Başkentgaz" else None  # açık Başkentgaz kaydı yalnızca demoda (CAG-2051)
        rows.append(base(ts, screen, error, rng.choice(customers), institution=inst, subscriber=sub, status=status))

    rows.sort(key=lambda r: r["created_at"])
    for i, r in enumerate(rows):
        r["incident_id"] = f"CAG-{FIRST_INCIDENT_NO + i:04d}"
        r["created_at"] = iso(r["created_at"])
    return rows


# ---------------------------------------------------------------------------
# Özet, kontrol, yazma
# ---------------------------------------------------------------------------
def summarize(contacts: List[Dict], incidents: List[Dict], solutions: List[Dict]) -> Dict:
    def after(r, ts):
        return r["created_at"] >= iso(ts)

    def before(r, ts):
        return r["created_at"] < iso(ts)

    d = {s: sum(1 for r in contacts if r["category"] == "Kredi" and r["subcategory"] == s) for s in D_SUBCATS}
    region = [r for r in contacts if r["region_affected"] == "1"]
    surge = [r for r in region if after(r, E_SURGE_START)]
    base = [r for r in region if after(r, E_BASE_START) and before(r, E_SURGE_START)]
    return {
        "contacts": len(contacts),
        "d_counts": d, "d_total": sum(d.values()),
        "e_surge": len(surge), "e_surge_topic": sum(1 for r in surge if r["subcategory"] == E_SUBCAT),
        "e_base_daily": round(len(base) / E_BASE_DAYS, 2),
        "incidents": len(incidents), "first_incident": incidents[0]["incident_id"], "last_incident": incidents[-1]["incident_id"],
        "b_history": sum(1 for r in incidents if r["solution_id"] == "SOL-031" and r["status"] == "kapali"),
        "c_open": sum(1 for r in incidents if r["subcategory"] == C_SUBCAT and r["institution"] == "İSKİ"
                      and r["status"] == "acik" and after(r, ISKI_START)),
        "c_total_subcat": sum(1 for r in incidents if r["subcategory"] == C_SUBCAT),
        "solutions": len(solutions),
    }


EXPECTED = {"d_total": 186, "e_surge": E_SURGE_TOTAL, "e_surge_topic": E_SURGE_TOPIC, "e_base_daily": float(E_BASE_DAILY),
            "incidents": INCIDENTS, "first_incident": "CAG-0651", "last_incident": "CAG-2050", "b_history": 6,
            "c_open": C_INCIDENTS, "c_total_subcat": C_INCIDENTS, "solutions": 37}


def write_csv(path: Path, rows: List[Dict], fields: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def build(seed: int = 42, customers_path: Path = OUT / "customers.csv", logs_path: Path = LOGS) -> Dict:
    rng = random.Random(seed)
    catalog = load_json(SEED / "catalog.json")
    texts = load_json(SEED / "texts.json")
    fixed = load_json(SEED / "fixed_texts.json")
    notes = {**texts["incident_notes"]}
    for k, v in fixed.get("incident_notes", {}).items():
        notes[k] = list(dict.fromkeys(v + notes.get(k, [])))
    customers = load_customers(customers_path)
    holders = {r["customer_number"] for r in load_customers(customers_path.with_name("loans.csv"))}
    contacts = build_contacts(rng, catalog, customers, notes, holders)
    solutions = build_solutions(catalog, texts, fixed)
    incidents = build_incidents(rng, catalog, customers, notes, solutions, iski_customers(logs_path))
    return {"contacts": contacts, "incidents": incidents, "solutions": solutions}


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Temaslar, çağrı kayıtları ve çözümler (V6)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out-dir", default=str(OUT))
    args = p.parse_args(argv)
    out = Path(args.out_dir)
    result = build(args.seed, out / "customers.csv")
    s = summarize(result["contacts"], result["incidents"], result["solutions"])
    wrong = {k: (s[k], v) for k, v in EXPECTED.items() if s[k] != v}
    if wrong or s["d_counts"] != D_SUBCATS:
        raise SystemExit(f"Senaryo değerleri tutmuyor (bulunan, beklenen): {wrong} {s['d_counts']}")
    write_csv(out / "contacts.csv", result["contacts"], CONTACT_FIELDS)
    write_csv(out / "incidents.csv", result["incidents"], INCIDENT_FIELDS)
    write_csv(out / "solutions.csv", result["solutions"], SOLUTION_FIELDS)
    print(f"Temas {s['contacts']} · çağrı {s['incidents']} ({s['first_incident']}…{s['last_incident']}) · çözüm {s['solutions']} → {out}")
    print(f"D · {s['d_counts']} = {s['d_total']}")
    print(f"E · son 5 gün {s['e_surge']} (erteleme {s['e_surge_topic']}) · önceki 30 gün günlük ort. {s['e_base_daily']}")
    print(f"B · SOL-031 ile kapanan {s['b_history']} · C · açık İSKİ çağrısı {s['c_open']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
