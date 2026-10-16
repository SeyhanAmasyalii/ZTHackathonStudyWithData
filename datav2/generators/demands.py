"""demands.json üreticisi (eski requests'in yerine).

İçerik (116 kayıt):
- 95 geçmiş talep (eski numaralar TLP-0503…TLP-1032, tamamlandı). Tarih, tür, bileşen, efor, talep eden
  birim ve analist korunur. 87 genel talebin başlığı 9 ekranlık kataloğa göre yeniden yazılır; kredi
  tarafında "hatırlatma" ve "erteleme" bilerek geçmez (D ve E'nin yeniliği). 8 özel talep (D'nin 5, E'nin 3
  referansı) metniyle korunur, yalnızca ekran ve departmanı uyarlanır.
- 11 takvim talebi TLP-1021…TLP-1031 (planlı), catalog.service_calendar sırasıyla. TLP-1023 = İZSU
  duyurusu (DUY-0415). KART_BASVURU → KART_YONETIM; FAST işi (ODEME_SISTEMLERI) → HESAP_YONETIM %30.
- 3 duyuru talebi TLP-1033…TLP-1035 (tamamlandı): DUY-0371, DUY-0408, DUY-0414.
- 7 bekleyen talep TLP-1036…TLP-1042 (analiz / oneri / iptal).
- D (TLP-1043), E (TLP-1044), G (TLP-1045) dosyada yok; demoda oluşur.
Efor yalnızca adam-gün; planlanan, gerçekleşenin %10–15 altında; bitmemişte gerçekleşen boş.
Mercek alanları boş (Mercek yoktu).

Çalıştırma (repo kökünden):  python datav2/generators/demands.py
"""

from __future__ import annotations

import csv
import json
import math
import random
import re
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "datav2"
SRC_REQUESTS = ROOT / "data" / "out" / "requests.csv"
SRC_CATALOG = ROOT / "data" / "seed" / "catalog.json"

SEED = 42
TODAY = date(2026, 10, 17)
rng = random.Random(SEED)

DEPARTMENT_ALIAS = {"KART_BASVURU": "KART_YONETIM", "ODEME_SISTEMLERI": "HESAP_YONETIM"}
UNIT_IDS = {"Kredi Tahsilatları": 9001, "Bireysel Krediler": 9002, "Kart Ürünleri": 9003, "Ödeme Sistemleri": 9004,
            "Şube Operasyonları": 9005, "Dijital Bankacılık": 9006, "Müşteri Deneyimi": 9007,
            "Uyum ve İç Kontrol": 9008}
DEPARTMENT_UNIT = {"KREDI_TAKIP": 9001, "KREDI_KULLANDIRIM": 9002, "KART_YONETIM": 9003, "FATURA_ODEME": 9004,
                   "HESAP_YONETIM": 9005, "MUSTERI_YONETIM": 9007}
# Genel geçmiş taleplerde talep eden birim, ana departmanın iş birimidir
DEMANDER_UNITS = {"KREDI_TAKIP": [9001], "KREDI_KULLANDIRIM": [9002], "KART_YONETIM": [9003],
                  "FATURA_ODEME": [9004], "HESAP_YONETIM": [9005, 9006], "MUSTERI_YONETIM": [9007, 9008]}
FORBIDDEN = re.compile(r"hatırlatma|erteleme|ertelen", re.IGNORECASE)

# Özel talepler: metin korunur, ekran ve departman uyarlanır
FIXED = {
    "TLP-0871": (["KRTTGUNC"], {"KART_YONETIM": 12, "MUSTERI_YONETIM": 2}),
    "TLP-0915": (["ODMTTLMT"], {"FATURA_ODEME": 9, "MUSTERI_YONETIM": 2}),
    "TLP-0962": ([], {"HESAP_YONETIM": 8, "MUSTERI_YONETIM": 1}),       # vadeli hesap ekranı katalogda yok
    "TLP-1004": (["KRTTGUNC"], {"KART_YONETIM": 5, "MUSTERI_YONETIM": 1}),
    "TLP-1019": ([], {"HESAP_YONETIM": 6, "MUSTERI_YONETIM": 2}),       # hesap hareketleri ekranı katalogda yok
    "TLP-0588": ([], {"KREDI_TAKIP": 8, "KREDI_KULLANDIRIM": 3, "MUSTERI_YONETIM": 4}),
    "TLP-0712": ([], {"KART_YONETIM": 9, "MUSTERI_YONETIM": 4}),
    "TLP-0846": ([], {"KREDI_TAKIP": 13, "KREDI_KULLANDIRIM": 4}),
}

