#!/usr/bin/env python3
"""Senaryo doğrulama (V8). docs/mercek-sentetik-veri-uretimi.md §12 tablosundaki her satırı kontrol eder.

Kullanım:
  python3 tools/mercek_data/validate_scenarios.py --sqlite [--now ...]          # SQL kontrolleri (Search satırları atlanır)
  python3 tools/mercek_data/validate_scenarios.py --sql --search                # Azure SQL + AI Search
  python3 tools/mercek_data/validate_scenarios.py --sql --search --only B,C
  python3 tools/mercek_data/validate_scenarios.py --search --eval               # değerlendirme seti (§8.1)

--now demo_reset'te verilen anla aynı olmalı (B'nin "son 30 dk" penceresi buna göre hesaplanır).
Çıkış kodu: tüm kontroller geçerse 0, en az biri ✗ ise 1. Atlanan (–) satırlar hatayı etkilemez.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import db  # noqa: E402
import demo_reset  # noqa: E402
import generate_banking_logs as gen  # noqa: E402
import search as srch  # noqa: E402

TR = timezone(timedelta(hours=3))
SEED = db.ROOT / "data" / "seed"
DATA_START_90 = datetime(2026, 7, 19, tzinfo=TR)
ISKI_START = datetime(2026, 10, 1, tzinfo=TR)
E_SURGE_START = datetime(2026, 10, 12, tzinfo=TR)
E_BASE_START = datetime(2026, 9, 12, tzinfo=TR)
DISASTER = "2026-10-10"
TODAY = date(2026, 10, 17)
B_QUERY = "Başkentgaz fatura ödeme kurumdan yanıt alınamadı"
C_QUERY = "İSKİ abone numarası 13 hane kabul edilmiyor"
D_TOP5 = {"TLP-0871", "TLP-0915", "TLP-0962", "TLP-1004", "TLP-1019"}
E_TOP3 = {"TLP-0588", "TLP-0712", "TLP-0846"}


class Ctx:
    def __init__(self, database: Optional[db.Database], now: datetime, search=None, embedder=None,
                 threshold: float = 0.75):
        self.db, self.now, self.search, self.embedder, self.threshold = database, now, search, embedder, threshold
        self.catalog = json.loads((SEED / "catalog.json").read_text(encoding="utf-8"))

    def q(self, sql: str, *params) -> int:
        return self.db.scalar(sql, [db.utc_iso(p) if isinstance(p, datetime) else p for p in params])

    def find(self, index: str, text: str, top: int = 5, filter: Optional[str] = None) -> List[Dict]:
        return srch.query(self.search, self.embedder, index, text, top, filter)


class Skip(Exception):
    pass


def need_db(ctx: Ctx) -> None:
    if ctx.db is None:
        raise Skip("veritabanı yok")


def need_search(ctx: Ctx) -> None:
    if ctx.search is None:
        raise Skip("--search verilmedi")


def fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if isinstance(v, int) and not isinstance(v, bool):
        return f"{v:,}".replace(",", ".")
    if isinstance(v, (list, tuple)):
        return " / ".join(fmt(x) for x in v)
    return str(v)


# ---------------------------------------------------------------------------
# Takvim kuralı (§3.5): backend'deki takvim servisinin başvuru uygulaması
# ---------------------------------------------------------------------------
def duration(main_share: int) -> int:
    return math.ceil(main_share * 6 / 5)  # ⌈pay × 1,2⌉, kayan nokta hatası olmadan


def is_workday(d: date) -> bool:
    return d.weekday() < 5


def busy(calendar: List[Dict], service_id: str, d: date) -> bool:
    return sum(c["allocation_pct"] for c in calendar if c["service_id"] == service_id
               and c["date_from"] <= d.isoformat() <= c["date_to"]) >= 100


def plan(calendar: List[Dict], service_id: str, main_share: int, today: date = TODAY,
         priority: bool = False) -> Tuple[date, date]:
    """priority: takvime bakmadan ilk iş günü başlar (öncelik kararı). Aksi halde ana servisin ilk boş iş günü."""
    d = today + timedelta(days=1)
    while not is_workday(d) or (not priority and busy(calendar, service_id, d)):
        d += timedelta(days=1)
    start, left = d, duration(main_share)
    while True:
        if is_workday(d):
            left -= 1
            if left == 0:
                return start, d
        d += timedelta(days=1)


def dm(pair: Tuple[date, date]) -> str:
    return f"{pair[0]:%d.%m} → {pair[1]:%d.%m}"


# ---------------------------------------------------------------------------
# Kontroller: (senaryo, açıklama, beklenen, fonksiyon, uyum) · uyum: "eq" ya da (alt, üst) aralığı
# ---------------------------------------------------------------------------
def c_counts(ctx):
    need_db(ctx)
    return [ctx.q("SELECT COUNT(*) FROM banking_logs WHERE source = 'seed'"), ctx.q("SELECT COUNT(*) FROM customers"),
            ctx.q("SELECT COUNT(*) FROM loans"), ctx.q("SELECT COUNT(*) FROM contacts"),
            ctx.q("SELECT COUNT(*) FROM incidents WHERE incident_id BETWEEN 'CAG-0651' AND 'CAG-2050'"),
            ctx.q("SELECT COUNT(*) FROM solutions"), ctx.q("SELECT COUNT(*) FROM requests WHERE request_id <= 'TLP-1037'"),
            ctx.q("SELECT COUNT(*) FROM announcements")]


def counts_ok(found, ctx=None) -> bool:
    logs, cust, loans, contacts, inc, sol, req, ann = found
    return (10_000 <= logs <= 10_800 and cust == 40_000 and loans == 33_000 and 8_000 <= contacts <= 8_600
            and inc == 1_400 and sol == 37 and req == 95 and ann == 20)


def c_integrity(ctx):
    need_db(ctx)
    return [ctx.q("SELECT COUNT(*) FROM loans WHERE customer_number NOT IN (SELECT customer_number FROM customers)"),
            ctx.q("SELECT COUNT(*) FROM incidents WHERE master_incident_id IS NOT NULL "
                  "AND master_incident_id NOT IN (SELECT incident_id FROM incidents)"),
            ctx.q("SELECT COUNT(*) FROM contacts WHERE incident_id IS NOT NULL "
                  "AND incident_id NOT IN (SELECT incident_id FROM incidents)"),
            ctx.q("SELECT COUNT(*) FROM incidents WHERE solution_id IS NOT NULL "
                  "AND solution_id NOT IN (SELECT solution_id FROM solutions)")]


def c_sync(ctx):
    need_db(ctx)
    need_search(ctx)
    return [[ctx.q(f"SELECT COUNT(*) FROM {t}") for t in srch.SEARCH_SOURCES],
            [ctx.search.count(t) for t in srch.SEARCH_SOURCES]]


def c_elif(ctx):
    return next(u["monthlyIncome"] for u in ctx.catalog["demo_users"] if u["username"] == "elif")


def c_loan(ctx):
    r3, r36 = gen.monthly_rate(3), gen.monthly_rate(36)
    e = r36 * 1.30
    max_amount = 38_000 * 0.5 * (1 - (1 + e) ** -36) / e
    return [round(gen.installment(400_000, r3, 3), 2), round(gen.installment(400_000, r36, 36), 2),
            math.floor(max_amount)]


def loan_ok(found, ctx=None) -> bool:
    return found[0] == 144_185.92 and found[1] == 22_754.17 and abs(found[2] - 334_004) <= 5


def c_b_window(ctx):
    need_db(ctx)
    return ctx.q("SELECT COUNT(*) FROM banking_logs WHERE institution = 'Başkentgaz' AND error_code = 'INSTITUTION_TIMEOUT' "
                 "AND ts >= ? AND ts < ?", ctx.now - timedelta(minutes=30), ctx.now)


def c_b_linked(ctx):
    need_db(ctx)
    return ctx.q("SELECT COUNT(*) FROM incidents WHERE master_incident_id = 'CAG-2051'")


def c_b_search(ctx):
    need_search(ctx)
    top = ctx.find("solutions", B_QUERY, 3)[0]
    return [top["id"], round(top["score"], 2)]


def c_c_counts(ctx):
    need_db(ctx)
    base = ("FROM banking_logs WHERE screen_code = 'ODMTFATR' AND error_field = 'subscriber_no' AND ts >= ?")
    return [ctx.q(f"SELECT COUNT(*) {base}", ISKI_START),
            ctx.q(f"SELECT COUNT(*) {base} AND institution = 'İSKİ'", ISKI_START),
            ctx.q(f"SELECT COUNT(*) {base} AND institution = 'İSKİ' AND subscriber_no_len = 13", ISKI_START),
            ctx.q(f"SELECT COUNT(DISTINCT customer_number) {base} AND institution = 'İSKİ'", ISKI_START)]


def c_c_before(ctx):
    need_db(ctx)
    return ctx.q("SELECT COUNT(*) FROM banking_logs WHERE institution = 'İSKİ' AND subscriber_no_len = 13 AND ts < ?",
                 ISKI_START)


def c_c_incidents(ctx):
    need_db(ctx)
    return ctx.q("SELECT COUNT(*) FROM incidents WHERE institution = 'İSKİ' AND subcategory = 'abone numarası kabul edilmiyor' "
                 "AND status = 'acik' AND created_at >= ?", ISKI_START)


def c_c_search(ctx):
    need_search(ctx)
    return round(ctx.find("solutions", C_QUERY, 3)[0]["score"], 2)


def c_c_ann(ctx):
    need_search(ctx)
    ids = [r["id"] for r in ctx.find("announcements", C_QUERY, 5)]
    return [ids[0], "DUY-0419 var" if "DUY-0419" in ids else "DUY-0419 yok"]


def c_d_contacts(ctx):
    need_db(ctx)
    return [ctx.q("SELECT COUNT(*) FROM contacts WHERE category = 'Kredi' AND subcategory = ? AND created_at >= ?", s,
                  DATA_START_90)
            for s in ("hatırlatma almadım / tarihi unuttum", "gecikme faizi itirazı", "taksit tutarı / tarih sorusu")]


def c_d_target(ctx):
    need_db(ctx)
    base = "FROM customers WHERE customer_number IN (SELECT customer_number FROM loans WHERE delinquent_12m = 1)"
    return [ctx.q(f"SELECT COUNT(*) {base}"), ctx.q(f"SELECT COUNT(*) {base} AND perm_email = 1"),
            ctx.q(f"SELECT COUNT(*) {base} AND perm_sms = 1"),
            ctx.q(f"SELECT COUNT(*) {base} AND (perm_email = 1 OR perm_sms = 1)")]


def c_d_search(ctx):
    need_search(ctx)
    return sorted(r["id"] for r in ctx.find("requests", demo_reset.D_TEXT, 5, srch.COMPLETED_REQUESTS))


def c_d_plan(ctx):
    cal = ctx.catalog["service_calendar"]
    return [dm(plan(cal, "KREDI_TAKIP", 15)), dm(plan(cal, "KREDI_TAKIP", 16))]


def c_e_region(ctx):
    need_db(ctx)
    loans = "FROM loans l JOIN customers c ON c.customer_number = l.customer_number WHERE c.region_affected = 1"
    return [ctx.q(f"SELECT COUNT(DISTINCT l.customer_number) {loans}"), ctx.q(f"SELECT COUNT(*) {loans}"),
            ctx.q(f"SELECT COUNT(*) {loans} AND l.status = 'gecikmede'"),
            ctx.q("SELECT COUNT(*) FROM customers WHERE region_affected = 1 AND address_changed_at > ? "
                  "AND customer_number IN (SELECT customer_number FROM loans)", DISASTER)]


def c_e_contacts(ctx):
    need_db(ctx)
    surge = ctx.q("SELECT COUNT(*) FROM contacts WHERE region_affected = 1 AND created_at >= ?", E_SURGE_START)
    topic = ctx.q("SELECT COUNT(*) FROM contacts WHERE region_affected = 1 AND created_at >= ? AND subcategory = ?",
                  E_SURGE_START, "erteleme / ödeme güçlüğü")
    base = ctx.q("SELECT COUNT(*) FROM contacts WHERE region_affected = 1 AND created_at >= ? AND created_at < ?",
                 E_BASE_START, E_SURGE_START)
    return [surge, topic, round(base / 30)]


def c_e_search(ctx):
    need_search(ctx)
    return sorted(r["id"] for r in ctx.find("requests", demo_reset.E_TEXT, 3, srch.COMPLETED_REQUESTS))


def c_e_plan(ctx):
    cal = ctx.catalog["service_calendar"]
    return [dm(plan(cal, "KREDI_TAKIP", 8, priority=True)), dm(plan(cal, "KREDI_TAKIP", 9, priority=True)),
            dm(plan(cal, "KREDI_TAKIP", 8))]


def c_e_screen(ctx):
    need_db(ctx)
    return ctx.q("SELECT COUNT(*) FROM screens WHERE code = 'KRDTERTL'")


def c_f(ctx):
    need_db(ctx)
    day = ctx.now.astimezone(TR).replace(hour=0, minute=0, second=0, microsecond=0)
    rows = ctx.db.query("SELECT screen_code, COUNT(*) FROM banking_logs WHERE level IN ('warn', 'error') AND ts >= ? "
                        "AND ts < ? GROUP BY screen_code", [db.utc_iso(day), db.utc_iso(ctx.now)])
    return max(rows, key=lambda r: r[1])[0] if rows else "-"


CHECKS: List[Tuple[str, str, str, Callable, object]] = [
    ("Genel", "Kayıt sayıları (logs, customers, loans, contacts, incidents, solutions, requests, announcements)",
     "≈10.400 / 40.000 / 33.000 / ≈8.300 / 1.400 / 37 / 95 / 20", c_counts, counts_ok),
    ("Genel", "Bütünlük: sahipsiz kredi / ana kayıt / temas çağrısı / çözüm", "0 / 0 / 0 / 0", c_integrity, [0, 0, 0, 0]),
    ("Genel", "SQL ↔ AI Search eşitliği: solutions / requests / announcements (SQL | indeks)", "aynı",
     c_sync, lambda f, ctx: f[0] == f[1]),
    ("A", "Elif'in aylık geliri", "38.000", c_elif, 38_000),
    ("A", "loanPlan: 400.000 · 3 ay / 36 ay taksit; 36 ayda azami tutar", "144.185,92 / 22.754,17 / ≈334.004",
     c_loan, loan_ok),
    ("B", "Son 30 dk Başkentgaz INSTITUTION_TIMEOUT (demo_reset sonrası)", "46", c_b_window, 46),
    ("B", "CAG-2051'e bağlı vaka", "11", c_b_linked, 11),
    ("B", f"solutions: \"{B_QUERY}\"", "SOL-031, skor ≥ eşik", c_b_search,
     lambda f, ctx: f[0] == "SOL-031" and f[1] >= ctx.threshold),
    ("C", "01.10 sonrası subscriber_no hatası: toplam / İSKİ / İSKİ 13 hane / farklı müşteri",
     "412 / 400 / 400 / 187", c_c_counts, [412, 400, 400, 187]),
    ("C", "01.10 öncesi İSKİ 13 hane", "0", c_c_before, 0),
    ("C", "C çağrıları (açık, İSKİ, abone no)", "23", c_c_incidents, 23),
    ("C", f"solutions: \"{C_QUERY}\" en yüksek skor", "< eşik (≈0,35)", c_c_search, lambda f, ctx: f < ctx.threshold),
    ("C", "announcements: aynı sorgu", "DUY-0412 ilk; DUY-0419 var", c_c_ann, ["DUY-0412", "DUY-0419 var"]),
    ("D", "Son 90 gün Kredi temasları: hatırlatma / faiz itirazı / taksit sorusu", "71 / 64 / 51", c_d_contacts,
     [71, 64, 51]),
    ("D", "Hedef grup / e-posta / SMS / en az biri", "2.340 / 1.357 / 1.895 / 2.083", c_d_target,
     [2340, 1357, 1895, 2083]),
    ("D", "requests: D talep metni ilk 5", "0871, 0915, 0962, 1004, 1019", c_d_search, sorted(D_TOP5)),
    ("D", "Takvim: Kredi Takip 15 / SMS ile 16", "09.11 → 02.12 / 09.11 → 04.12", c_d_plan,
     ["09.11 → 02.12", "09.11 → 04.12"]),
    ("E", "Etkilenen bölge: müşteri / kredi / gecikmede / adres değişikliği", "4.870 / 6.215 / 612 / 37", c_e_region,
     [4870, 6215, 612, 37]),
    ("E", "Bölge temasları: 12.10 sonrası / erteleme / önceki 30 gün günlük", "497 / 418 / 16", c_e_contacts,
     [497, 418, 16]),
    ("E", "requests: E talep metni ilk 3", "0588, 0712, 0846", c_e_search, sorted(E_TOP3)),
    ("E", "Takvim: öncelik 8 / öncelik + SMS 9 / sıraya koy 8", "19.10 → 30.10 / 19.10 → 02.11 / 09.11 → 20.11",
     c_e_plan, ["19.10 → 30.10", "19.10 → 02.11", "09.11 → 20.11"]),
    ("E", "Katalogda KRDTERTL", "0 (yok)", c_e_screen, 0),
    ("F", "Bugün en çok warn/error alan ekran", "ODMTFATR", c_f, "ODMTFATR"),
]


def judge(rule, found, ctx) -> bool:
    if callable(rule):
        return bool(rule(found, ctx))
    return found == rule


def run_checks(ctx: Ctx, only: Optional[Sequence[str]] = None) -> List[Dict]:
    results = []
    for scenario, label, expected, fn, rule in CHECKS:
        if only and scenario not in only:
            continue
        try:
            found = fn(ctx)
            status = "✓" if judge(rule, found, ctx) else "✗"
            shown = fmt(found)
        except Skip as why:
            status, shown = "–", f"atlandı ({why})"
        results.append({"scenario": scenario, "label": label, "expected": expected, "found": shown, "status": status})
    return results


# ---------------------------------------------------------------------------
# Değerlendirme seti (§8.1)
# ---------------------------------------------------------------------------
def run_eval(ctx: Ctx, cases: Optional[List[Dict]] = None) -> List[Dict]:
    need_search(ctx)
    cases = cases or json.loads((SEED / "eval_cases.json").read_text(encoding="utf-8"))["cases"]
    match = [c for c in cases if c["group"] == "match"]
    no_match = [c for c in cases if c["group"] == "no_match"]
    hits = wrong = 0
    for c in match:
        top = ctx.find("solutions", c["text"], 3)[0]
        hits += top["id"] == c["expected_solution_id"] and top["score"] >= ctx.threshold
    for c in no_match:
        wrong += ctx.find("solutions", c["text"], 1)[0]["score"] >= ctx.threshold
    out = [{"scenario": "Değerlendirme", "label": "match: doğru çözüm ve skor ≥ eşik", "expected": "≥ 8/10",
            "found": f"{hits}/{len(match)}", "status": "✓" if hits >= 8 else "✗"},
           {"scenario": "Değerlendirme", "label": "no_match: yanlış eşleşme", "expected": "≤ 1/10",
            "found": f"{wrong}/{len(no_match)}", "status": "✓" if wrong <= 1 else "✗"},
           {"scenario": "Değerlendirme", "label": "request: sınıflandırma", "expected": "≥ 8/10",
            "found": "atlandı (backend /api/requests/analyze ile ölçülür)", "status": "–"}]
    unreviewed = sum(1 for c in cases if not c.get("reviewed"))
    if unreviewed:
        out.append({"scenario": "Değerlendirme", "label": "gözden geçirilmemiş vaka", "expected": "0",
                    "found": str(unreviewed), "status": "!"})
    return out


def print_results(results: List[Dict]) -> None:
    for r in results:
        print(f" {r['status']}  {r['scenario']:<13} {r['label']}\n      beklenen: {r['expected']}   bulunan: {r['found']}")
    ok = sum(r["status"] == "✓" for r in results)
    bad = sum(r["status"] == "✗" for r in results)
    skip = sum(r["status"] == "–" for r in results)
    print(f"\n{ok} geçti · {bad} hatalı · {skip} atlandı")


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sql", action="store_true", help="Azure SQL")
    p.add_argument("--sqlite", nargs="?", const=str(db.DEFAULT_SQLITE), metavar="DOSYA", help="yerel SQLite")
    p.add_argument("--search", action="store_true", help="AI Search satırlarını da çalıştır")
    p.add_argument("--now", help="demo anı (demo_reset ile aynı); varsayılan şu an")
    p.add_argument("--only", help="senaryo filtresi, ör. B,C")
    p.add_argument("--eval", action="store_true", help="değerlendirme setini çalıştır (--search gerekir)")
    a = p.parse_args(argv)
    database = db.Database.azure() if a.sql else db.Database.sqlite(Path(a.sqlite)) if a.sqlite else None
    search = embedder = None
    if a.search or a.eval:
        search, embedder = srch.AzureSearch(), srch.FoundryEmbedder()
    ctx = Ctx(database, demo_reset.parse_now(a.now), search, embedder,
              float(os.environ.get("MATCH_THRESHOLD", "0.75")))
    only = [s.strip() for s in a.only.split(",")] if a.only else None
    results = run_checks(ctx, only)
    if a.eval:
        results += run_eval(ctx)
    print_results(results)
    if database:
        database.close()
    return 1 if any(r["status"] == "✗" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
