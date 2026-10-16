"""kibana_logs.json üreticisi (datav2 nihai şeması, eski banking_logs'un yerine).

Parçalar (seed 42, deterministik):
- Gündelik akış      10.000  16.09.2026 00:00 – 17.10.2026 09:00 (+03), 9 ekran, 20 kuraldan hatalar
- B  Başkentgaz          46  17.10 08:30–09:00, ODMTTLMT, GAZ02, 110731 INSTITUTION_TIMEOUT
- C  abone no           412  01.10 sonrası ODMTTLMT 110412 (400 İSKİ · 13 hane, 12 ASKİ); öncesinde 0
- E  adres değişikliği   37  MUSTGUNC başarılı adres güncellemesi (customers.stats.json)
- Telefon biçimi         60  MUSTGUNC kuralsız hata; app_exception_value boş, mercek_assigned 150130

KVKK: IP, makine adı, bağlantı kimliği, AD kullanıcı adı üretilmez; mesaj alanlarında kişisel veri
(ad, TCKN, telefon, e-posta, adres, abone numarasının kendisi) yoktur. Kullanıcılar sentetik koddur.

Çalıştırma (repo kökünden):  python datav2/generators/kibana_logs.py
"""

from __future__ import annotations

import json
import random
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "datav2"

SEED = 42
TZ = timezone(timedelta(hours=3))
START = datetime(2026, 9, 16, 0, 0, tzinfo=TZ)
END = datetime(2026, 10, 17, 9, 0, tzinfo=TZ)
C_FROM = datetime(2026, 10, 1, 0, 0, tzinfo=TZ)
B_FROM = datetime(2026, 10, 17, 8, 30, tzinfo=TZ)

DAILY_COUNT = 10_000
B_COUNT = 46
C_ISKI_COUNT = 400
C_OTHER_COUNT = 12
PHONE_ERROR_COUNT = 60
PHONE_ERROR_NUMBER = 150130

rng = random.Random(SEED)

# ---------------------------------------------------------------------------
# Ekran tanımları
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Action:
    action_id: int
    name: str
    path: str
    method: str
    weight: int
    service: str  # .NET sınıfı (source_context son parçası)


SCREEN_META = {
    "KRTTBASV": ("Fineart.Kart", "Fineart.Kart.Basvuru", "krt"),
    "KRTTGUNC": ("Fineart.Kart", "Fineart.Kart.Guncelleme", "krt"),
    "KRDTKULL": ("Fineart.Kredi", "Fineart.Kredi.Kullandirim", "krd"),
    "MUSTTANM": ("Fineart.Musteri", "Fineart.Musteri.Tanimlama", "mus"),
    "MUSTGUNC": ("Fineart.Musteri", "Fineart.Musteri.Guncelleme", "mus"),
    "HSPTVDSZ": ("Fineart.Hesap", "Fineart.Hesap.Vadesiz", "hsp"),
    "ODMTTLMT": ("Fineart.Odeme", "Fineart.Odeme.Talimat", "odm"),
    "KRDTTAHS": ("Fineart.Kredi", "Fineart.Kredi.Tahsilat", "krd"),
    "PRMTGENL": ("Fineart.Parametre", "Fineart.Parametre.Genel", "prm"),
}