# Departman -> [(ekran, tür, başlık)]
TITLE_POOLS = {
    "HESAP_YONETIM": [
        ("HSPTVDSZ", "existing_change", "Vadesiz hesap açılışında döviz cinsi listesine yeni para birimleri eklensin"),
        ("HSPTVDSZ", "existing_change", "Hesap açılışında şube seçimi müşterinin adresine göre önerilsin"),
        ("HSPTVDSZ", "existing_change", "Hesap açılışındaki sözleşme onayları tek adımda toplansın"),
        ("HSPTVDSZ", "existing_change", "IBAN gösterim adımına kopyalama ve paylaşma seçeneği eklensin"),
        ("HSPTVDSZ", "existing_change", "Hesap açılışında müşteri segmentine göre varsayılan ürün gelsin"),
        ("HSPTVDSZ", "existing_change", "Döviz hesabı açılışında kaynak beyanı alanı zorunlu olsun"),
        ("HSPTVDSZ", "existing_change", "Hesap açılış ekranında eksik alan uyarıları alan bazında gösterilsin"),
        ("HSPTVDSZ", "existing_change", "Hesap açılışında ortak hesap sahibi eklenebilsin"),
        ("PRMTGENL", "existing_change", "Vadesiz hesap ücret parametreleri parametre ekranından yönetilsin"),
        ("PRMTGENL", "existing_change", "Hesap açılış limit parametreleri dört göz onayına bağlansın"),
        ("HSPTVDSZ", "new_screen", "Hesap açılış başvurularını izleme alt ekranı"),
        ("HSPTVDSZ", "new_screen", "Hesap kapama talep alt ekranı"),
        ("HSPTVDSZ", "new_screen", "Ortak hesap yetkilendirme alt ekranı"),
        ("HSPTVDSZ", "batch", "Gün sonunda açılan hesapların uyum raporu"),
        ("HSPTVDSZ", "batch", "Atıl vadesiz hesapların aylık listelenmesi"),
        ("HSPTVDSZ", "batch", "Hesap açılış belgelerinin arşive aktarım işi"),
        ("HSPTVDSZ", "mixed", "Kurumsal maaş müşterileri için toplu hesap açılışı"),
        ("HSPTVDSZ", "mixed", "Döviz hesabı açılışında kur bilgisi ve günlük açılış raporu"),
    ],
    "KART_YONETIM": [
        ("KRTTBASV", "existing_change", "Kart başvurusunda kart tipine göre limit önerisi gösterilsin"),
        ("KRTTBASV", "existing_change", "Kart başvuru formunda meslek listesi güncellensin"),
        ("KRTTBASV", "existing_change", "Başvuru sonucunda red gerekçesi temsilciye ayrıntılı gösterilsin"),
        ("KRTTBASV", "existing_change", "Kart başvurusunda gelir belgesi yükleme adımı eklensin"),
        ("KRTTGUNC", "existing_change", "Hesap kesim günü değişikliği yılda iki kezle sınırlansın"),
        ("KRTTGUNC", "existing_change", "Kart limit değişikliği geçmişi ekranda listelensin"),
        ("KRTTGUNC", "existing_change", "Ekstre tercihi varsayılanı müşteri profiline göre gelsin"),
        ("KRTTGUNC", "existing_change", "Otomatik ödeme talimatı kart güncelleme ekranından tanımlanabilsin"),
        ("KRTTGUNC", "existing_change", "Kart güncelleme özet adımında değişen alanlar vurgulansın"),
        ("KRTTBASV", "new_screen", "Ek kart başvuru alt ekranı"),
        ("KRTTGUNC", "new_screen", "Sanal kart limit ayarı alt ekranı"),
        ("KRTTGUNC", "new_screen", "Kart kapama talep alt ekranı"),
        ("KRTTBASV", "batch", "Onaylanan kart başvurularının basım dosyası işi"),
        ("KRTTGUNC", "batch", "Limit artış önerilerinin aylık hesaplanması"),
        ("KRTTBASV", "mixed", "Kart başvurusunda kampanya kodu ve kampanya raporu"),
    ],
    "FATURA_ODEME": [
        ("ODMTTLMT", "existing_change", "Talimat ekranında kurum listesi fatura türüne göre filtrelensin"),
        ("ODMTTLMT", "existing_change", "Talimat üst limiti aşıldığında temsilciye uyarı gösterilsin"),
        ("ODMTTLMT", "existing_change", "Talimat başlangıç tarihi geçmiş tarihli seçilemesin"),
        ("ODMTTLMT", "existing_change", "Kurum yanıt kodları talimat ekranında açıklamalı gösterilsin"),
        ("ODMTTLMT", "existing_change", "Talimat onay adımına bildirim tercihi özeti eklensin"),
        ("ODMTTLMT", "existing_change", "Talimat ödeme hesabı seçiminde kullanılabilir bakiye gösterilsin"),
        ("PRMTGENL", "existing_change", "Kurum zaman aşımı süreleri parametre ekranından yönetilsin"),
        ("PRMTGENL", "existing_change", "Kurum bazlı talimat üst limiti parametreye taşınsın"),
        ("ODMTTLMT", "new_screen", "Talimat geçmişi alt ekranı"),
        ("ODMTTLMT", "new_screen", "Toplu talimat iptal alt ekranı"),
        ("ODMTTLMT", "batch", "Gece talimat ödeme işi"),
        ("ODMTTLMT", "batch", "Kurum mutabakat dosyası karşılaştırma işi"),
        ("ODMTTLMT", "batch", "Başarısız talimat ödemelerinin günlük raporu"),
        ("ODMTTLMT", "mixed", "Yeni kurum entegrasyonu ve talimat ekranına eklenmesi"),
        ("ODMTTLMT", "mixed", "Talimat kanal raporu ve ekranda kanal filtresi"),
    ],
    "MUSTERI_YONETIM": [
        ("MUSTTANM", "existing_change", "Müşteri tanımlamada KVKK onay metni güncellensin"),
        ("MUSTTANM", "existing_change", "Mükerrer müşteri kontrolü kimlik ve telefonla birlikte yapılsın"),
        ("MUSTTANM", "existing_change", "Meslek ve gelir alanları tanımlamada zorunlu olsun"),
        ("MUSTTANM", "existing_change", "Kimlik doğrulamada yeni kimlik kartı okuyucu desteği"),
        ("MUSTGUNC", "existing_change", "İletişim izinleri tek bölümde yönetilsin"),
        ("MUSTGUNC", "existing_change", "Adres değişikliğinde il ve ilçe listesi güncellensin"),
        ("MUSTGUNC", "existing_change", "Değişiklik özetinde eski ve yeni değer yan yana gösterilsin"),
        ("MUSTGUNC", "existing_change", "Gelir güncellemesinde belge yükleme adımı eklensin"),
        ("MUSTTANM", "new_screen", "Yabancı uyruklu müşteri tanımlama alt ekranı"),
        ("MUSTGUNC", "new_screen", "Müşteri bilgi değişiklik geçmişi alt ekranı"),
        ("MUSTGUNC", "batch", "İletişim izni değişikliklerinin günlük uyum raporu"),
        ("MUSTGUNC", "batch", "Eksik müşteri bilgisi tespit işi"),
        ("MUSTGUNC", "mixed", "Adres doğrulama servisi entegrasyonu ve ekrana eklenmesi"),
    ],
    "KREDI_KULLANDIRIM": [
        ("KRDTKULL", "existing_change", "Ödeme planı çıktısına yıllık maliyet oranı eklensin"),
        ("KRDTKULL", "existing_change", "Uygunluk kontrolünde red gerekçesi ayrıntılı gösterilsin"),
        ("KRDTKULL", "existing_change", "Vade seçenekleri ürüne göre listelensin"),
        ("KRDTKULL", "existing_change", "Alacak hesabı seçiminde yalnızca TL hesaplar listelensin"),
        ("KRDTKULL", "existing_change", "Uygunluk kontrolünde ek gelir beyanı alanı eklensin"),
        ("KRDTKULL", "existing_change", "Yüksek tutarlı kullandırımlara dört göz onayı eklensin"),
        ("PRMTGENL", "existing_change", "Kredi ürün faiz oranları parametre ekranından yönetilsin"),
        ("PRMTGENL", "existing_change", "Taksit / gelir oranı eşiği parametreye taşınsın"),
        ("KRDTKULL", "new_screen", "Kredi teklif karşılaştırma alt ekranı"),
        ("KRDTKULL", "batch", "Günlük kredi kullandırım raporu"),
        ("KRDTKULL", "batch", "Ön onaylı kredi listesi hesaplama işi"),
        ("KRDTKULL", "mixed", "Kampanyalı kredi ürünü tanımı ve kullandırım ekranı uyarlaması"),
    ],
    "KREDI_TAKIP": [
        ("KRDTTAHS", "existing_change", "Taksit listesinde gecikme gün sayısı gösterilsin"),
        ("KRDTTAHS", "existing_change", "Gecikme faizi hesap detayı dekonta eklensin"),
        ("KRDTTAHS", "existing_change", "Birden çok taksit tek işlemde tahsil edilebilsin"),
        ("PRMTGENL", "existing_change", "Gecikme faizi oranı parametre ekranından yönetilsin"),
        ("KRDTTAHS", "batch", "Gecikmedeki taksitler için gece otomatik tahsilat işi"),
        ("KRDTTAHS", "batch", "Tahsilat günlük mutabakat raporu"),
    ],
}

