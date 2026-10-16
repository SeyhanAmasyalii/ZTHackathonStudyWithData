"""incidents.json üreticisi (datav2 nihai şeması).

Kararlar (16.10.2026):
- ~700 geçmiş çağrı, CAG-1351 … CAG-2050, 16.09 – 17.10 08:30 (+03). Her çağrı tek bir müşteri
  işlemine, yani tek bir hata loguna bağlıdır (kibana_correlation_id). Çağrı, logdan 5–60 dk sonra açılır.
- Dijital kanalda (3, 4) hata alan müşteri çağrı merkezini arar → çağrıyı çağrı merkezi (9009) açar.
  Servis kanalından (5) çağrı açılmaz.
- C: 12 İSKİ çağrısı (Kadıköy 5, Levent 4, Çağrı Merkezi 3); 10'u SOL-005 "kullanıcı hatası" ile
  kapatılmış, son 2'si açık.
- B: 6 kurum zaman aşımı çağrısı SOL-031 ile kapanmış ("6 benzer geçmiş olay").
- Telefon biçimi: logda hata numarası yok → mercek_assigned_error_code PHONE_FORMAT_INVALID, SOL-027.
- Mercek pilotu 15–16.10: yalnızca çağrı önerisi; o günlerin çağrılarında enriched_json dolu.
- Demo çağrıları (CAG-2051, CAG-2051-NN, CAG-2052) dosyada yok; demoda Mercek üretir.

Çalıştırma (repo kökünden):  python datav2/generators/incidents.py
"""

from __future__ import annotations

import json
import math
import random
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATA = Path(__file__).resolve().parents[1]
SEED = 42
TZ = timezone(timedelta(hours=3))
CUTOFF = datetime(2026, 10, 17, 8, 30, tzinfo=TZ)
PILOT_FROM = datetime(2026, 10, 15, 0, 0, tzinfo=TZ)
FIRST_NO = 1351
LAST_NO = 2050
TARGET = LAST_NO - FIRST_NO + 1  # 700

rng = random.Random(SEED)

# Hata numarası -> logdan çağrıya dönüşme olasılığı
CALL_RATE = {
    190101: 0.75, 190102: 0.75, 190103: 0.75,
    120218: 0.55, 120640: 0.45, 150210: 0.50, 130305: 0.40, 110520: 0.45, 110610: 0.30,
    130412: 0.35, 150220: 0.30, 160110: 0.35, 120101: 0.25, 120102: 0.30, 130101: 0.25,
    130102: 0.25, 140101: 0.30, 150101: 0.30,
}
PHONE_CALLS = 15
B_HISTORY = 6  # SOL-031 ile kapanmış geçmiş kurum kesintisi (B: "6 benzer geçmiş olay")
C_PLAN = {101: 5, 102: 4, 9009: 3}

SUBCATEGORY = {
    110731: "kurumdan yanıt alınamadı", 110412: "abone numarası kabul edilmiyor",
    110520: "talimat kaydedilemedi", 110610: "talimat kaydedilemedi",
    120218: "kullandırım yapılamadı", 120101: "kullandırım yapılamadı",
    120640: "taksit tahsil edilemedi", 120102: "taksit tahsil edilemedi",
    130305: "başvuru reddedildi", 130101: "başvuru tamamlanamadı",
    130412: "kart bilgileri güncellenemiyor", 130102: "kart bilgileri güncellenemiyor",
    140101: "hesap açılamadı", 150210: "kimlik doğrulama başarısız", 150220: "müşteri tanımlanamadı",
    160110: "parametre onayı tamamlanamadı",
}
TECH_SUB = "ekran açılmıyor / genel hata"