ACTIONS = {
    "KRTTBASV": [
        Action(1301, "BasvuruBaslat", "/api/krt/basvuru", "GET", 3, "BasvuruController"),
        Action(1302, "LimitHesapla", "/api/krt/basvuru/limit", "POST", 3, "LimitService"),
        Action(1303, "BasvuruGonder", "/api/krt/basvuru", "POST", 4, "BasvuruService"),
    ],
    "KRTTGUNC": [
        Action(1311, "KartGetir", "/api/krt/kart", "GET", 4, "KartController"),
        Action(1312, "KartBilgiGuncelle", "/api/krt/kart/guncelle", "PUT", 6, "KartGuncellemeService"),
    ],
    "KRDTKULL": [
        Action(1201, "OdemePlaniHesapla", "/api/krd/kullandirim/odeme-plani", "POST", 4, "OdemePlaniService"),
        Action(1202, "UygunlukKontrol", "/api/krd/kullandirim/uygunluk", "POST", 3, "UygunlukService"),
        Action(1203, "KrediKullandir", "/api/krd/kullandirim", "POST", 3, "KullandirimService"),
    ],
    "MUSTTANM": [
        Action(1501, "KimlikDogrula", "/api/mus/tanimlama/kimlik-dogrula", "POST", 5, "KimlikDogrulamaService"),
        Action(1502, "MusteriKaydet", "/api/mus/tanimlama", "POST", 5, "MusteriTanimlamaService"),
    ],
    "MUSTGUNC": [
        Action(1511, "MusteriGetir", "/api/mus/musteri", "GET", 4, "MusteriController"),
        Action(1512, "MusteriGuncelle", "/api/mus/musteri/guncelle", "PUT", 6, "MusteriGuncellemeService"),
    ],
    "HSPTVDSZ": [
        Action(1401, "HesapOnKontrol", "/api/hsp/vadesiz/on-kontrol", "POST", 4, "HesapAcilisController"),
        Action(1402, "HesapAc", "/api/hsp/vadesiz", "POST", 6, "HesapAcilisService"),
    ],
    "ODMTTLMT": [
        Action(1101, "KurumListele", "/api/odm/talimat/kurumlar", "GET", 2, "TalimatController"),
        Action(1102, "AboneDogrula", "/api/odm/talimat/abone-dogrula", "POST", 5, "AboneDogrulamaService"),
        Action(1103, "TalimatKaydet", "/api/odm/talimat", "POST", 3, "TalimatService"),
    ],
    "KRDTTAHS": [
        Action(1211, "TaksitListele", "/api/krd/tahsilat/taksitler", "GET", 4, "TahsilatController"),
        Action(1212, "GecikmeFaiziHesapla", "/api/krd/tahsilat/gecikme-faizi", "POST", 2, "GecikmeFaiziService"),
        Action(1213, "TaksitTahsilEt", "/api/krd/tahsilat", "POST", 4, "TahsilatService"),
    ],
    "PRMTGENL": [
        Action(1601, "ParametreListele", "/api/prm/parametreler", "GET", 4, "ParametreController"),
        Action(1602, "ParametreDegisiklikGonder", "/api/prm/parametreler/degisiklik", "POST", 3, "ParametreService"),
        Action(1603, "ParametreOnayla", "/api/prm/parametreler/onay", "POST", 3, "ParametreOnayService"),
    ],
}

# Gündelik akışın ekranlara dağılımı (%)
SCREEN_WEIGHTS = {
    "ODMTTLMT": 22, "KRDTKULL": 14, "KRDTTAHS": 14, "HSPTVDSZ": 12, "MUSTGUNC": 10,
    "KRTTBASV": 10, "KRTTGUNC": 7, "MUSTTANM": 7, "PRMTGENL": 4,
}

# Ekran -> kanal ağırlıkları (1 Şube, 2 Çağrı Merkezi, 3 İnternet, 4 Mobil, 5 Servis, 6 İş Birimi)
CHANNEL_WEIGHTS = {
    "KRTTBASV": {1: 45, 2: 10, 3: 15, 4: 30},
    "KRTTGUNC": {1: 30, 2: 25, 3: 15, 4: 30},
    "KRDTKULL": {1: 50, 2: 5, 3: 10, 4: 30, 6: 5},
    "MUSTTANM": {1: 80, 4: 20},
    "MUSTGUNC": {1: 40, 2: 25, 3: 10, 4: 25},
    "HSPTVDSZ": {1: 50, 3: 15, 4: 35},
    "ODMTTLMT": {1: 40, 2: 15, 3: 15, 4: 30},
    "KRDTTAHS": {1: 35, 2: 20, 3: 10, 4: 15, 5: 10, 6: 10},
    "PRMTGENL": {6: 100},
}

CLIENT_IDS = {1: "fineart-sube", 2: "fineart-cagri", 3: "fineart-internet", 4: "fineart-mobil",
              5: "fineart-batch", 6: "fineart-genel-mudurluk"}