# Takvim talepleri (catalog.service_calendar sırasıyla TLP-1021…)
CALENDAR_DEMANDS = [
    ("Yıl sonu regülasyon işi: tahsilat ve gecikme faizi raporlamasının güncellenmesi", "existing_change", ["KRDTTAHS", "PRMTGENL"], "manuel"),
    ("Kampanya parametrelerinin yıl sonu kampanyasına göre güncellenmesi", "existing_change", ["PRMTGENL"], "manuel"),
    ("İZSU ödeme saati kısıtının kaldırılması ve kurum entegrasyon bakımı", "existing_change", ["ODMTTLMT"], "manuel"),
    ("Yıl sonu kapanış desteği (tahsilat)", "batch", ["KRDTTAHS"], "otomatik"),
    ("Kredi skorlama modeli entegrasyonu", "mixed", ["KRDTKULL"], "manuel"),
    ("Adres doğrulama altyapısı güncellemesi", "existing_change", ["MUSTGUNC"], "manuel"),
    ("KVKK izin yönetimi iyileştirmeleri", "existing_change", ["MUSTGUNC", "MUSTTANM"], "manuel"),
    ("Yeni kurum entegrasyonları (3 kurum)", "mixed", ["ODMTTLMT"], "manuel"),
    ("Hesap hareketleri performans iyileştirmesi", "existing_change", [], "manuel"),
    ("Sanal kart projesi", "new_screen", ["KRTTBASV"], "yeni ekran"),
    ("FAST entegrasyon güncellemesi", "mixed", [], "manuel"),
]
CALENDAR_ALLOCATION_OVERRIDE = {10: 30}  # FAST: HESAP_YONETIM %70 ile birlikte %100'ü aşmasın