TEMPLATES = {  # hata kodu -> aday şablonlar
    "INSTITUTION_TIMEOUT": ["SOL-001", "SOL-002", "SOL-003"], "SUBSCRIBER_NO_INVALID": ["SOL-005"],
    "SUBSCRIBER_NOT_FOUND": ["SOL-006"], "ORDER_ALREADY_EXISTS": ["SOL-007"],
    "AFFORDABILITY_EXCEEDED": ["SOL-008", "SOL-009", "SOL-010", "SOL-011"],
    "INSUFFICIENT_BALANCE": ["SOL-013", "SOL-014"], "INSUFFICIENT_INCOME": ["SOL-017", "SOL-018"],
    "LIMIT_INCREASE_REJECTED": ["SOL-019"], "KPS_VERIFICATION_FAILED": ["SOL-023", "SOL-024"],
    "CUSTOMER_ALREADY_EXISTS": ["SOL-025"], "FOUR_EYES_REQUIRED": ["SOL-028"],
    "CORE_BANKING_TIMEOUT": ["SOL-029", "SOL-030", "SOL-032"],
    "SERVICE_UNAVAILABLE": ["SOL-033", "SOL-034"], "DB_CONNECTION_ERROR": ["SOL-035", "SOL-036", "SOL-037"],
    "PHONE_FORMAT_INVALID": ["SOL-027"],
}
VALIDATION_TEMPLATE = {"KRDTKULL": "SOL-012", "KRDTTAHS": "SOL-016", "KRTTBASV": None, "KRTTGUNC": "SOL-020",
                       "HSPTVDSZ": "SOL-021", "MUSTGUNC": "SOL-026"}
# Şablonsuz kapanışlar (ana, alt)
FALLBACK_CLOSURES = {
    "business": [("KULLANICI_KAYNAKLI", "KULLANICI_HATASI"), ("KULLANICI_KAYNAKLI", "KULLANICI_BILGI_EKSIKLIGI"),
                 ("IS_BIRIMLERI_KAYNAKLI", "IS_BIRIMI_KURAL"), ("INCELEME_CAGRISI", "INCELEME_SORUN_YOK"),
                 ("KULLANICI_KAYNAKLI", "SSS_ILE_CEVAPLANDI")],
    "technical": [("SISTEM_PERFORMANSI", "YAVASLIK"), ("TEKNIK_SORUN", "MERKEZI_SISTEM"),
                  ("INCELEME_CAGRISI", "INCELEME_SORUN_YOK")],
}
RESOLUTION_NOTES = {
    "KULLANICI_HATASI": "Kullanıcı yönlendirildi; işlem doğru bilgilerle tekrarlandı.",
    "KULLANICI_BILGI_EKSIKLIGI": "İşlem adımları kullanıcıya anlatıldı, işlem tamamlandı.",
    "IS_BIRIMI_KURAL": "İş kuralı gereği işlem yapılamayacağı bildirildi.",
    "INCELEME_SORUN_YOK": "Yapılan incelemede sistemsel sorun görülmedi; tekrar denemede işlem başarılı.",
    "SSS_ILE_CEVAPLANDI": "Sık sorulan sorular yanıtıyla bilgi verildi.",
    "YAVASLIK": "Anlık yavaşlık giderildi, işlem tekrarlandı.",
    "MERKEZI_SISTEM": "Merkezi sistemdeki geçici sorun giderildi.",
}

