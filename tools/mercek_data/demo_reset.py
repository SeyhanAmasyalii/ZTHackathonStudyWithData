#!/usr/bin/env python3
"""Demo sıfırlama (V8). Her prova ve gerçek demodan hemen önce çalıştırılır. docs/mercek-sentetik-veri-uretimi.md §11.

Kullanım:
  python3 tools/mercek_data/demo_reset.py --sqlite                    # yerel data/out/mercek.db
  python3 tools/mercek_data/demo_reset.py --sql                       # Azure SQL
  python3 tools/mercek_data/demo_reset.py --sql --now 2026-10-17T13:20:00+03:00 --with-d-plan

Adımlar (tek transaction; hata olursa hiçbir şey değişmez):
  1. Canlı kayıtları siler: CAG-2051 ve sonrası, TLP-1043 ve sonrası, seed dışı loglar (demo penceresi ve
     uygulamanın yazdığı canlı loglar; source <> 'seed'), mercek_events.
  2. B penceresi: now−30 dk … now−1 dk arasına 46 Başkentgaz INSTITUTION_TIMEOUT logu (seed 7, her seferinde aynı),
     CAG-2051 ana kaydı (now−24 dk) ve ona bağlı 11 vaka CAG-2051-01 … -11 (now−22 … now−2 dk; müşteri, abone no,
     trace pencere loglarından). Bağlı vaka numarası = ana kayıt no + sıra; böylece uygulamanın açacağı bir sonraki
     ana kayıt CAG-2052 olur (C) ve Mehmet'in vakası CAG-2051-12 olur.
  3. --with-d-plan: D'nin talebi TLP-1043 planlı (20 a/g, Kredi Takip 09.11–04.12) eklenir (E'yi tek başına oynatmak için).
Mehmet'in canlı işlemi 47. kayıt olur; onu uygulama yazar.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402
import inject_log_scenarios as inj  # noqa: E402

TR = timezone(timedelta(hours=3))
MASTER_ID = "CAG-2051"
FIRST_LIVE_INCIDENT = 2051
FIRST_LIVE_REQUEST = "TLP-1043"
LINKED = 11
B_NOTES = [
    "Müşteri doğalgaz faturasını ödemek istedi, ekranda kurumdan yanıt alınamadı uyarısı çıktı.",
    "Başkentgaz faturası ödenemiyor, işlem zaman aşımına düşüyor. Müşteri tekrar denediğini söyledi.",
    "Şubede Başkentgaz fatura ödemesi yapılamadı; sistem kurumdan cevap gelmediğini gösteriyor.",
    "Mobil uygulamadan doğalgaz faturası ödenmiyor, birkaç dakika bekleyip hata veriyor.",
    "Müşteri internet şubesinde Başkentgaz faturasını ödeyemediğini, son ödeme tarihinin bugün olduğunu belirtti.",
]
D_TEXT = ("Taksit ödemelerindeki gecikmeleri azaltmak istiyoruz. Daha önce gecikme yapmış müşterilere, taksit ödeme "
          "tarihinden birkaç gün önce otomatik hatırlatma e-postası gönderilsin. Ayrıca temsilcilerimiz gerektiğinde "
          "ilgili ekrandan seçtikleri bir müşteriye o taksit için anında hatırlatma e-postası gönderebilsin.")
E_TEXT = ("Yönetim, doğal afetten etkilenen 3 ildeki müşterilerimizin bireysel kredi taksitlerinin 3 ay ertelenmesine "
          "karar verdi. Erteleme başvurusu şubelerden ve çağrı merkezinden alınabilsin, müşteriye ertelemeden sonraki "
          "yeni ödeme planı gösterilsin. Uygulamanın iki hafta içinde devreye girmesi gerekiyor.")
D_PLAN = {
    "request_id": FIRST_LIVE_REQUEST, "created_at": "2026-10-17", "requester_unit": "Kredi Tahsilatları",
    "title": "Gecikme yapmış müşterilere taksit hatırlatma (otomatik ve ekrandan)", "description": D_TEXT,
    "type": "mixed", "components_json": [{"kind": "otomatik"}, {"kind": "manuel"}], "screens_json": ["KRDRTKSR"],
    "services_json": [{"service_id": "KREDI_TAKIP", "role": "ana"}, {"service_id": "MUSTERI_YONETIM", "role": "etkilesimli"}],
    "effort_md": 20, "service_efforts_json": {"KREDI_TAKIP": 16, "MUSTERI_YONETIM": 4},
    "decisions": "Kanal e-posta + SMS (veriden eklenen kapsam); izin olmayan kanaldan gönderim yok",
    "scope_additions": ["ADD-SMS"], "analyst": "Ayşe Kaya", "approved_by": "Fatma", "status": "planli",
    "planned_service_id": "KREDI_TAKIP", "planned_from": "2026-11-09", "planned_to": "2026-12-04",
}


def parse_now(value: Optional[str]) -> datetime:
    if not value:
        return datetime.now(TR)
    ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if ts.tzinfo is None:
        raise SystemExit("--now saat dilimi içermeli (ör. 2026-10-17T13:20:00+03:00)")
    return ts


def log_pool(database: db.Database) -> Dict[str, Dict]:
    """Seed loglarındaki müşteriler (V3 ile aynı havuz; build_demo_window'a verilir)."""
    rows = database.query("SELECT raw_json FROM banking_logs WHERE source = 'seed' ORDER BY ts, log_id")
    if not rows:
        raise SystemExit("banking_logs boş: önce load_all.py çalıştırın")
    return inj.customers_from([json.loads(r[0]) for r in rows])


def incident_row(incident_id: str, ts: datetime, log: Dict, note: str, master: Optional[str]) -> Dict:
    bill = log["banking"]["bill"]
    channel = {"Şube": "sube", "Mobil": "dijital", "İnternet Şube": "dijital"}.get(log["channel"], "cagri_merkezi")
    return {"incident_id": incident_id, "created_at": ts, "channel": channel, "screen_code": "ODMTFATR",
            "category": "Fatura ödeme", "subcategory": "kurumdan yanıt alınamadı", "note": note,
            "customer_number": log["customer"]["number"], "subscriber_no": bill["subscriber_no"],
            "trace_id": log["trace"]["id"], "city": log["customer"]["city"], "service_id": "FATURA_ODEME",
            "error_code": "INSTITUTION_TIMEOUT", "institution": "Başkentgaz", "master_incident_id": master,
            "status": "acik", "solution_id": None, "resolution_minutes": None}


def build_b(now: datetime, pool: Dict[str, Dict]) -> Dict[str, List[Dict]]:
    window = inj.build_demo_window(now, pool)
    rng = random.Random(11)
    picks = rng.sample(window, LINKED + 1)
    incidents = [incident_row(MASTER_ID, now - timedelta(minutes=24), picks[0], B_NOTES[0], None)]
    for i, log in enumerate(picks[1:]):
        ts = now - timedelta(minutes=22) + timedelta(minutes=2 * i)  # −22 … −2 dk
        incidents.append(incident_row(f"{MASTER_ID}-{i + 1:02d}", ts, log,
                                      B_NOTES[(i + 1) % len(B_NOTES)], MASTER_ID))
    return {"logs": [db.flatten_log(r, source="demo") for r in window], "incidents": incidents}


def reset(database: db.Database, now: datetime, with_d_plan: bool = False) -> Dict[str, int]:
    pool = log_pool(database)
    b = build_b(now, pool)
    counts: Dict[str, int] = {}
    try:
        for table, where in (("incidents", f"incident_id >= 'CAG-{FIRST_LIVE_INCIDENT:04d}'"),
                             ("requests", f"request_id >= '{FIRST_LIVE_REQUEST}'"),
                             ("banking_logs", "source IS NULL OR source <> 'seed'"),
                             ("mercek_events", "1 = 1")):
            counts[f"silinen_{table}"] = database.scalar(f"SELECT COUNT(*) FROM {table} WHERE {where}")
            database.execute(f"DELETE FROM {table} WHERE {where}")
        counts["demo_logs"] = database.insert_many("banking_logs", b["logs"])
        counts["demo_incidents"] = database.insert_many("incidents", b["incidents"])
        if with_d_plan:
            counts["d_plan"] = database.insert_many("requests", [D_PLAN])
        database.commit()
    except BaseException:
        database.rollback()
        raise
    return counts


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    target = p.add_mutually_exclusive_group(required=True)
    target.add_argument("--sql", action="store_true", help="Azure SQL")
    target.add_argument("--sqlite", nargs="?", const=str(db.DEFAULT_SQLITE), metavar="DOSYA", help="yerel SQLite")
    p.add_argument("--now", help="demo anı (ISO, saat dilimli); varsayılan şu an")
    p.add_argument("--with-d-plan", action="store_true", help="TLP-1043 planını ekle (E'yi tek başına oynatmak için)")
    p.add_argument("--sync-search", action="store_true",
                   help="sonra AI Search indexer'larını hemen çalıştır (silinen/eklenen talepler indekse yansısın)")
    a = p.parse_args(argv)
    now = parse_now(a.now)
    database = db.Database.azure() if a.sql else db.Database.sqlite(Path(a.sqlite))
    counts = reset(database, now, a.with_d_plan)
    database.close()
    print(f"Demo sıfırlandı · now = {now.astimezone(TR).isoformat(timespec='minutes')}")
    for k, v in counts.items():
        print(f"  {k:<24} {v}")
    if a.sync_search:
        import search as srch

        print("AI Search indexer'ları tetiklendi:", ", ".join(srch.sync_now(srch.AzureSearch())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