ANNOUNCEMENT_DEMANDS = {
    "TLP-1033": ("DUY-0371", "Ödeme yanıtındaki kurum işlem referans numarasının dekont ve mutabakata eklenmesi", 5),
    "TLP-1034": ("DUY-0408", "Kurumsal hat faturaları için ayrı fatura türünün talimat ekranında desteklenmesi", 6),
    "TLP-1035": ("DUY-0414", "Vergi ödeme isteklerine kurum kimlik doğrulamasının eklenmesi", 7),
}

PENDING = [
    ("TLP-1036", "2026-09-21", 9003, "analiz", "Kart başvurusunda gelir doğrulamasının elektronik belgeyle yapılması",
     "existing_change", ["KRTTBASV"], {"KART_YONETIM": 7, "MUSTERI_YONETIM": 2}),
    ("TLP-1037", "2026-09-25", 9006, "analiz", "Hesap açılışında görüntülü görüşmeyle kimlik doğrulama",
     "mixed", ["HSPTVDSZ", "MUSTTANM"], {"HESAP_YONETIM": 9, "MUSTERI_YONETIM": 6}),
    ("TLP-1038", "2026-09-30", 9007, "oneri", "Müşteri bilgileri güncellemede e-posta doğrulama kodu",
     "existing_change", ["MUSTGUNC"], {"MUSTERI_YONETIM": 0}),
    ("TLP-1039", "2026-10-02", 9002, "analiz", "Kredi kullandırımda hayat sigortası teklif adımı",
     "existing_change", ["KRDTKULL"], {"KREDI_KULLANDIRIM": 8, "MUSTERI_YONETIM": 1}),
    ("TLP-1040", "2026-10-07", 9005, "oneri", "Parametre değişikliklerinde onaycıya e-posta bildirimi",
     "existing_change", ["PRMTGENL"], {"HESAP_YONETIM": 0}),
    ("TLP-1041", "2026-10-09", 9003, "iptal", "Kart ekstresinin posta ile gönderiminin sonlandırılması",
     "batch", ["KRTTGUNC"], {"KART_YONETIM": 0}),
    ("TLP-1042", "2026-10-14", 9004, "oneri", "Talimat ekranından güncel fatura tutarı sorgulama",
     "existing_change", ["ODMTTLMT"], {"FATURA_ODEME": 0}),
]