NOTE_TEMPLATES = {
    "kurumdan yanıt alınamadı": ["{inst} talimatında abone doğrulama adımında kurumdan yanıt gelmiyor.",
                                 "Talimat girişi sırasında {inst} için zaman aşımı alındı, işlem tamamlanamadı."],
    "abone numarası kabul edilmiyor": ["{inst} abone numarası ekranda kabul edilmiyor, talimat girilemiyor.",
                                       "Müşterinin faturadaki {inst} abone numarası girildiğinde geçersiz uyarısı alınıyor."],
    "talimat kaydedilemedi": ["Talimat onay adımında kaydedilemiyor, mükerrer talimat uyarısı var.",
                              "{inst} talimatı kaydedilemedi, kurum abone kaydını bulamadı.",
                              "Fatura talimatı son adımda hata verdi."],
    "kullandırım yapılamadı": ["Kredi kullandırımında uygunluk kontrolünde takılıyor, müşteri gelirinin yeterli olduğunu söylüyor.",
                               "İhtiyaç kredisi ödeme planı adımında hata alındı.",
                               "Kredi kullandırılamadı, ekranda uygun değil uyarısı var."],
    "taksit tahsil edilemedi": ["Gecikmedeki taksit tahsil edilemiyor, hesapta bakiye olduğu görülüyor.",
                                "Taksit tahsilatı yapılamadı, ekranda uyarı var."],
    "gecikme faizi hatalı hesaplandı": ["Tahsilat ekranında gecikme faizi beklenenden yüksek görünüyor, müşteri itiraz ediyor.",
                                        "Gecikme faizi tutarı önceki aya göre farklı hesaplanmış."],
    "başvuru reddedildi": ["Kart başvurusu gelir yetersiz denilerek reddedildi, müşteri itiraz ediyor.",
                           "Kredi kartı başvurusu sonuç adımında reddedildi."],
    "başvuru tamamlanamadı": ["Kart başvurusu gönderilemedi, form hatası alınıyor."],
    "kart bilgileri güncellenemiyor": ["Kart limit / hesap kesim günü güncellemesi kaydedilemiyor."],
    "hesap açılamadı": ["Vadesiz hesap açılışı onay adımında duruyor.", "Döviz hesabı açılamadı."],
    "kimlik doğrulama başarısız": ["Yeni müşteri tanımlamasında kimlik doğrulanamıyor."],
    "müşteri tanımlanamadı": ["Müşteri tanımlama kayıt adımında hata veriyor."],
    "adres güncellenemiyor": ["Müşteri bilgileri güncellemede adres bölümü kaydedilemiyor."],
    "telefon numarası hatalı": ["Müşterinin cep telefonu güncellenirken beklenmeyen hata alındı.",
                                "İletişim bilgisi güncellemesi kaydedilemiyor, telefon alanında hata var."],
    "parametre onayı tamamlanamadı": ["Parametre değişikliği kaydedilemiyor, onay ekranında hata var."],
    TECH_SUB: ["{screen} ekranında işlem sırasında sistem hatası alındı.",
               "{screen} ekranı yanıt vermiyor, işlem tamamlanamadı."],
}
CATEGORY_BY_SCREEN = {
    "ODMTTLMT": "Fatura talimatı", "KRDTKULL": "Kredi", "KRDTTAHS": "Kredi", "KRTTBASV": "Kart",
    "KRTTGUNC": "Kart", "HSPTVDSZ": "Hesap", "MUSTTANM": "Müşteri bilgileri", "MUSTGUNC": "Müşteri bilgileri",
    "PRMTGENL": "Parametre",
}
PRM_DEPARTMENT = {"KREDI": "KREDI_KULLANDIRIM", "TAHSILAT": "KREDI_TAKIP", "KART": "KART_YONETIM",
                  "ODEME": "FATURA_ODEME", "HESAP": "HESAP_YONETIM", "MUSTERI": "MUSTERI_YONETIM"}
