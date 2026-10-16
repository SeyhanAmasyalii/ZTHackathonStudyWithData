"""announcements.json üreticisi (18 geçmiş duyuru, hepsi insan tarafından işlenmiş).

Şema kararı (16.10): `mercek_assigned_` öneki kaldırıldı; kaydı kimin oluşturduğu `source` (insan/mercek)
kolonunda. Geçmiş 18 duyuru `source=insan`, `status=onayli`. İSKİ (C) ve ASKİ (G, DUY-0419) duyuruları
dosyada yok; demoda Mercek `source=mercek`, `status=onerildi` olarak ekler.

Talep bağlantıları (demands adımında oluşturulur):
- DUY-0371, DUY-0408, DUY-0414 → TLP-1033, TLP-1034, TLP-1035 (tamamlandı)
- DUY-0415 → TLP-1023 (takvimdeki "Kurum entegrasyon bakımı", FATURA_ODEME 19–23.10, planlı)

Çalıştırma (repo kökünden):  python datav2/generators/announcements.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "datav2"
SRC = ROOT / "data" / "seed" / "announcements.json"

# ann_id -> (özet, etki, talep)
DETAILS = {
    "DUY-0371": ("Ödeme yanıtlarına kurum işlem referans numarası ekleniyor; dekont ve mutabakatta kullanılmalı.", "orta", "TLP-1033"),
    "DUY-0376": ("25–26 Temmuz hafta sonu bakım; bakım süresince fatura sorgu ve ödeme yapılamaz.", "dusuk", None),
    "DUY-0383": ("15 Ağustos'tan itibaren kısmi ödeme kabul ediliyor; talimatlar tam tutarla çalışmaya devam eder.", "yok", None),
    "DUY-0387": ("1 Eylül'den itibaren fatura sorgu servisi yeni adreste; entegrasyon parametresi güncellenmeli.", "dusuk", None),
    "DUY-0390": ("Fatura kesim dönemlerinde değişiklik yok; bilgilendirme.", "yok", None),
    "DUY-0393": ("Ödeme bildiriminin hizmete yansıma süresi 15 dakikaya iniyor; bankada değişiklik gerekmez.", "yok", None),
    "DUY-0398": ("1 Eylül'den itibaren her gece 02:00–04:00 bakım; bu saatlerde kurum servisi yanıt vermeyebilir.", "dusuk", None),
    "DUY-0401": ("Sorgu yanıtına isteğe bağlı dönem kodu alanı ekleniyor; mevcut entegrasyon etkilenmez.", "dusuk", None),
    "DUY-0402": ("15 Eylül'den itibaren ayrıntılı hata kodları dönecek; hata eşlemesi gözden geçirilmeli.", "dusuk", None),
    "DUY-0405": ("Ödeme bildirim formatında değişiklik yok; bilgilendirme.", "yok", None),
    "DUY-0406": ("Planlı su kesintileri kurum portalında duyurulacak; ödeme entegrasyonunu etkilemez.", "yok", None),
    "DUY-0408": ("1 Ekim'den itibaren kurumsal hat faturaları ayrı fatura türü koduyla gelecek; talimat ekranında desteklenmeli.", "orta", "TLP-1034"),
    "DUY-0410": ("Fatura sorgu yanıt süreleri ortalama %30 kısaldı; bilgilendirme.", "yok", None),
    "DUY-0414": ("1 Ekim'den itibaren vergi ödeme isteklerinde kurum kimlik doğrulaması zorunlu.", "orta", "TLP-1035"),
    "DUY-0415": ("1 Kasım'dan itibaren ödemeler günün her saatinde kabul edilecek; talimat saat kısıtı kaldırılmalı.", "orta", "TLP-1023"),
    "DUY-0417": ("Sorgu servisi sertifikası 26 Eylül'de yenilendi; sertifika sabitleme yapan kurumlar güncellemeli.", "dusuk", None),
    "DUY-0418": ("15 Ekim'den itibaren sorgu yanıtına isteğe bağlı son ödeme saati alanı ekleniyor.", "yok", None),
    "DUY-0421": ("Ay sonunda kampanya kaynaklı ödeme yoğunluğu bekleniyor; zaman aşımı değerleri gözden geçirilmeli.", "yok", None),
}


def load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def main() -> None:
    source = {a["ann_id"]: a for a in json.loads(SRC.read_text(encoding="utf-8"))}
    institutions = {i["name"]: i["institution_code"] for i in load("institutions.json")}
    emails = {e["linked_announcement_id"]: e for e in load("inbound_emails.json") if e["linked_announcement_id"]}
    assert set(emails) == set(DETAILS), set(emails) ^ set(DETAILS)

    records = []
    for ann_id, (summary, impact, demand) in DETAILS.items():
        ann, email = source[ann_id], emails[ann_id]
        records.append({
            "ann_id": ann_id,
            "source_email_id": email["email_id"],
            "source": "insan",
            "institution_code": institutions[ann["institution"]],
            "published_at": ann["published_at"],
            "effective_at": ann["effective_at"],
            "title": ann["title"],
            "summary": summary,
            "screens_json": json.dumps(["ODMTTLMT"]),
            "departments_json": json.dumps(["FATURA_ODEME"]),
            "impact": impact,
            "proposed_demand_id": demand,
            "status": "onayli",
            "approved_by": email["processed_by"],
            "approved_at": email["processed_at"],
        })
    (DATA / "announcements.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for r in records:
        print(r["ann_id"], r["source_email_id"], r["institution_code"].ljust(5), r["impact"].ljust(6),
              (r["proposed_demand_id"] or "").ljust(8), r["title"][:50])


if __name__ == "__main__":
    main()