REASONS = ["Hatalı işlem sayısını azaltmayı hedefliyoruz.", "Operasyon ekibinin iş yükünü azaltmak istiyoruz.",
           "Müşteri şikâyetlerinde bu ihtiyaç sık geçiyor.", "Denetim bulgusu kapsamında gerekiyor.",
           "Raporlama sürecini hızlandırmak istiyoruz."]


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------

def load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def is_workday(d: date) -> bool:
    return d.weekday() < 5


def add_workdays(start: date, days: int) -> date:
    d, left = start, days
    while not is_workday(d):
        d += timedelta(days=1)
    while True:
        if is_workday(d):
            left -= 1
            if left == 0:
                return d
        d += timedelta(days=1)


def workdays_between(a: date, b: date) -> int:
    return sum(1 for n in range((b - a).days + 1) if is_workday(a + timedelta(days=n)))


def scale(efforts: dict[str, int], total: int) -> dict[str, int]:
    """Dağılımı koruyarak toplamı `total`e ölçekler (en büyük kalan yöntemi)."""
    base = sum(efforts.values())
    raw = {k: v * total / base for k, v in efforts.items()}
    out = {k: math.floor(v) for k, v in raw.items()}
    for k in sorted(raw, key=lambda k: raw[k] - out[k], reverse=True)[: total - sum(out.values())]:
        out[k] += 1
    return out


def planned_from_actual(actual: int) -> int:
    return max(1, round(actual * rng.uniform(0.85, 0.90)))


def departments_json(efforts: dict[str, int]) -> str:
    main = max(efforts, key=efforts.get)
    return json.dumps([{"department_id": d, "role": "ana" if d == main else "etkilesimli"} for d in efforts],
                      ensure_ascii=False)


def base_record(demand_id: str, created: str, unit: int, title: str, description: str, status: str, kind: str,
                components: list, screens: list) -> dict:
    return {
        "demand_id": demand_id, "created_at": created, "demander_unit_id": unit, "origin": "business_unit",
        "source_announcement_id": None, "title": title, "description": description, "status": status,
        "type": kind, "components_json": json.dumps(components, ensure_ascii=False),
        "screens_json": json.dumps(screens, ensure_ascii=False), "departments_json": None,
        "planned_effort_md": None, "actual_effort_md": None,
        "planned_component_efforts_json": None, "actual_component_efforts_json": None,
        "planned_department_efforts_json": None, "actual_department_efforts_json": None,
        "decisions": None, "analyst": None, "approved_by": None, "approved_at": None,
        "planned_department_id": None, "planned_from": None, "planned_to": None,
        "mercek_assigned_analysis_json": None, "mercek_suggestions_json": None,
    }


def fill_efforts(rec: dict, actual_by_dept: dict[str, int] | None, planned_by_dept: dict[str, int], kind: str) -> None:
    planned = sum(planned_by_dept.values())
    rec["departments_json"] = departments_json(planned_by_dept if planned else {**planned_by_dept})
    if planned:
        rec["planned_effort_md"] = planned
        rec["planned_component_efforts_json"] = json.dumps({kind: planned}, ensure_ascii=False)
        rec["planned_department_efforts_json"] = json.dumps(planned_by_dept, ensure_ascii=False)
    if actual_by_dept:
        actual = sum(actual_by_dept.values())
        rec["actual_effort_md"] = actual
        rec["actual_component_efforts_json"] = json.dumps({kind: actual}, ensure_ascii=False)
        rec["actual_department_efforts_json"] = json.dumps(actual_by_dept, ensure_ascii=False)