# İş birimi (kanal 6) kullanıcılarının birimi
G_UNIT_BY_SCREEN = {"KRDTKULL": [9002, 8001, 8006, 8035], "KRDTTAHS": [9001, 8002, 8006]}
PRM_UNITS = [9001, 9002, 9003, 9004, 9005, 9007]  # her departmanın kendi parametresi

# ---------------------------------------------------------------------------
# Hatalar: error_number -> (http, exception sınıfı, mesaj, ağırlık)
# ---------------------------------------------------------------------------

BUSINESS_ERRORS = {
    "KRTTBASV": [(130305, "Beyan edilen gelir talep edilen kart limiti için yetersiz.", 6),
                 (130101, "Başvuru formunda zorunlu alan eksik.", 4)],
    "KRTTGUNC": [(130412, "Limit artış talebi kart geçmişi nedeniyle reddedildi.", 5),
                 (130102, "Hesap kesim günü geçerli aralıkta değil.", 5)],
    "KRDTKULL": [(120218, "Aylık taksit tutarı gelirin %50'sini aşıyor; kredi uygun değil.", 7),
                 (120101, "Vade ya da tutar ürün sınırlarının dışında.", 3)],
    "MUSTTANM": [(150210, "Kimlik doğrulama servisi kimliği doğrulamadı.", 5),
                 (150220, "Bu kimlik numarasıyla kayıtlı müşteri zaten var.", 5)],
    "MUSTGUNC": [(150101, "Güncelleme formunda zorunlu alan eksik.", 10)],
    "HSPTVDSZ": [(140101, "Hesap açılış bilgilerinde zorunlu alan eksik.", 10)],
    "ODMTTLMT": [(110520, "Kurum abone kaydını bulamadı.", 6),
                 (110610, "Bu abone için aktif talimat zaten var.", 4)],
    "KRDTTAHS": [(120640, "Tahsilat hesabında taksit için yeterli bakiye yok.", 8),
                 (120102, "Seçilen taksit tahsilata uygun değil.", 2)],
    "PRMTGENL": [(160110, "Parametre değişikliği ikinci onaycı olmadan kaydedilemez.", 10)],
}

ERROR_CODES = {
    130305: "INSUFFICIENT_INCOME", 130101: "VALIDATION_ERROR", 130412: "LIMIT_INCREASE_REJECTED",
    130102: "VALIDATION_ERROR", 120218: "AFFORDABILITY_EXCEEDED", 120101: "VALIDATION_ERROR",
    150210: "KPS_VERIFICATION_FAILED", 150220: "CUSTOMER_ALREADY_EXISTS", 150101: "VALIDATION_ERROR",
    140101: "VALIDATION_ERROR", 110520: "SUBSCRIBER_NOT_FOUND", 110610: "ORDER_ALREADY_EXISTS",
    120640: "INSUFFICIENT_BALANCE", 120102: "VALIDATION_ERROR", 160110: "FOUR_EYES_REQUIRED",
    110731: "INSTITUTION_TIMEOUT", 110412: "SUBSCRIBER_NO_INVALID", 190101: "CORE_BANKING_TIMEOUT",
    190102: "SERVICE_UNAVAILABLE", 190103: "DB_CONNECTION_ERROR",
}

TECHNICAL_ERRORS = {
    190101: (504, "Ana bankacılık servisi yanıt vermedi (zaman aşımı).",
             "System.TimeoutException", "The operation has timed out after 30000 ms.", "Fineart.Core.Integration"),
    190102: (503, "Bağımlı servis geçici olarak kullanılamıyor.",
             "System.Net.Http.HttpRequestException", "Response status code does not indicate success: 503 (Service Unavailable).",
             "System.Net.Http"),
    190103: (500, "Veritabanı bağlantısı kurulamadı.",
             "Microsoft.Data.SqlClient.SqlException", "A network-related or instance-specific error occurred while establishing a connection to SQL Server.",
             "Core Microsoft SqlClient Data Provider"),
}

BUSINESS_RATE = 0.13
TECHNICAL_RATE = 0.017

# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------