BACKLOG_FROM = datetime(2026, 10, 13, 0, 0, tzinfo=TZ)
BACKLOG_RATE = 0.27
# Joyride senaryo eşleşmesi (datav2/ui/scenarios.ts). Eşleşme, çağrı türünün (ekran + hata + alt kategori)
# senaryonun `description` alanıyla anlamca karşılaştırılmasıyla belirlendi (17.10 kararı):
#  - aynı hatayı/reddi anlatan senaryo varsa o (ör. 120218 → krd-gelir-orani),
#  - doğrulama hatalarında, hatalı alanı doğru dolduran işlem turu (ör. 120101 → krd-36-ay),
#  - karşılığı olmayan türlerde (19xx teknik hatalar, 110520, 110610, 150220) boş.
SCENARIO_BASE_URL = "https://webapp-test-dev-frontend-eycfa5hpakcvg4ak.westus3-01.azurewebsites.net/tour/bankacilik"
SCENARIO_BY_TYPE = {  # (ekran, hata no | "PHONE", alt kategori | None) -> senaryo id
    ("KRTTBASV", 130305, None): "krt-gelir-yetersiz",
    ("KRTTBASV", 130101, None): "krt-gold-onay",
    ("KRTTGUNC", 130412, None): "krt-limit-red",
    ("KRTTGUNC", 130102, None): "krt-kart-guncelle",
    ("KRDTKULL", 120218, None): "krd-gelir-orani",
    ("KRDTKULL", 120101, None): "krd-36-ay",
    ("KRDTTAHS", 120640, None): "tah-bakiye-yetersiz",
    ("KRDTTAHS", 120102, None): "tah-taksit-tahsilat",
    ("HSPTVDSZ", 140101, None): "hsp-usd",
    ("MUSTTANM", 150210, None): "mtn-yeni-musteri",
    ("MUSTGUNC", 150101, None): "mus-adres",
    ("MUSTGUNC", "PHONE", None): "mus-telefon-bicim",
    ("ODMTTLMT", 110731, None): "odm-baskentgaz-zaman-asimi",
    ("ODMTTLMT", 110412, None): "odm-iski-13-hane",
    ("PRMTGENL", 160110, None): "prm-dort-goz",
}


def scenario_path(screen: str, error_key: int | str | None) -> str | None:
    scenario_id = SCENARIO_BY_TYPE.get((screen, error_key, None))
    return f"{SCENARIO_BASE_URL}/{screen}/{scenario_id}" if scenario_id else None


PRIORITY = {1: 3, 2: 12, 3: 55, 4: 25, 5: 5}