def approve(rec: dict, created: date, unit: int) -> None:
    rec["approved_by"] = f"g{unit}u01"
    rec["approved_at"] = (created + timedelta(days=rng.randint(3, 10))).isoformat()


def schedule_past(rec: dict, created: date, main_dept: str, main_actual: int) -> None:
    start = add_workdays(created + timedelta(days=rng.randint(15, 60)), 1)
    end = add_workdays(start, math.ceil(main_actual * 1.2))
    if end >= TODAY:  # geçmiş talep bugünden önce bitmiş olmalı
        end = add_workdays(TODAY - timedelta(days=rng.randint(20, 40)), 1)
        start = end - timedelta(days=math.ceil(main_actual * 1.2 * 7 / 5))
    rec["planned_department_id"] = main_dept
    rec["planned_from"], rec["planned_to"] = start.isoformat(), end.isoformat()


# ---------------------------------------------------------------------------
# Parçalar
# ---------------------------------------------------------------------------

class TitlePicker:
    def __init__(self) -> None:
        self.used: dict[str, int] = {}

    def pick(self, department: str, kind: str) -> tuple[str, str]:
        pool = TITLE_POOLS[department]
        options = [p for p in pool if p[1] == kind] or pool
        options.sort(key=lambda p: (self.used.get(p[2], 0), rng.random()))
        screen, _, title = options[0]
        count = self.used.get(title, 0)
        self.used[title] = count + 1
        return screen, title if count == 0 else f"{title} ({count + 1}. faz)"


def historical(rows: list[dict]) -> list[dict]:
    picker = TitlePicker()
    records = []
    for row in rows:
        created = date.fromisoformat(row["created_at"])
        unit = UNIT_IDS[row["requester_unit"]]
        kind = row["type"]
        component = json.loads(row["components_json"])[0]["kind"]
        old_efforts = json.loads(row["service_efforts_json"])
        actual_by_dept: dict[str, int] = {}
        for dept, md in old_efforts.items():
            dept = DEPARTMENT_ALIAS.get(dept, dept)
            actual_by_dept[dept] = actual_by_dept.get(dept, 0) + int(md)

        if row["request_id"] in FIXED:
            screens, actual_by_dept = FIXED[row["request_id"]]
            title, description = row["title"], row["description"]
        else:
            main = max(actual_by_dept, key=actual_by_dept.get)
            screen, title = picker.pick(main, kind)
            unit = rng.choice(DEMANDER_UNITS[main])
            screens = [screen]
            reason = row["description"][len(row["title"]):].strip(" .") or rng.choice(REASONS).rstrip(".")
            description = f"{title}. {reason}."
            assert not (main.startswith("KREDI") and FORBIDDEN.search(title)), title

        actual = sum(actual_by_dept.values())
        planned_by_dept = scale(actual_by_dept, planned_from_actual(actual))
        rec = base_record(row["request_id"], row["created_at"], unit, title, description, "tamamlandi", kind,
                          [{"kind": component}], screens)
        fill_efforts(rec, actual_by_dept, planned_by_dept, component)
        rec["decisions"] = row["decisions"] or None
        rec["analyst"] = row["analyst"]
        approve(rec, created, unit)
        main = max(actual_by_dept, key=actual_by_dept.get)
        schedule_past(rec, created, main, actual_by_dept[main])
        records.append(rec)
    return records


def calendar_demands(calendar: list[dict]) -> list[dict]:
    records = []
    for n, (cal, (title, kind, screens, component)) in enumerate(zip(calendar, CALENDAR_DEMANDS)):
        demand_id = f"TLP-{1021 + n}"
        dept = DEPARTMENT_ALIAS.get(cal["service_id"], cal["service_id"])
        pct = CALENDAR_ALLOCATION_OVERRIDE.get(n, cal["allocation_pct"])
        start, end = date.fromisoformat(cal["date_from"]), date.fromisoformat(cal["date_to"])
        planned = max(1, round(workdays_between(start, end) * pct / 100))
        created = start - timedelta(days=rng.randint(25, 50))
        unit = 9006 if title.startswith("FAST") else DEPARTMENT_UNIT[dept]
        rec = base_record(demand_id, created.isoformat(), unit, title, f"{title}. Takvime alınmış planlı iş.",
                          "planli", kind, [{"kind": component}], screens)
        by_dept = {dept: planned}
        if dept != "MUSTERI_YONETIM" and kind in ("mixed", "new_screen"):
            by_dept = scale({dept: 4, "MUSTERI_YONETIM": 1}, planned)
        fill_efforts(rec, None, by_dept, component)
        rec["analyst"] = rng.choice(["Ayşe Kaya", "Selin Kurt", "Burak Tekin"])
        approve(rec, created, unit)
        rec["planned_department_id"] = dept
        rec["planned_from"], rec["planned_to"] = cal["date_from"], cal["date_to"]
        rec["calendar_allocation_pct"] = pct  # department_calendar üretimi için; JSON'a yazılmaz
        if n == 2:
            rec["source_announcement_id"] = "DUY-0415"
        records.append(rec)
    return records