def load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def weighted(options: dict):
    keys = list(options)
    return rng.choices(keys, weights=[options[k] for k in keys], k=1)[0]


def new_id() -> str:
    return uuid.UUID(int=rng.getrandbits(128), version=4).hex


def iso_utc(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{ts.microsecond // 1000:03d}Z"


def iso_local(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ts.microsecond // 1000:03d}+03:00"


def random_time(start: datetime, end: datetime, channel: int) -> datetime:
    """Kanalın çalışma saatlerine uyan rastgele zaman."""
    span = (end - start).total_seconds()
    for _ in range(200):
        ts = start + timedelta(seconds=rng.random() * span, microseconds=rng.randint(0, 999) * 1000)
        weekday, hour = ts.weekday(), ts.hour
        if channel in (1, 6):
            ok = weekday < 5 and 9 <= hour < 18
        elif channel == 2:
            ok = 8 <= hour < 22
        elif channel == 5:
            ok = 1 <= hour < 6
        else:
            ok = hour >= 7 or rng.random() < 0.15
        if ok:
            return ts
    return ts


def stack_trace(exc_type: str, message: str, screen: str, action: Action, files: dict) -> str:
    _, namespace, _ = SCREEN_META[screen]
    backend = files[screen]["backend"][0]
    line = 40 + action.action_id % 97
    frames = [
        f"{exc_type}: {message}",
        f"   at {namespace}.Services.{action.service}.{action.name}Async(RequestContext context) in {backend}:line {line}",
        f"   at {namespace}.Controllers.{SCREEN_META[screen][0].split('.')[-1]}Controller.{action.name}(RequestModel request) in {backend}:line {line - 31}",
        "   at Fineart.Core.Web.Middleware.ExceptionHandlingMiddleware.InvokeAsync(HttpContext context)",
    ]
    return "\n".join(frames)


# ---------------------------------------------------------------------------
# Kayıt üretimi
# ---------------------------------------------------------------------------


class LogFactory:
    def __init__(self) -> None:
        self.customers = load("customers.json")
        self.loans = load("loans.json")
        self.units = {u["unit_id"]: u for u in load("org_units.json")}
        self.institutions = {i["institution_code"]: i for i in load("institutions.json")}
        self.files = {s["code"]: s["files_json"] for s in load("screens.json")}
        self.by_no = {c["customer_number"]: c for c in self.customers}
        self.borrowers = sorted({ln["customer_number"] for ln in self.loans})
        self.loan_by_customer: dict[str, list[dict]] = {}
        for ln in self.loans:
            self.loan_by_customer.setdefault(ln["customer_number"], []).append(ln)
        self.delinquent = sorted({ln["customer_number"] for ln in self.loans if ln["status"] == "gecikmede"})
        self.synthetic = [c for c in self.customers if c["customer_number"] >= "10000101"]

    # --- müşteri ve birim ---------------------------------------------------
    def customer_branch(self, customer: dict) -> int:
        city = customer["city"]
        if city == "İstanbul":
            return 101 if int(customer["customer_number"]) % 2 else 102
        return {"Ankara": 601, "İzmir": 3501}.get(city, 9999)

    def pick_customer(self, screen: str) -> dict | None:
        if screen == "PRMTGENL":
            return None
        if screen == "KRDTTAHS":
            pool = self.delinquent if rng.random() < 0.45 else self.borrowers
            return self.by_no[rng.choice(pool)]
        if screen == "KRDTKULL" and rng.random() < 0.5:
            return self.by_no[rng.choice(self.borrowers)]
        return rng.choice(self.synthetic)

    def unit_for(self, screen: str, channel: int, customer: dict | None) -> int:
        if channel == 1:
            branch = self.customer_branch(customer) if customer else 101
            return branch if branch != 9999 else rng.choice([101, 102, 601, 3501])
        if channel == 2:
            return 9009
        if channel in (3, 4):
            return 9999
        if channel == 5:
            return 9006
        if screen == "PRMTGENL":
            return rng.choice(PRM_UNITS)
        return rng.choice(G_UNIT_BY_SCREEN[screen])

    def user_for(self, unit_id: int, channel: int) -> str:
        if channel in (3, 4):
            return "MUSTERI"
        if channel == 5:
            return "BATCH_TAHSILAT"
        unit_type = self.units[unit_id]["unit_type"].lower()
        return f"{unit_type}{unit_id}u{rng.randint(1, 12):02d}"

    # --- kayıt ---------------------------------------------------------------
    def build(self, *, ts: datetime, screen: str, action: Action, channel: int, customer: dict | None,
              unit_id: int | None = None, user_name: str | None = None, level: str = "Information",
              http_status: int = 200, message: str, error_number: int | None = None,
              business: bool = False, exception: tuple[str, str, str] | None = None,
              inner: tuple[str, str, str] | None = None, fields: dict | None = None,
              response: dict | None = None, mercek_error_number: int | None = None,
              correlation_id: str | None = None) -> dict:
        application, namespace, _ = SCREEN_META[screen]
        unit_id = unit_id if unit_id is not None else self.unit_for(screen, channel, customer)
        user_name = user_name or self.user_for(unit_id, channel)
        session_start = ts - timedelta(minutes=rng.randint(1, 90), seconds=rng.randint(0, 59))
        exc_type, exc_msg, exc_src = exception or (None, None, None)
        in_type, in_msg, in_src = inner or (None, None, None)
        query = f"?page=1&pageSize={rng.choice([10, 20, 50])}" if action.method == "GET" else None
        record = {
            "log_id": None,
            "timestamp": iso_utc(ts),
            "log_time": iso_local(ts),
            "log_level": level,
            "app_name": "fineart",
            "application": application,
            "source_context": f"{namespace}.Services.{action.service}",
            "action_id": action.action_id,
            "action_name": action.name,
            "request_path": action.path,
            "referer": f"/ekran/{screen}",
            "http_method": action.method,
            "http_status_code": http_status,
            "is_business_exception": business,
            "correlation_id": correlation_id or new_id(),
            "message": message,
            "exception_message": exc_msg,
            "exception_source": exc_src,
            "exception_stack_trace": stack_trace(exc_type, exc_msg, screen, action, self.files) if exc_type else None,
            "inner_exception_message": in_msg,
            "inner_exception_source": in_src,
            "inner_exception_stack_trace": f"{in_type}: {in_msg}\n   at {in_src}.Execute()" if in_type else None,
            "app_exception_value": error_number,
            "message_fields": json.dumps(fields or {}, ensure_ascii=False),
            "message_filter": json.dumps({"screen": screen, "action": action.name}, ensure_ascii=False),
            "message_query_string": query,
            "message_response": json.dumps(response or {"success": error_number is None and exc_type is None},
                                           ensure_ascii=False),
            "screen_id": screen,
            "branch_id": unit_id,
            "branch_type": self.units[unit_id]["unit_type"],
            "channel_id": channel,
            "call_id": f"CM-{ts:%Y%m%d}{rng.randint(0, 99999):05d}" if channel == 2 else None,
            "client_id": CLIENT_IDS[channel],
            "user_name": user_name,
            "current_date": ts.date().isoformat(),
            "customer_id": customer["customer_number"] if customer else None,
            "customer_branch_id": self.customer_branch(customer) if customer else None,
            "session_id": new_id(),
            "session_start_date": iso_local(session_start),
            "event_original": None,
            "mercek_assigned_error_number": mercek_error_number,
        }
        record["event_original"] = json.dumps({
            "@timestamp": record["timestamp"], "LogLevel": level, "AppName": "fineart",
            "Application": application, "SourceContext": record["source_context"],
            "ActionId": action.action_id, "ActionName": action.name, "RequestPath": action.path,
            "HttpStatusCode": http_status, "CorrelationId": record["correlation_id"], "Message": message,
            "AppExceptionValue": error_number, "ScreenId": screen, "BranchId": unit_id,
            "BranchType": record["branch_type"], "ChannelId": channel, "UserName": user_name,
            "CustomerId": record["customer_id"],
        }, ensure_ascii=False)
        return record

    # --- alanlar -------------------------------------------------------------
    def fields_for(self, screen: str, action: Action, customer: dict | None, institution: str | None = None,
                   subscriber_len: int | None = None) -> dict:
        if screen == "ODMTTLMT":
            inst = self.institutions[institution]
            data = {"institutionCode": institution, "billType": inst["bill_type"]}
            if action.name != "KurumListele":
                data["subscriberNoLength"] = subscriber_len
            if action.name == "TalimatKaydet":
                data["upperLimit"] = rng.choice([500, 1000, 1500, 2500])
            return data
        if screen in ("KRDTTAHS",) and customer:
            loans = self.loan_by_customer.get(customer["customer_number"])
            if loans:
                loan = rng.choice(loans)
                return {"loanId": loan["loan_id"], "installmentNo": loan["paid_installments"] + 1,
                        "loanStatus": loan["status"]}
        if screen == "KRDTKULL":
            return {"amount": rng.choice([50_000, 100_000, 150_000, 250_000, 400_000]),
                    "term": rng.choice([12, 18, 24, 36])}
        if screen == "PRMTGENL":
            return {"parameterGroup": rng.choice(["KREDI", "TAHSILAT", "KART", "ODEME", "HESAP", "MUSTERI"])}
        if screen == "MUSTGUNC":
            return {"section": rng.choice(["iletisim", "adres", "gelir", "izinler"])}
        if screen == "KRTTBASV":
            return {"cardType": rng.choice(["Classic", "Gold", "Platinum"])}
        if screen == "KRTTGUNC":
            return {"changeType": rng.choice(["limit", "hesap_kesim", "ekstre", "otomatik_odeme"])}
        if screen == "HSPTVDSZ":
            return {"currency": rng.choice(["TRY", "TRY", "TRY", "USD", "EUR"])}
        return {}

    # --- gündelik akış ---------------------------------------------------------
    def daily(self) -> dict:
        screen = weighted(SCREEN_WEIGHTS)
        channel = weighted(CHANNEL_WEIGHTS[screen])
        ts = random_time(START, B_FROM, channel)
        action = rng.choices(ACTIONS[screen], weights=[a.weight for a in ACTIONS[screen]], k=1)[0]
        customer = self.pick_customer(screen)
        institution, subscriber_len = None, None
        if screen == "ODMTTLMT":
            institution = rng.choice(sorted(self.institutions))
            subscriber_len = rng.randint(6, 12)
            if institution == "SU01" and ts >= C_FROM:
                subscriber_len = rng.randint(10, 12)  # C dışındaki İSKİ talimatları eski numaralı müşterilerden
        fields = self.fields_for(screen, action, customer, institution, subscriber_len)
        roll = rng.random()

        # B dışında gece bakım penceresinde Başkentgaz zaman aşımları
        if screen == "ODMTTLMT" and institution == "GAZ02" and 2 <= ts.hour < 4 and action.name == "AboneDogrula":
            return self.institution_timeout(ts, action, channel, customer, "GAZ02", fields)

        if roll < TECHNICAL_RATE:
            if screen == "ODMTTLMT" and action.name == "AboneDogrula" and rng.random() < 0.4:
                timeout_inst = rng.choice([c for c in sorted(self.institutions) if c != "GAZ02"])
                fields["institutionCode"] = timeout_inst
                return self.institution_timeout(ts, action, channel, customer, timeout_inst, fields)
            number = rng.choice(list(TECHNICAL_ERRORS))
            http, msg, in_type, in_msg, in_src = TECHNICAL_ERRORS[number]
            return self.build(
                ts=ts, screen=screen, action=action, channel=channel, customer=customer, level="Error",
                http_status=http, message=f"{screen} {action.name}: {msg}", error_number=number,
                exception=("Fineart.Core.Exceptions.TechnicalException", msg, "Fineart.Core"),
                inner=(in_type, in_msg, in_src), fields=fields,
                response={"success": False, "errorNumber": number, "errorCode": ERROR_CODES[number]},
            )
        if roll < TECHNICAL_RATE + BUSINESS_RATE:
            options = {e[0]: e[2] for e in BUSINESS_ERRORS[screen]}
            number = weighted(options)
            msg = next(e[1] for e in BUSINESS_ERRORS[screen] if e[0] == number)
            return self.build(
                ts=ts, screen=screen, action=action, channel=channel, customer=customer, level="Warning",
                http_status=422, message=f"{screen} {action.name}: {msg}", error_number=number, business=True,
                exception=("Fineart.Core.Exceptions.BusinessException", msg, SCREEN_META[screen][1]),
                fields=fields, response={"success": False, "errorNumber": number, "errorCode": ERROR_CODES[number]},
            )
        message = f"{screen} {action.name} başarıyla tamamlandı."
        if screen == "ODMTTLMT" and action.name == "AboneDogrula":
            message = f"ODMTTLMT AboneDogrula: {institution} abone doğrulaması başarılı ({subscriber_len} hane)."
        return self.build(ts=ts, screen=screen, action=action, channel=channel, customer=customer,
                          message=message, fields=fields)

    def institution_timeout(self, ts, action, channel, customer, institution, fields, **kw) -> dict:
        timeout = self.institutions[institution]["timeout_ms"]
        msg = f"{institution} kurum servisi {timeout} ms içinde yanıt vermedi."
        return self.build(
            ts=ts, screen="ODMTTLMT", action=action, channel=channel, customer=customer, level="Error",
            http_status=504, message=f"ODMTTLMT AboneDogrula: {msg}", error_number=110731,
            exception=("Fineart.Core.Exceptions.IntegrationException", msg, "Fineart.Odeme.Talimat"),
            inner=("System.TimeoutException", f"The operation has timed out after {timeout} ms.",
                   "Fineart.Odeme.Kurum.KurumServisClient"),
            fields=fields, response={"success": False, "errorNumber": 110731, "errorCode": "INSTITUTION_TIMEOUT"},
            **kw,
        )

    # --- senaryolar -----------------------------------------------------------
    def scenario_b(self) -> list[dict]:
        action = ACTIONS["ODMTTLMT"][1]
        ankara = [c for c in self.synthetic if c["city"] == "Ankara"]
        records = []
        for i in range(B_COUNT):
            ts = B_FROM + timedelta(seconds=rng.uniform(0, 29 * 60 + 59))
            channel = rng.choices([1, 2, 4, 3], weights=[55, 15, 20, 10], k=1)[0]
            customer = rng.choice(ankara)
            unit = 601 if channel == 1 else None
            user = "elif" if channel == 1 and i % 4 == 0 else None
            fields = {"institutionCode": "GAZ02", "billType": "Doğalgaz", "subscriberNoLength": rng.randint(8, 10)}
            records.append(self.institution_timeout(ts, action, channel, customer, "GAZ02", fields,
                                                    unit_id=unit, user_name=user))
        return records

    def scenario_c(self) -> list[dict]:
        action = ACTIONS["ODMTTLMT"][1]
        records = []
        plan = [("SU01", 13)] * C_ISKI_COUNT + [("SU02", 5)] * C_OTHER_COUNT
        istanbul = [c for c in self.synthetic if c["city"] == "İstanbul"]
        ankara = [c for c in self.synthetic if c["city"] == "Ankara"]
        for institution, length in plan:
            channel = weighted(CHANNEL_WEIGHTS["ODMTTLMT"])
            ts = random_time(C_FROM, B_FROM, channel)
            customer = rng.choice(istanbul if institution == "SU01" else ankara)
            name = self.institutions[institution]["name"]
            msg = f"Abone numarası {length} hane; ekran 6–12 hane kabul ediyor."
            records.append(self.build(
                ts=ts, screen="ODMTTLMT", action=action, channel=channel, customer=customer, level="Warning",
                http_status=422, message=f"ODMTTLMT AboneDogrula: {institution} ({name}) {msg}",
                error_number=110412, business=True,
                exception=("Fineart.Core.Exceptions.BusinessException", msg, "Fineart.Odeme.Talimat"),
                fields={"institutionCode": institution, "billType": "Su", "subscriberNoLength": length},
                response={"success": False, "errorNumber": 110412, "errorCode": "SUBSCRIBER_NO_INVALID"},
            ))
        return records

    def scenario_e(self, changes: list[dict]) -> list[dict]:
        action = ACTIONS["MUSTGUNC"][1]
        records = []
        for change in changes:
            customer = self.by_no[change["customer_number"]]
            day = datetime.fromisoformat(change["changed_at"]).replace(tzinfo=TZ)
            channel = rng.choice([1, 2, 4])
            ts = random_time(day, min(day + timedelta(days=1), B_FROM), channel)
            records.append(self.build(
                ts=ts, screen="MUSTGUNC", action=action, channel=channel, customer=customer,
                message="MUSTGUNC MusteriGuncelle: adres bilgisi güncellendi (il değişikliği).",
                fields={"section": "adres", "cityChanged": True},
            ))
        return records

    def phone_errors(self) -> list[dict]:
        action = ACTIONS["MUSTGUNC"][1]
        records = []
        for _ in range(PHONE_ERROR_COUNT):
            channel = weighted(CHANNEL_WEIGHTS["MUSTGUNC"])
            ts = random_time(datetime(2026, 9, 20, tzinfo=TZ), B_FROM, channel)
            msg = "Input string was not in a correct format."
            records.append(self.build(
                ts=ts, screen="MUSTGUNC", action=action, channel=channel, customer=rng.choice(self.synthetic),
                level="Error", http_status=500,
                message="MUSTGUNC MusteriGuncelle: beklenmeyen hata; telefon numarası alanı çözümlenemedi.",
                exception=("System.FormatException", msg, "System.Private.CoreLib"),
                fields={"section": "iletisim", "field": "phone"},
                response={"success": False},
                mercek_error_number=PHONE_ERROR_NUMBER,
            ))
        return records


# ---------------------------------------------------------------------------
# Çalıştırma
# ---------------------------------------------------------------------------


def stats(records: list[dict]) -> dict:
    def count(pred):
        return sum(1 for r in records if pred(r))

    c_after = [r for r in records if r["app_exception_value"] == 110412 and r["log_time"] >= "2026-10-01"]
    c_iski = [r for r in c_after if '"SU01"' in r["message_fields"]]
    return {
        "total": len(records),
        "period": [records[0]["log_time"], records[-1]["log_time"]],
        "levels": dict(Counter(r["log_level"] for r in records)),
        "screens": dict(Counter(r["screen_id"] for r in records).most_common()),
        "channels": dict(sorted(Counter(r["channel_id"] for r in records).items())),
        "B_gaz02_timeout_last_30_min": count(lambda r: r["app_exception_value"] == 110731
                                             and '"GAZ02"' in r["message_fields"]
                                             and r["log_time"] >= "2026-10-17T08:30"),
        "C_110412_before_10_01": count(lambda r: r["app_exception_value"] == 110412 and r["log_time"] < "2026-10-01"),
        "C_110412_after_10_01": len(c_after),
        "C_iski_share_pct": round(100 * len(c_iski) / len(c_after), 1),
        "C_iski_all_13_digits": all('"subscriberNoLength": 13' in r["message_fields"] for r in c_iski),
        "E_address_changes": count(lambda r: '"cityChanged": true' in r["message_fields"]),
        "phone_errors_without_rule": count(lambda r: r["mercek_assigned_error_number"] == PHONE_ERROR_NUMBER),
        "D_krdttahs_insufficient_balance": count(lambda r: r["app_exception_value"] == 120640),
        "error_numbers": dict(Counter(r["app_exception_value"] for r in records if r["app_exception_value"]).most_common()),
    }


def main() -> None:
    factory = LogFactory()
    changes = load("customers.stats.json")["E"]["address_changes"]
    records = [factory.daily() for _ in range(DAILY_COUNT)]
    records += factory.scenario_b() + factory.scenario_c() + factory.scenario_e(changes) + factory.phone_errors()
    records.sort(key=lambda r: r["timestamp"])
    for i, record in enumerate(records, start=1):
        record["log_id"] = i
    assert all(r["timestamp"] < iso_utc(END) for r in records)

    (DATA / "kibana_logs.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summary = stats(records)
    (DATA / "kibana_logs.stats.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in summary.items() if k != "error_numbers"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
