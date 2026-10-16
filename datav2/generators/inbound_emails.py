"""inbound_emails.json üreticisi (dış paydaş ortak posta kutusu, 35 e-posta).

- 18 kurum duyurusu: işlenmiş, announcements'a bağlı (eski data/seed/announcements.json metinleri).
- İSKİ 12.09 (13 hane) ve 26.09 hatırlatması: işlenmemiş → C'nin kök nedeni.
- ASKİ 05.10 (Ocak 2027'de 13 hane): işlenmemiş → G.
- 14 diğer: otomatik yanıt, mutabakat, toplantı, yanlış adres, bülten, test, oltalama, KVKK bulgulu müşteri e-postası.
- mercek_assigned_* alanları boş: Mercek e-posta taramasını demoda yapar.
Adresler kurgusaldır (`*.ornek.test`); gerçek alan adı, kişi ya da bağlantı yoktur.

Çalıştırma (repo kökünden):  python datav2/generators/inbound_emails.py
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "datav2"
SRC_ANNOUNCEMENTS = ROOT / "data" / "seed" / "announcements.json"

SEED = 42
TZ = timezone(timedelta(hours=3))
MAILBOX = "dis-paydas-duyuru@fineart.ornek.test"
TEAM = "FATURA_ODEME"
UNPROCESSED_ANNOUNCEMENTS = {"DUY-0412": "SU01", "DUY-0419": "SU02"}  # C ve G: ann_id bu kayıtlarda oluşmaz

rng = random.Random(SEED)

DOMAINS = {
    "ELK01": "ck-bogazici", "ELK02": "enerjisa-baskent", "ELK03": "gediz", "SU01": "iski", "SU02": "aski",
    "SU03": "izsu", "GAZ01": "igdas", "GAZ02": "baskentgaz", "GAZ03": "izmirgaz", "INT01": "turktelekom",
    "INT02": "superonline", "INT03": "turknet", "GSM01": "turkcell", "GSM02": "vodafone",
    "GSM03": "turktelekom-mobil", "VRG01": "gelir-idaresi",
}
ATTACHMENTS = {
    "DUY-0371": ["odeme_yaniti_alan_listesi.pdf"], "DUY-0387": ["yeni_servis_adresi.pdf"],
    "DUY-0401": ["sorgu_yaniti_v3.pdf"], "DUY-0402": ["hata_kodlari_listesi.xlsx"],
    "DUY-0412": ["abone_numaralandirma_teknik_not.pdf"], "DUY-0414": ["kimlik_dogrulama_entegrasyon.pdf"],
    "DUY-0419": ["abone_no_13_hane_gecis_plani.pdf"],
}

OTHER_EMAILS = [
    # (received_at, code|None, from_local, from_display, subject, body, attachments, status, team)
    ("2026-07-21T09:12:00", "ELK03", "operasyon", "Gediz Elektrik Operasyon",
     "Otomatik yanıt: Ofis dışındayım",
     "28 Temmuz'a kadar izindeyim. Acil konular için kurum operasyon hattına yazabilirsiniz.",
     [], "yok_sayildi", None),
    ("2026-08-04T14:30:00", "GSM01", "entegrasyon", "Turkcell Entegrasyon Ekibi",
     "Test ortamı çalışmaları hakkında teşekkür",
     "Geçen hafta tamamlanan test ortamı çalışmalarındaki desteğiniz için teşekkür ederiz.",
     [], "yok_sayildi", None),
    ("2026-08-05T10:05:00", "ELK02", "mutabakat", "Enerjisa Başkent Mutabakat",
     "Temmuz 2026 tahsilat mutabakat raporu",
     "Temmuz 2026 dönemine ait tahsilat mutabakat raporu ektedir. Fark bulunmamaktadır.",
     ["mutabakat_2026_07.xlsx"], "islendi", TEAM),
    ("2026-08-12T16:40:00", None, "bulten", "Ödeme Sistemleri Bülteni",
     "Ağustos sayısı: Anlık ödemelerde yeni dönem",
     "Bültenimizin bu sayısında anlık ödeme altyapılarındaki gelişmeleri derledik. Abonelikten çıkmak için yanıtlayınız.",
     [], "yok_sayildi", None),
    ("2026-08-26T11:20:00", "SU03", "entegrasyon", "İZSU Entegrasyon Birimi",
     "Toplantı daveti: Ödeme kanalları saat sınırlaması",
     "Ödeme kanallarındaki saat sınırlamasının kaldırılması için 3 Eylül 10:00'da çevrim içi bir toplantı planladık.",
     ["toplanti_daveti.ics"], "islendi", TEAM),
    ("2026-09-02T09:48:00", None, "mailer-daemon", "Mail Delivery System",
     "Teslim edilemedi: Ödeme bildirimi",
     "İletiniz alıcıya teslim edilemedi. Alıcı adresi bulunamadı.",
     [], "yok_sayildi", None),
    ("2026-09-04T10:15:00", "GAZ01", "mutabakat", "İGDAŞ Mutabakat",
     "Ağustos 2026 tahsilat mutabakat raporu",
     "Ağustos 2026 dönemine ait mutabakat raporu ektedir. İki işlemde tutar farkı incelenmektedir.",
     ["mutabakat_2026_08.xlsx"], "islendi", TEAM),
    ("2026-09-09T13:02:00", "INT03", "test", "Turknet Test",
     "Test mesajı, lütfen dikkate almayınız",
     "Bu bir test mesajıdır.",
     [], "yok_sayildi", None),
    ("2026-09-15T15:27:00", None, "kurumsal", "Örnek Katılım Bankası Ödeme Birimi",
     "Talimat dosyası (yanlış adres)",
     "Merhaba, bu hafta gönderilecek talimat dosyası ektedir. İyi çalışmalar.",
     ["talimat_dosyasi.txt"], "yok_sayildi", None),
    ("2026-09-22T10:44:00", "INT02", "entegrasyon", "Superonline Entegrasyon",
     "Entegrasyon sorumlusu değişikliği",
     "1 Ekim 2026 itibarıyla kurum entegrasyon sorumlumuz değişmektedir. Teknik yazışmalarınızı entegrasyon adresimize yapabilirsiniz.",
     [], "islendi", TEAM),
    ("2026-09-26T09:30:00", "SU01", "entegrasyon", "İSKİ Entegrasyon Birimi",
     "Hatırlatma: 1 Ekim'de 13 haneli abone numaralarına geçiş",
     "Sayın paydaşlarımız, 12 Eylül tarihli duyurumuzu hatırlatırız. 1 Ekim 2026'dan itibaren yeni abonelerimize 13 haneli "
     "abone numarası verilecektir. Sistemlerinizin hazır olup olmadığını teyit etmenizi rica ederiz.",
     [], "yeni", None),
    ("2026-10-03T08:55:00", None, "guvenlik-bildirim", "Fineart Güvenlik (!)",
     "Acil: Hesabınız askıya alınacak",
     "Posta kutunuzun doğrulaması gerekiyor. 24 saat içinde http://fineart-giris.ornek.test/dogrula adresinden giriş "
     "yapmazsanız hesabınız askıya alınacaktır.",
     [], "yok_sayildi", None),
    ("2026-10-06T14:12:00", None, "selin.karaca.84", "Selin Karaca",
     "Ekstrem gelmiyor",
     "Merhaba, ben Selin Karaca. İki aydır kredi kartı ekstrem gelmiyor. 0532 000 47 18 numaralı telefondan bana "
     "ulaşabilir misiniz?",
     [], "yok_sayildi", None),
    ("2026-10-09T10:20:00", "ELK03", "anket", "Gediz Elektrik Paydaş İlişkileri",
     "Paydaş memnuniyet anketi",
     "Kurumlar arası iş birliğimizi değerlendirmek için kısa anketimize katılımınızı rica ederiz.",
     [], "yok_sayildi", None),
]


def ts(value: str) -> str:
    return datetime.fromisoformat(value).replace(tzinfo=TZ).isoformat()


def address(code: str | None, local: str) -> str:
    return f"{local}@{DOMAINS[code]}.ornek.test" if code else f"{local}@posta.ornek.test"


def processor() -> str:
    return f"g9004u{rng.randint(1, 8):02d}"


def announcement_emails(institutions: dict[str, dict]) -> list[dict]:
    by_name = {i["name"]: code for code, i in institutions.items()}
    emails = []
    for ann in json.loads(SRC_ANNOUNCEMENTS.read_text(encoding="utf-8")):
        code = by_name[ann["institution"]]
        received = datetime.fromisoformat(ann["published_at"]).replace(
            hour=rng.randint(9, 16), minute=rng.randint(0, 59), tzinfo=TZ)
        unprocessed = ann["ann_id"] in UNPROCESSED_ANNOUNCEMENTS
        processed_at = received + timedelta(days=rng.randint(1, 3), hours=rng.randint(0, 5))
        emails.append({
            "received_at": received.isoformat(),
            "from_address": address(code, "duyuru" if code != "SU01" else "entegrasyon"),
            "from_display": f"{institutions[code]['name']} {'Entegrasyon Birimi' if code == 'SU01' else 'Kurumsal İletişim'}",
            "subject": ann["title"],
            "body_text": ann["body"],
            "attachments_json": json.dumps(ATTACHMENTS.get(ann["ann_id"], []), ensure_ascii=False),
            "assigned_team": None if unprocessed else TEAM,
            "processing_status": "yeni" if unprocessed else "islendi",
            "processed_by": None if unprocessed else processor(),
            "processed_at": None if unprocessed else processed_at.isoformat(),
            "linked_announcement_id": None if unprocessed else ann["ann_id"],
        })
    return emails


def other_emails() -> list[dict]:
    emails = []
    for received, code, local, display, subject, body, attachments, status, team in OTHER_EMAILS:
        done = status in ("islendi", "yok_sayildi")
        processed_at = datetime.fromisoformat(received).replace(tzinfo=TZ) + timedelta(hours=rng.randint(2, 30))
        emails.append({
            "received_at": ts(received),
            "from_address": address(code, local),
            "from_display": display,
            "subject": subject,
            "body_text": body,
            "attachments_json": json.dumps(attachments, ensure_ascii=False),
            "assigned_team": team,
            "processing_status": status,
            "processed_by": processor() if done else None,
            "processed_at": processed_at.isoformat() if done else None,
            "linked_announcement_id": None,
        })
    return emails


def main() -> None:
    institutions = {i["institution_code"]: i for i in json.loads((DATA / "institutions.json").read_text(encoding="utf-8"))}
    emails = announcement_emails(institutions) + other_emails()
    emails.sort(key=lambda e: e["received_at"])
    records = []
    for n, email in enumerate(emails, start=1):
        records.append({
            "email_id": f"EML-{n:04d}",
            "mailbox": MAILBOX,
            **{k: email[k] for k in ("received_at", "from_address", "from_display", "subject", "body_text",
                                     "attachments_json", "assigned_team", "processing_status", "processed_by",
                                     "processed_at")},
            "mercek_assigned_type": None,
            "mercek_assigned_confidence": None,
            "mercek_assigned_institution_code": None,
            "mercek_assigned_summary": None,
            "linked_announcement_id": email["linked_announcement_id"],
        })
    (DATA / "inbound_emails.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for r in records:
        print(r["email_id"], r["received_at"][:10], r["processing_status"].ljust(11),
              (r["linked_announcement_id"] or "").ljust(8), r["from_display"][:28].ljust(28), "|", r["subject"][:55])


if __name__ == "__main__":
    main()