def announcement_demands(announcements: dict[str, dict]) -> list[dict]:
    records = []
    for demand_id, (ann_id, title, actual) in ANNOUNCEMENT_DEMANDS.items():
        ann = announcements[ann_id]
        created = date.fromisoformat(ann["approved_at"][:10]) + timedelta(days=1)
        effective = date.fromisoformat(ann["effective_at"])
        rec = base_record(demand_id, created.isoformat(), 9004, title,
                          f"{title}. Kurum duyurusu ({ann_id}) gereği, geçerlilik tarihinden önce tamamlanmalı.",
                          "tamamlandi", "existing_change", [{"kind": "manuel"}], ["ODMTTLMT"])
        rec["source_announcement_id"] = ann_id
        actual_by_dept = {"FATURA_ODEME": actual}
        fill_efforts(rec, actual_by_dept, {"FATURA_ODEME": planned_from_actual(actual)}, "manuel")
        rec["analyst"] = rng.choice(["Ayşe Kaya", "Selin Kurt", "Burak Tekin"])
        approve(rec, created, 9004)
        end = add_workdays(effective - timedelta(days=6), 1)
        start = end - timedelta(days=math.ceil(actual * 1.2 * 7 / 5))
        rec["planned_department_id"] = "FATURA_ODEME"
        rec["planned_from"], rec["planned_to"] = start.isoformat(), end.isoformat()
        records.append(rec)
    return records


def pending_demands() -> list[dict]:
    records = []
    for demand_id, created, unit, status, title, kind, screens, efforts in PENDING:
        component = "yeni ekran" if kind == "new_screen" else ("otomatik" if kind == "batch" else "manuel")
        rec = base_record(demand_id, created, unit, title, f"{title}. {rng.choice(REASONS)}", status, kind,
                          [{"kind": component}], screens)
        rec["departments_json"] = departments_json({k: max(v, 1) for k, v in efforts.items()})
        if status == "analiz":
            fill_efforts(rec, None, efforts, component)
            rec["analyst"] = rng.choice(["Ayşe Kaya", "Selin Kurt", "Burak Tekin"])
        records.append(rec)
    return records


def main() -> None:
    with SRC_REQUESTS.open(encoding="utf-8") as f:
        rows = sorted(csv.DictReader(f), key=lambda r: r["request_id"])
    catalog = json.loads(SRC_CATALOG.read_text(encoding="utf-8"))
    announcements = {a["ann_id"]: a for a in load("announcements.json")}

    records = (historical(rows) + calendar_demands(catalog["service_calendar"])
               + announcement_demands(announcements) + pending_demands())
    records.sort(key=lambda r: r["demand_id"])
    ids = [r["demand_id"] for r in records]
    assert len(ids) == len(set(ids)), "talep numarası tekrarı"

    calendar_rows = [{"demand_id": r["demand_id"], "department_id": r["planned_department_id"],
                      "date_from": r["planned_from"], "date_to": r["planned_to"],
                      "allocation_pct": r.pop("calendar_allocation_pct")}
                     for r in records if "calendar_allocation_pct" in r]
    (DATA / "demands.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (DATA / "generators" / "_calendar_rows.json").write_text(
        json.dumps(calendar_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    from collections import Counter
    print(len(records), Counter(r["status"] for r in records))
    print(Counter(s for r in records for s in json.loads(r["screens_json"])))
    print(Counter(json.loads(r["departments_json"])[0]["department_id"] for r in records))


if __name__ == "__main__":
    main()