def load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def fmt(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M:%S+03:00")


class IncidentFactory:
    def __init__(self) -> None:
        self.logs = load("kibana_logs.json")
        self.rules = load("error_handling_rules.json")
        self.templates = {t["solution_template_id"]: t for t in load("solution_templates.json")}
        self.institutions = {i["institution_code"]: i for i in load("institutions.json")}
        self.channels = {c["channel_id"]: c for c in load("channels.json")}
        self.categories = {(c["category"], c["subcategory"]): c["screen_code"] for c in load("incident_categories.json")}
        self.main_department = {sd["screen_code"]: sd["department_id"] for sd in load("screen_departments.json")
                                if sd["role"] == "ana"}
        self.rule_department = {(r["screen_code"], r["error_number"]): r["department_id"] for r in self.rules}

    # --- seçim ---------------------------------------------------------------
    def eligible(self, log: dict) -> bool:
        return (parse(log["log_time"]) < CUTOFF - timedelta(minutes=30)
                and log["channel_id"] != 5
                and log["log_level"] != "Information")

    def pick_logs(self) -> list[tuple[dict, str]]:
        picked: list[tuple[dict, str]] = []
        candidates = [lg for lg in self.logs if self.eligible(lg)]

        # C · 12 İSKİ çağrısı (her birim için kronolojik)
        c_logs = [lg for lg in candidates if lg["app_exception_value"] == 110412 and '"SU01"' in lg["message_fields"]]
        for unit, count in C_PLAN.items():
            pool = [lg for lg in c_logs if self.reporter(lg) == unit]
            step = len(pool) // count
            picked += [(pool[i * step + rng.randrange(step)], "C") for i in range(count)]

        # Kurum zaman aşımları (B geçmişi)
        timeouts = [lg for lg in candidates if lg["app_exception_value"] == 110731 and lg["channel_id"] != 5]
        picked += [(lg, "B") for lg in rng.sample(timeouts, min(B_HISTORY, len(timeouts)))]

        # Telefon biçimi
        phone = [lg for lg in candidates if lg["mercek_assigned_error_number"]]
        picked += [(lg, "PHONE") for lg in rng.sample(phone, PHONE_CALLS)]

        # Gündelik
        used = {lg["log_id"] for lg, _ in picked}
        pool = [lg for lg in candidates if lg["log_id"] not in used and lg["app_exception_value"] in CALL_RATE]
        # ağırlıklı, tekrarsız örnekleme (Efraimidis–Spirakis): çağrıya dönüşme olasılığı yüksek hata öne çıkar
        pool.sort(key=lambda lg: rng.random() ** (1 / CALL_RATE[lg["app_exception_value"]]), reverse=True)
        picked += [(lg, "DAILY") for lg in pool[: TARGET - len(picked)]]
        assert len(picked) == TARGET, len(picked)
        return picked

    def reporter(self, log: dict) -> int:
        channel = log["channel_id"]
        if channel in (2, 3, 4):
            return 9009
        return log["branch_id"]

    # --- alanlar -------------------------------------------------------------
    def incident_channel(self, log: dict) -> str:
        return "cagri_merkezi" if log["channel_id"] in (3, 4) else self.channels[log["channel_id"]]["incident_channel"]

    def created_at(self, log: dict, channel: str) -> datetime:
        ts = parse(log["log_time"]) + timedelta(minutes=rng.randint(5, 60), seconds=rng.randint(0, 59))
        if channel in ("sube", "is_birimi") and not 9 <= ts.hour < 18:  # şube 09–18 açık
            next_day = ts if ts.hour < 9 else ts + timedelta(days=1)
            ts = next_day.replace(hour=9, minute=rng.randint(0, 59))
        while channel in ("sube", "is_birimi") and ts.weekday() >= 5:
            ts += timedelta(days=1)
        if channel == "cagri_merkezi" and not 8 <= ts.hour < 22:  # çağrı merkezi 08–22 açık
            next_day = ts if ts.hour < 8 else ts + timedelta(days=1)
            ts = next_day.replace(hour=8, minute=rng.randint(0, 59))
        return min(ts, CUTOFF - timedelta(minutes=rng.randint(1, 20)))

    def department(self, log: dict) -> str | None:
        screen = log["screen_id"]
        if screen == "PRMTGENL":
            group = json.loads(log["message_fields"]).get("parameterGroup", "KREDI")
            return PRM_DEPARTMENT[group]
        return self.rule_department.get((screen, log["app_exception_value"])) or self.main_department.get(screen)

    def error_code(self, log: dict) -> str:
        if log["mercek_assigned_error_number"]:
            return "PHONE_FORMAT_INVALID"
        return next(r["error_code"] for r in self.rules if r["error_number"] == log["app_exception_value"])

    def classify(self, log: dict, kind: str) -> tuple[str, str]:
        number = log["app_exception_value"]
        if kind == "PHONE":
            sub = "telefon numarası hatalı"
        elif number and number >= 190000:
            sub = TECH_SUB
        elif number == 150101:
            sub = "adres güncellenemiyor"
        elif number == 120102 and rng.random() < 0.4:
            sub = "gecikme faizi hatalı hesaplandı"
        else:
            sub = SUBCATEGORY[number]
        category = "Diğer" if sub == TECH_SUB else CATEGORY_BY_SCREEN[log["screen_id"]]
        assert (category, sub) in self.categories, (category, sub)
        return category, sub

    def template(self, log: dict, kind: str, code: str, sub: str, created: datetime) -> str | None:
        if kind == "C":
            return "SOL-005"
        if kind == "B":
            return "SOL-004" if 2 <= parse(log["log_time"]).hour < 4 else "SOL-031"
        if kind == "PHONE":
            return "SOL-027"
        if sub == "gecikme faizi hatalı hesaplandı":
            return "SOL-015"
        if rng.random() > 0.6:
            return None
        if code == "VALIDATION_ERROR":
            return VALIDATION_TEMPLATE.get(log["screen_id"])
        return rng.choice(TEMPLATES[code])

    def note(self, sub: str, log: dict, institution: str | None) -> str:
        text = rng.choice(NOTE_TEMPLATES[sub])
        inst_name = self.institutions[institution]["name"] if institution else ""
        return text.format(inst=inst_name, screen=log["screen_id"])

    def enrichment(self, incident: dict, template_id: str | None, code: str) -> dict:
        suggested = template_id or rng.choice(TEMPLATES.get(code, ["SOL-029"]))
        tpl = self.templates[suggested]
        return {
            "mercek_version": "pilot-2026-10-15",
            "error_code": code,
            "suggested_template_id": suggested,
            "suggested_closure_code": tpl["closure_code"],
            "suggested_sub_closure_code": tpl["sub_closure_code"],
            "suggested_department_id": incident["department_id"],
            "explanation": f"{tpl['mercek_assigned_title']}: {tpl['mercek_assigned_root_cause']}",
            "accepted": template_id == suggested,
        }

    # --- çağrı ---------------------------------------------------------------
    def build(self, number: int, log: dict, kind: str) -> dict:
        channel = self.incident_channel(log)
        created = self.created_at(log, channel)
        category, sub = self.classify(log, kind)
        fields = json.loads(log["message_fields"])
        institution = fields.get("institutionCode")
        code = self.error_code(log)
        template_id = self.template(log, kind, code, sub, created)
        if template_id:
            tpl = self.templates[template_id]
            closure, sub_closure = tpl["closure_code"], tpl["sub_closure_code"]
            resolution = tpl["mercek_assigned_steps"] and json.loads(tpl["mercek_assigned_steps"])[-1]
        else:
            closure, sub_closure = rng.choice(FALLBACK_CLOSURES["technical" if code in
                                              ("CORE_BANKING_TIMEOUT", "SERVICE_UNAVAILABLE", "DB_CONNECTION_ERROR")
                                              else "business"])
            resolution = RESOLUTION_NOTES[sub_closure]
        priority = 2 if kind == "B" else rng.choices(list(PRIORITY), weights=list(PRIORITY.values()), k=1)[0]
        minutes = max(15, int(rng.lognormvariate(math.log(300), 0.8)))
        resolved = created + timedelta(minutes=minutes)
        incident = {
            "incident_id": f"CAG-{number:04d}",
            "created_at": fmt(created),
            "channel": channel,
            "reporter_unit_id": self.reporter(log),
            "screen_code": log["screen_id"],
            "category": category,
            "subcategory": sub,
            "note": self.note(sub, log, institution),
            "customer_number": log["customer_id"],
            "kibana_correlation_id": log["correlation_id"],
            "department_id": self.department(log),
            "mercek_assigned_error_code": "PHONE_FORMAT_INVALID" if kind == "PHONE" else None,
            "institution_code": institution,
            "master_incident_id": None,
            "priority": priority,
            "status": "kapali",
            "solution_template_id": template_id,
            "closure_code": closure,
            "sub_closure_code": sub_closure,
            "resolution_note": resolution,
            "resolved_at": fmt(resolved),
            "enriched_json": None,
            "scenario_path": scenario_path(log["screen_id"], "PHONE" if kind == "PHONE" else log["app_exception_value"]),
        }
        if created >= PILOT_FROM:
            enrichment = self.enrichment(incident, template_id, code)
            if enrichment["accepted"]:
                resolved = created + timedelta(minutes=max(10, minutes // 2))
                incident["resolved_at"] = fmt(resolved)
            incident["enriched_json"] = json.dumps(enrichment, ensure_ascii=False)
        if resolved >= CUTOFF or (created >= BACKLOG_FROM and kind != "C" and rng.random() < BACKLOG_RATE):
            self.open(incident)
        return incident

    @staticmethod
    def open(incident: dict) -> None:
        incident.update(status="acik", solution_template_id=None, closure_code=None, sub_closure_code=None,
                        resolution_note=None, resolved_at=None)
        if incident["enriched_json"]:
            enrichment = json.loads(incident["enriched_json"])
            enrichment["accepted"] = None  # karar çağrı kapanınca verilir
            incident["enriched_json"] = json.dumps(enrichment, ensure_ascii=False)


def stats(incidents: list[dict]) -> dict:
    def count(pred):
        return sum(1 for i in incidents if pred(i))

    c = [i for i in incidents if i["institution_code"] == "SU01" and i["subcategory"] == "abone numarası kabul edilmiyor"]
    assert len(c) == sum(C_PLAN.values()), len(c)
    pilot = [i for i in incidents if i["enriched_json"]]
    accepted = [i for i in pilot if json.loads(i["enriched_json"])["accepted"] and i["status"] == "kapali"]
    return {
        "total": len(incidents),
        "ids": [incidents[0]["incident_id"], incidents[-1]["incident_id"]],
        "period": [incidents[0]["created_at"], incidents[-1]["created_at"]],
        "status": dict(Counter(i["status"] for i in incidents)),
        "channel": dict(Counter(i["channel"] for i in incidents)),
        "screens": dict(Counter(i["screen_code"] for i in incidents).most_common()),
        "priority": dict(sorted(Counter(i["priority"] for i in incidents).items())),
        "with_template": count(lambda i: i["solution_template_id"]),
        "linked_to_log": count(lambda i: i["kibana_correlation_id"]),
        "A_affordability": count(lambda i: i["screen_code"] == "KRDTKULL" and i["subcategory"] == "kullandırım yapılamadı"),
        "B_institution_timeout": {i["incident_id"]: [i["institution_code"], i["solution_template_id"]]
                                  for i in incidents if i["subcategory"] == "kurumdan yanıt alınamadı"},
        "C_iski": {"total": len(c), "by_unit": dict(Counter(i["reporter_unit_id"] for i in c)),
                   "closed_with_SOL_005": sum(1 for i in c if i["solution_template_id"] == "SOL-005"),
                   "open": sum(1 for i in c if i["status"] == "acik")},
        "phone_format": count(lambda i: i["mercek_assigned_error_code"] == "PHONE_FORMAT_INVALID"),
        "scenario_path": dict(Counter(i["scenario_path"].rsplit("/", 1)[-1] if i["scenario_path"] else None
                                      for i in incidents).most_common()),
        "pilot_enriched": len(pilot),
        "pilot_accepted_and_closed": len(accepted),
        "demo_expected": {
            "CAG-2051": "B ana kaydı; demoda Mercek açar (GAZ02, ODMTTLMT, 110731, priority 2, SOL-031)",
            "CAG-2051-NN": "B bağlı vakaları; MUKERRER_CAGRI / ANA_KAYDA_BAGLANDI",
            "CAG-2052": "C ana kaydı; demoda Mercek örüntüden açar (SU01, 110412)",
        },
    }


def main() -> None:
    factory = IncidentFactory()
    picked = factory.pick_logs()
    picked.sort(key=lambda p: p[0]["log_time"])
    incidents = [factory.build(FIRST_NO + n, log, kind) for n, (log, kind) in enumerate(picked)]
    incidents.sort(key=lambda i: i["created_at"])
    for n, incident in enumerate(incidents):
        incident["incident_id"] = f"CAG-{FIRST_NO + n:04d}"

    # C: son 2 İSKİ çağrısı açık kalır
    c = [i for i in incidents if i["institution_code"] == "SU01" and i["subcategory"] == "abone numarası kabul edilmiyor"]
    for incident in c[-2:]:
        IncidentFactory.open(incident)

    (DATA / "incidents.json").write_text(json.dumps(incidents, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = stats(incidents)
    (DATA / "incidents.stats.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
