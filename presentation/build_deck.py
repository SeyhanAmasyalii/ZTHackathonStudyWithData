# Mercek — hackathon sunumu, Ziraat Teknoloji sunum şablonuyla (.pptx, 16:9).
# Çalıştırma: python3 build_deck.py
# Şablon: sablon/ziraat-sunum-sablonu-2025.pptx (logo ve asıl slayt buradan gelir).
# Şablon kuralları: beyaz zemin, Calibri, başlık 32 punto kalın, metin 14-20 punto,
# kırmızı ve gri tonları, sayfada en fazla 5 renk, en fazla 5 madde.
import copy
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

HERE = Path(__file__).parent
TEMPLATE = HERE / "sablon" / "ziraat-sunum-sablonu-2025.pptx"
OUT = HERE / "Mercek_AI_Overflow_Sunum.pptx"
MOCK = HERE / "mockups"
ICON = HERE / "assets" / "icons"
LOGO = HERE / "assets" / "logo"

# Şablondaki renkler
RED, RED2, RED3 = RGBColor(0xE1, 0x05, 0x14), RGBColor(0xB9, 0x0F, 0x0A), RGBColor(0x87, 0x0F, 0x00)
G1, G2, G3 = RGBColor(0xD2, 0xDC, 0xE1), RGBColor(0xB4, 0xBE, 0xC3), RGBColor(0x91, 0x96, 0x9B)
INK, WHITE, SOFT = RGBColor(0x1E, 0x1E, 0x1E), RGBColor(0xFF, 0xFF, 0xFF), RGBColor(0xF2, 0xF5, 0xF6)
FONT = "Calibri"

prs = Presentation(TEMPLATE)
# Şablondaki örnek slaytları kaldır (asıl slayt, düzenler ve logo kalır)
sld_ids = prs.slides._sldIdLst
for sid in list(sld_ids):
    prs.part.drop_rel(sid.get(qn("r:id")))
    sld_ids.remove(sid)
BLANK = next(l for l in prs.slide_layouts if l.name == "Boş")
page = {"n": 0}


# ---------- yardımcılar ----------
def new_slide(title=None, sub=None):
    s = prs.slides.add_slide(BLANK)
    page["n"] += 1
    if title:
        text(s, 0.15, 0.1, 11.0, 0.62, [(title, {"size": 32, "bold": True})])
        wordmark(s, 11.55, 0.17, 0.6)
        if sub:
            text(s, 0.17, 0.72, 12.5, 0.4, [(sub, {"size": 16, "color": G3})])
    if page["n"] > 1:
        text(s, 12.35, 6.98, 0.75, 0.3, [(str(page["n"]), {"size": 11, "color": G3})], align=PP_ALIGN.RIGHT)
    return s


def _run(p, t, o):
    r = p.add_run()
    r.text = t
    f = r.font
    f.name = FONT
    f.size = Pt(o.get("size", 16))
    f.bold = o.get("bold", False)
    f.italic = o.get("italic", False)
    f.color.rgb = o.get("color", INK)


def text(s, x, y, w, h, paras, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, bullets=False, space=4, name=None):
    """paras: list of (text, opts) — her biri bir paragraf; ya da [(t,o),(t,o)] listesi = tek paragrafta birden çok run."""
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        tb.name = name
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for side in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, side, 0)
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space)
        runs = para if isinstance(para, list) else [para]
        for t, o in runs:
            _run(p, t, o)
        if bullets:
            pPr = p._p.get_or_add_pPr()
            pPr.set("marL", "228600")
            pPr.set("indent", "-228600")
            bu_clr = pPr.makeelement(qn("a:buClr"), {})
            srgb = bu_clr.makeelement(qn("a:srgbClr"), {"val": "E10514"})
            bu_clr.append(srgb)
            pPr.append(bu_clr)
            pPr.append(pPr.makeelement(qn("a:buFont"), {"typeface": "Arial"}))
            pPr.append(pPr.makeelement(qn("a:buChar"), {"char": "•"}))
    return tb


def box(s, x, y, w, h, fill=SOFT, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06, name=None):
    sh = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        sh.name = name
    if fill is None:
        sh.fill.background()
    else:
        sh.fill.solid()
        sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line
        sh.line.width = Pt(1.25)
    sh.shadow.inherit = False
    st = sh._element.find(qn("p:style"))
    if st is not None:
        sh._element.remove(st)
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        sh.adjustments[0] = radius
    sh.text_frame.text = ""
    return sh


def circle(s, x, y, d, fill, label=None, size=16, icon=None):
    c = box(s, x, y, d, d, fill=fill, shape=MSO_SHAPE.OVAL)
    if icon:
        p = d * 0.25
        s.shapes.add_picture(str(ICON / icon), Inches(x + p), Inches(y + p), Inches(d - 2 * p), Inches(d - 2 * p))
    if label:
        text(s, x, y, d, d, [(label, {"size": size, "bold": True, "color": WHITE})], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    return c


def pill(s, x, y, w, h, label, fill, color=WHITE, size=11):
    box(s, x, y, w, h, fill=fill, radius=0.5)
    text(s, x, y, w, h, [(label, {"size": size, "bold": True, "color": color})], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


def line(s, x1, y1, x2, y2, color=G3):
    c = s.shapes.add_connector(1, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = color
    c.line.width = Pt(1.75)
    ln = c.line._get_or_add_ln()
    ln.append(ln.makeelement(qn("a:tailEnd"), {"type": "triangle"}))



def wordmark(s, x, y, size=1.0):
    """Köşe logosu: sade mercek + MERCEK yazısı."""
    d = 0.64 * size
    s.shapes.add_picture(str(LOGO / "mercek-logo-kucuk.png"), Inches(x), Inches(y), Inches(d), Inches(d))
    text(s, x + d + 0.12 * size, y, 3 * size, d, [("MERCEK", {"size": int(26 * size), "bold": True})], anchor=MSO_ANCHOR.MIDDLE)


def logo(s, x, y, w):
    """Büyük logo: saplı mercek, log satırı odakta."""
    s.shapes.add_picture(str(LOGO / "mercek-logo.png"), Inches(x), Inches(y), Inches(w), Inches(w))

def draft_note(s, x, y):
    text(s, x, y, 7, 0.28, [("Taslak görsel — gerçek ekran görüntüsüyle değiştirilecek", {"size": 11, "italic": True, "color": G3})])


def notes(s, t):
    s.notes_slide.notes_text_frame.text = t


# ---------- 1. Kapak ----------
s = new_slide()
text(s, 1.0, 1.55, 6.8, 0.4, [("ZİRAAT TEKNOLOJİ YAPAY ZEKÂ HACKATHONU · TEMA 2", {"size": 14, "bold": True, "color": RED})])
text(s, 1.0, 2.0, 6.8, 1.3, [("MERCEK", {"size": 72, "bold": True})])
box(s, 1.05, 3.35, 1.2, 0.07, fill=RED, shape=MSO_SHAPE.RECTANGLE)
text(s, 1.0, 3.6, 6.8, 0.6, [("Soruna odaklanır, çözümü netleştirir.", {"size": 26, "italic": True, "color": RED2})])
text(s, 1.0, 4.75, 6.8, 0.9, [("AI Overflow Takımı", {"size": 20, "bold": True}), ("17 Ekim 2026", {"size": 16, "color": G3})], space=4)
logo(s, 7.75, 1.0, 4.6)
notes(s, "0:00–0:10 · Merhaba, biz AI Overflow. Projemizin adı Mercek: soruna odaklanır, çözümü netleştirir.")

# ---------- 2. Takım ----------
s = new_slide("AI Overflow Takımı")
for i in range(5):
    x, y, w, h = 0.55 + i * 2.5, 1.45, 2.3, 4.6
    box(s, x, y, w, h)
    c = box(s, x + w / 2 - 0.65, y + 0.4, 1.3, 1.3, fill=WHITE, line=RED, shape=MSO_SHAPE.OVAL)
    s.shapes.add_picture(str(ICON / "user-g.png"), Inches(x + w / 2 - 0.3), Inches(y + 0.75), Inches(0.6), Inches(0.6))
    text(s, x + 0.15, y + 1.95, w - 0.3, 2.2, [("Ad Soyad", {"size": 18, "bold": True}), ("Birim", {"size": 14, "color": G3}),
                                               ("Projedeki rolü", {"size": 14})], align=PP_ALIGN.CENTER, space=6)
text(s, 0.55, 6.25, 12, 0.35, [("Sorumluluklar 19 maddelik listeden herkesin kendi seçimiyle dağıtıldı.", {"size": 14, "color": G3})])
notes(s, "0:10–0:20 · Takımı tek cümleyle tanıtın. (Ad, birim ve rolleri doldurun; fotoğraf eklenecekse daire içine yerleştirin.)")

# ---------- 3. Problem ----------
s = new_slide("Hata mı, Kural mı? Bilinmeyince Çağrı Açılıyor")
box(s, 0.45, 1.3, 3.55, 5.25, fill=RED2)
s.shapes.add_picture(str(ICON / "quote-w.png"), Inches(0.8), Inches(1.65), Inches(0.5), Inches(0.5))
text(s, 0.8, 2.35, 2.9, 2.4, [("“Ekran ‘kullandırılamaz’ diyor. Sistem mi bozuk?”", {"size": 24, "bold": True, "italic": True, "color": WHITE})])
text(s, 0.8, 5.6, 2.9, 0.7, [("Elif, şube müşteri temsilcisi · KRDTKULL", {"size": 14, "color": WHITE})], anchor=MSO_ANCHOR.BOTTOM)
steps = ["Temsilci uyarıyı görür", "Çağrı açar", "L1 Kibana'da log arar", "L2 kurumu ve kodu inceler", "Yeni talep bu sorunlardan habersiz planlanır"]
for i, t in enumerate(steps):
    x = 4.3 + i * 1.72
    box(s, x, 1.3, 1.58, 1.95)
    circle(s, x + 0.15, 1.45, 0.45, RED, str(i + 1), 14)
    text(s, x + 0.15, 2.0, 1.3, 1.2, [(t, {"size": 14})])
text(s, 4.3, 3.4, 8.5, 0.6, [[("Bedeli: ", {"size": 14, "bold": True, "color": RED2}),
                             ("işlem yapamayan müşteri · gereksiz çağrılar · aynı kurum sorunu için onlarca kayıt · veriden kopuk planlanan talepler", {"size": 14, "color": RED2})]])
pains = [("eye-w.png", "Hata mı kural mı belli değil", "İş kuralı reddi ekranda teknik hatadan ayrılamıyor."),
         ("users-w.png", "Aynı sorun, onlarca çağrı", "Kurum kaynaklı sorunda her arama ayrı kayıt; çözüm kişilerde."),
         ("unlink-w.png", "Talepler veriden kopuk", "Efor toplantıda; erişim ve kapasite sorunları geç fark ediliyor.")]
for i, (ic, h1, d) in enumerate(pains):
    x = 4.3 + i * 2.88
    circle(s, x, 4.25, 0.6, G3, icon=ic)
    text(s, x, 5.0, 2.7, 1.5, [(h1, {"size": 16, "bold": True}), (d, {"size": 14, "color": G3})])
notes(s, "0:20–0:40 · Şube personeli işlem yapamadığında hata mı kural mı bilemiyor, çağrı açıyor. L1 ve L2 Kibana'da log arıyor, aynı kurum sorunu için onlarca çağrı açılıyor, bilinen çözümler kişilerde kalıyor. Yeni talepler de bu sorunlardan habersiz planlanıyor.")

# ---------- 4. Çözüm ----------
s = new_slide("Mercek: Sorundan Plana Tek Akış")
text(s, 0.45, 1.2, 12.4, 0.8, [("Banka çalışanlarının ekranlarda yaşadığı sorunu loglardan, çağrı geçmişinden ve koddan açıklar; çağrıları doğru servise yönlendirip birleştirir ve iş birimi taleplerini servis bazlı efor ve takvimle plana dönüştürür.", {"size": 18})])
mods = [("headset-w.png", "Akıllı Problem Çözüm ve Çağrı Yönetimi",
         ["Ekran bağlamıyla logu bulur, iş kuralını hatadan ayırır", "Çağrıyı servise atar, mükerrerleri ana kayda bağlar", "Geçmiş çözümü bulur; yoksa duyuruya ve koda bakar"]),
        ("clip-w.png", "Akıllı Talep Analizi, Efor ve Takvim",
         ["Talebi bileşenlere ayırır, ekranları ve servisleri bulur", "Benzer taleplerden adam-gün, servis takviminden plan", "Çağrı ve müşteri verisiyle kapsamı düzeltir"])]
for i, (ic, head, items) in enumerate(mods):
    x, y, w = 0.45 + i * 6.65, 2.2, 5.75
    box(s, x, y, w, 3.25)
    box(s, x, y, w, 0.85, fill=RED if i == 0 else RED2, radius=0.12)
    circle(s, x + 0.2, y + 0.13, 0.6, RED3, icon=ic)
    text(s, x + 0.95, y, w - 1.1, 0.85, [(head, {"size": 18, "bold": True, "color": WHITE})], anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 0.3, y + 1.1, w - 0.6, 2.0, [(t, {"size": 16}) for t in items], bullets=True, space=8)
box(s, 6.27, 3.3, 0.8, 1.0, fill=RED3, radius=0.15)
text(s, 6.27, 3.3, 0.8, 1.0, [("veri", {"size": 11, "bold": True, "color": WHITE}), ("→", {"size": 11, "bold": True, "color": WHITE}), ("kapsam", {"size": 11, "bold": True, "color": WHITE})], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, space=0)
text(s, 0.45, 5.75, 1.8, 0.55, [("Kullanıcılar", {"size": 16, "bold": True})], anchor=MSO_ANCHOR.MIDDLE)
for i, t in enumerate(["Şube, çağrı merkezi", "L2, platform", "İş birimleri", "İş analisti"]):
    pill(s, 2.3 + i * 2.6, 5.75, 2.4, 0.55, t, G1, INK, 14)
notes(s, "0:40–0:50 · Tek cümle çözüm. İki modül ve köprü: loglar, çağrı ve müşteri verisi talep kapsamına giriyor. Mercek'i müşteri değil banka çalışanları kullanıyor.")

# ---------- 5. Farklar ----------
s = new_slide("Dört Farkımız", "Bugünkü araçlar sorunu kaydeder; Mercek açıklar, kaynağına bağlar ve yeni talebin planına taşır.")
diffs = [("bolt-w.png", RED, "Bağlamı bilir", "Ekran kodu, son işlemin logu ve temsilcinin cümlesiyle çalışır; kullanıcı yazmadan açıklar ve ekranı doğru değerlerle doldurur."),
         ("code-w.png", RED2, "Üç kaynağı birleştirir", "Log (ne oluyor), kurum duyurusu (neden) ve uygulama kodu (nerede düzeltilir) tek analizde."),
         ("sync-w.png", RED3, "Kapalı döngü", "Çağrı ve müşteri verisi, talebin değerini kanıtlar ve eksik kapsamı talep anında gösterir."),
         ("shield-w.png", G3, "Güvenilir AI", "Hesabı kod yapar, AI açıklar. Eşik altında öneri yok; her rakam ve kod satırı doğrulanır.")]
for i, (ic, col, head, d) in enumerate(diffs):
    x, y, w, h = 0.45 + (i % 2) * 6.3, 1.4 + (i // 2) * 2.6, 6.05, 2.35
    box(s, x, y, w, h)
    circle(s, x + 0.35, y + 0.4, 0.85, col, icon=ic)
    text(s, x + 1.5, y + 0.35, w - 1.8, h - 0.5, [(head, {"size": 20, "bold": True}), (d, {"size": 16, "color": INK})], space=6)
notes(s, "0:50–0:58 · Mercek çağrıyı kaydetmekle kalmıyor: açıklıyor, birleştiriyor, koda bağlıyor ve talebi gerekçelendiriyor. AI'ın rolü sınırlı ve denetlenebilir.")

# ---------- 6. Mimari ----------
s = new_slide("Mimari: Azure Üzerinde Hibrit RAG")


def arch(x, y, w, h, head, sub, fill, color=INK, line_c=None, hs=15, ss=12):
    box(s, x, y, w, h, fill=fill, line=line_c)
    text(s, x + 0.08, y + 0.05, w - 0.16, h - 0.1, [(head, {"size": hs, "bold": True, "color": color}), (sub, {"size": ss, "color": color})],
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, space=2)


arch(0.45, 2.35, 1.6, 2.6, "Kullanıcılar", "Şube, çağrı\nmerkezi\nL2 destek\nİş birimi,\nanalist", SOFT)
arch(2.3, 1.35, 2.3, 1.75, "App Service · web", "Next.js 16\nBankacılık ekranları,\nMercek, Talep", RED, WHITE)
arch(2.3, 4.15, 2.3, 1.75, "App Service · api", "FastAPI · /api/health\norkestrasyon, hesap\nve doğrulama", RED2, WHITE)
# Hibrit RAG çerçevesi
box(s, 4.85, 1.2, 4.1, 4.75, fill=WHITE, line=RED)
text(s, 5.0, 1.24, 3.8, 0.4, [[("HİBRİT RAG  ", {"size": 13, "bold": True, "color": RED}),
                              ("1 getir · 2 bağlam · 3 üret", {"size": 11, "color": G3})]], anchor=MSO_ANCHOR.MIDDLE)
arch(5.0, 1.7, 2.3, 1.6, "Azure AI Search", "1 · anlamca getir\nçözüm · talep · duyuru\nvektör + kelime, Türkçe", SOFT, line_c=RED, hs=14, ss=11)
arch(5.0, 3.45, 2.3, 1.45, "Azure SQL", "1 · rakamı getir\nlog · çağrı · portföy · takvim\nparametreli sorgu", SOFT, line_c=G2, hs=14, ss=11)
arch(7.55, 1.7, 1.25, 3.2, "Azure AI Foundry", "2 · bağlam\n\n3 · chat ile üret\n\nembedding → indeks", RED, WHITE, hs=13, ss=11)
text(s, 5.0, 5.0, 3.8, 0.9, [("Benzeri AI Search bulur, rakamı SQL verir; model yalnızca bu kaynaklı bağlamla yazar ve her cevapta kaynak no'su gösterir.",
                              {"size": 11, "color": INK})], anchor=MSO_ANCHOR.MIDDLE)
line(s, 2.05, 3.0, 2.3, 2.25)
line(s, 3.45, 3.1, 3.45, 4.15)
line(s, 4.6, 4.7, 5.0, 2.5)
line(s, 4.6, 5.0, 5.0, 4.17)
line(s, 7.3, 2.5, 7.55, 2.9, color=RED)
line(s, 7.3, 4.17, 7.55, 3.7, color=RED)
box(s, 0.45, 6.1, 8.35, 0.65)
s.shapes.add_picture(str(ICON / "github-g.png"), Inches(0.6), Inches(6.22), Inches(0.42), Inches(0.42))
text(s, 1.15, 6.1, 7.6, 0.65, [[("GitHub Actions: ", {"size": 12, "bold": True}), ("lint · test · audit · gitleaks → build → 2 deploy → smoke test    ", {"size": 12}),
                               ("GHAS: ", {"size": 12, "bold": True}), ("CodeQL · Dependabot · secret scanning", {"size": 12})]], anchor=MSO_ANCHOR.MIDDLE)
box(s, 9.15, 1.35, 3.75, 2.55, fill=RED)
text(s, 9.35, 1.45, 3.4, 2.4, [("AI ne yapar (Foundry)", {"size": 16, "bold": True, "color": WHITE})] +
     [(t, {"size": 14, "color": WHITE}) for t in ["Metinden bilgi çıkarma, açıklama", "Çağrı zenginleştirme", "Çözüm uyarlama", "Kod analizi", "Talep bileşenleri ve sorular"]], space=3)
box(s, 9.15, 4.1, 3.75, 2.65, fill=G3)
text(s, 9.35, 4.2, 3.4, 2.5, [("Kod ne yapar (kurallar)", {"size": 16, "bold": True, "color": WHITE})] +
     [(t, {"size": 14, "color": WHITE}) for t in ["Log örüntüsü, kredi hesabı", "Eşik, servis ataması, ana kayıt", "Adam-gün medyanı, takvim", "Köprü sayıları", "AI çıktısındaki sayı ve satırları doğrulama"]], space=3)
notes(s, "0:58–1:05 · Mercek hibrit RAG kullanır: AI Search geçmiş çözümleri, talepleri ve duyuruları anlam benzerliğiyle bulur (vektör + kelime, Türkçe analizör, Foundry embedding); Azure SQL o anki gerçek rakamları parametreli sorgularla getirir. Foundry ikisini bağlam olarak alıp cevabı yazar; rakam uydurmaz çünkü her sayı SQL'den gelir. Model SQL yazmaz (text-to-SQL yok). CI/CD her PR'da test ve güvenlik taraması yapıyor. Sağda AI'ın ve kuralların işi. (Yalnızca gerçekten çalışan servisler bu slaytta kalmalı.)")

# ---------- 7. Kullanım senaryoları ----------
s = new_slide("Altı Kullanım Senaryosu")
# live: True = canlı demoda; 2. gün 12:00 kararına göre güncellenir
scen = [("A", "Hata mı, kural mı?", "KRDTKULL · Elif (şube)", "İş kuralı açıklandı, uygun tutar ekrana dolduruldu", "Çağrı açılmadı", True),
        ("B", "Yaygın sorun, bilinen çözüm", "ODMTFATR · Mehmet → Zeynep → Kerem", "Müşteriye hazır açıklama, %93 eşleşen çözüm", "Onlarca arama tek kayıtta", True),
        ("C", "Dış dünya değişti", "ODMTFATR · Elif → Kerem", "Log + kurum duyurusu + kod; düzeltme önerisi", "187 müşteri · ASKİ önceden", True),
        ("D", "Talepten plana", "Talep Yönlendirme · Fatma → Ayşe", "Servis, adam-gün, takvim; veriyle kapsam", "Erişim %58 → %89 · 20 a/g", True),
        ("E", "Acil yeni ekran", "KRDTERTL (yeni) · Hakan → Ayşe", "Etkilenen müşteri, riskli sorular, kapasite çatışması", "Aynı gün karar · 17 a/g", False),
        ("F", "Günlük durum özeti", "Mercek sohbet · Kerem", "Kibana bilgisi gerektirmeden sohbetle özet", "En sorunlu ekran: ODMTFATR", False)]
for i, (L, head, who, what, res, live) in enumerate(scen):
    x, y, w, h = 0.45 + (i % 3) * 4.2, 1.2 + (i // 3) * 2.8, 3.95, 2.6
    col = RED if live else G3
    box(s, x, y, w, h)
    circle(s, x + 0.25, y + 0.25, 0.62, col, L, 20)
    text(s, x + 1.02, y + 0.2, w - 1.15, 0.75, [(head, {"size": 17, "bold": True}), (who, {"size": 12, "color": G3})], anchor=MSO_ANCHOR.MIDDLE, space=1)
    text(s, x + 0.25, y + 1.07, w - 0.5, 0.7, [(what, {"size": 14})])
    text(s, x + 0.25, y + 1.85, w - 1.55, 0.55, [(res, {"size": 14, "bold": True, "color": RED2 if live else INK})], anchor=MSO_ANCHOR.MIDDLE)
    pill(s, x + w - 1.3, y + 1.93, 1.1, 0.38, "CANLI" if live else "KAYIT", col)
notes(s, "1:05–1:20 · Mercek'in altı kullanım senaryosu. 'CANLI' etiketliler birazdan canlı gösterilecek; diğerleri ekran görüntüsü veya kısa videoyla. (2. gün 12:00 kod dondurmada etiketleri gerçek duruma göre güncelleyin: canlı demoya yalnızca deploy edilmiş ortamda doğrulaması yeşil ve 3 provada hatasız olan senaryolar girer.)")

# ---------- 8. Canlı demo ----------
s = new_slide("Canlı Demo: Dört Sahne")
scenes = [("~45 sn", "A · Hata mı, kural mı?", "m-a-panel.png", "Elif yazmadan Mercek iş kuralını açıklıyor, 'Bana göster' ile 330.000 TL / 36 ay dolduruluyor. Çağrı açılmıyor."),
          ("~50 sn", "B · Bilinen çözüm", "m-b-callcenter.png", "Zeynep'e müşteriye söylenecek metin; vaka CAG-2051'e bağlanıyor; Kerem'e %93 eşleşen çözüm."),
          ("~35 sn", "C · Dış dünya değişti", "m-c-code.png", "412 hata, %97 İSKİ, 13 hane; İSKİ duyurusu; kuralın koddaki iki yeri ve düzeltme; ASKİ uyarısı."),
          ("~45 sn", "D · Talepten plana", "m-d-request.png", "KRDRTKSR'ye buton + batch işi, 18 a/g; SMS ile erişim %58 → %89, 20 a/g, 4 Aralık.")]
AR = 2560 / 1516
for i, (t, head, img, d) in enumerate(scenes):
    x, y, w, h = 0.45 + (i % 2) * 6.3, 1.15 + (i // 2) * 2.75, 6.1, 2.6
    box(s, x, y, w, h)
    ih = 2.2
    iw = ih * AR
    pic = s.shapes.add_picture(str(MOCK / img), Inches(x + 0.2), Inches(y + 0.2), Inches(iw), Inches(ih))
    pic.line.color.rgb = G2
    tx, tw = x + 0.4 + iw, w - iw - 0.6
    pill(s, tx, y + 0.2, 0.95, 0.34, t, RED)
    text(s, tx, y + 0.65, tw, 0.55, [(head, {"size": 16, "bold": True})])
    text(s, tx, y + 1.2, tw, 1.3, [(d, {"size": 12})])
draft_note(s, 0.45, 6.68)
notes(s, "1:20–4:15 · CANLI DEMO (~3 dk), önce demo_reset çalıştırılmış olmalı. A: Elif KRDTKULL 400.000 / 3 ay → Sorun yaşıyorum → iş kuralı kartı → Bana göster. B: Mehmet ODMTFATR Başkentgaz (odm-dogalgaz turu) → Zeynep Mercek'e yazar → müşteriye söylenecek metin, CAG-2051 bağlı vaka 12 → Kerem %93 eşleşme. C: Elif İSKİ metni → 412 / %97 / 13 hane, duyuru → Kerem: %35, kod analizi, diff, ASKİ. D: Fatma talebi → analiz kartları → önerileri kabul et → 18 a/g, 9 Kasım–2 Aralık → köprü → Evet → 20 a/g, 4 Aralık. Canlıda olmayan sahneyi ekran görüntüsüyle 15 sn'de geçin; bir sahne bozulursa videosuna geçin.")

# ---------- 9. İş değeri ----------
s = new_slide("İş Değeri: Önce ve Sonra")
for i, (big, lbl, col) in enumerate([("Çağrı hiç açılmıyor", "İş kuralı reddinde (A)", RED), ("Onlarca arama → tek kayıt", "Kurum kaynaklı sorunda (B)", RED2), ("Toplantı → dakikalar", "Talep analizi ve planı (D)", RED3)]):
    x = 0.45 + i * 4.2
    box(s, x, 1.2, 3.95, 1.5)
    text(s, x + 0.3, 1.2, 3.4, 1.5, [(big, {"size": 22, "bold": True, "color": col}), (lbl, {"size": 14, "color": G3})], anchor=MSO_ANCHOR.MIDDLE, space=2)
rows = [("Ölçü", "Bugün", "Mercek ile"),
        ("İş kuralı reddi", "Çağrı açılır, L1 kuralı açıklar", "Ekranda açıklanır, uygun alternatif hesaplanır"),
        ("Yaygın kurum sorunu", "Her arama ayrı çağrı", "Tek ana kayıt, temsilciye hazır müşteri açıklaması"),
        ("Bilinen sorun", "L2 log arar, çözüm kişide", "Kaynaklı eşleşen çözüm, saniyeler içinde"),
        ("Yeni sorun", "Kök neden günlerce aranır", "Log + duyuru + kod; sonraki olay önceden görülür"),
        ("Talep planı", "Servisler ve erişim sorunu geç fark edilir", "Servis bazlı a/g ve takvim; kapsam veriyle düzeltilir")]
tbl = s.shapes.add_table(len(rows), 3, Inches(0.45), Inches(2.95), Inches(12.4), Inches(3.3)).table
for j, wdt in enumerate([2.9, 4.3, 5.2]):
    tbl.columns[j].width = Inches(wdt)
tblPr = tbl._tbl.tblPr
for k in list(tblPr):
    if k.tag == qn("a:tableStyleId"):
        tblPr.remove(k)
for r, row in enumerate(rows):
    for c, val in enumerate(row):
        cell = tbl.cell(r, c)
        cell.fill.solid()
        cell.fill.fore_color.rgb = RED2 if r == 0 else (SOFT if r % 2 == 0 else WHITE)
        cell.margin_left = cell.margin_right = Inches(0.12)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf = cell.text_frame
        tf.text = ""
        _run(tf.paragraphs[0], val, {"size": 14, "bold": r == 0 or c == 0, "color": WHITE if r == 0 else INK})
text(s, 0.45, 6.4, 12.4, 0.3, [("Rakamlar sentetik veriye dayanır; demo sırasında Mercek'in sayaçları (önlenen çağrı, bağlanan vaka, analiz süresi) gösterilir.", {"size": 12, "italic": True, "color": G3})])
notes(s, "4:15–4:45 · Önce/sonra. Demo sırasında artan sayaçları ve ölçülen analiz süresini söyleyin. Varsayımları açıkça belirtin.")

# ---------- 10. Neredeyiz ----------
s = new_slide("Neredeyiz, Sırada Ne Var")
cols = [("check-w.png", RED, "Tamamlanan", ["M1: bağlam, log örüntüsü, servis ataması, ana kayıt, eşleştirme, kod analizi", "M2: talep analizi, servis etkisi, adam-gün, takvim, köprü", "Azure: 2 App Service, Foundry, hibrit RAG (AI Search + SQL)", "CI/CD ve PR'da güvenlik taraması"]),
        ("warn-w.png", G3, "Sınırlamalar", ["Veri tamamen sentetik", "Gerçek log, çağrı ve kod entegrasyonu yok", "Kod düzeltmeleri öneri; uygulama insan onaylı", "E-posta ve SMS gönderimi simülasyon"]),
        ("route-w.png", RED3, "Canlıya geçiş", ["Log kaynağı: Kibana / Elasticsearch", "Çağrı sistemi ve kod reposu için salt-okur entegrasyon", "KVKK: loglarda maskeleme", "Pilot: şube kanalı, KRDTKULL ve ODMTFATR"])]
for i, (ic, col, head, items) in enumerate(cols):
    x, w = 0.45 + i * 4.2, 3.95
    box(s, x, 1.2, w, 5.4)
    circle(s, x + 0.3, 1.45, 0.75, col, icon=ic)
    text(s, x + 1.2, 1.45, w - 1.4, 0.75, [(head, {"size": 20, "bold": True})], anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 0.3, 2.5, w - 0.6, 3.9, [(t, {"size": 15}) for t in items], bullets=True, space=10)
notes(s, "4:45–4:55 · 'Tamamlanan' listesini 2. gün 12:00'de gerçek duruma göre güncelleyin. S-C: AI yanlışsa → eşik, kaynak, sayı doğrulaması, insan onayı. Maliyet → küçük model, kısa bağlam, analiz başına ölçülen token.")

# ---------- 11. Ekler ve kapanış ----------
s = new_slide("Ekler")
for i, (ic, h1, v) in enumerate([("github-w.png", "GitHub repository", "[repo bağlantısı]"), ("globe-w.png", "Web uygulaması", "[mercek-web adresi]"), ("video-w.png", "Senaryo videoları", "[video bağlantısı]")]):
    y = 1.5 + i * 1.2
    circle(s, 0.6, y, 0.8, RED2, icon=ic)
    text(s, 1.65, y - 0.02, 5.5, 0.85, [(h1, {"size": 18, "bold": True}), (v, {"size": 16, "color": RED})], anchor=MSO_ANCHOR.MIDDLE, space=2)
logo(s, 8.45, 1.25, 3.3)
text(s, 7.6, 4.85, 5.0, 1.0, [("MERCEK", {"size": 32, "bold": True}), ("Soruna odaklanır, çözümü netleştirir.", {"size": 18, "italic": True, "color": RED2})], align=PP_ALIGN.CENTER, space=4)
text(s, 0.6, 5.4, 12, 0.5, [("Teşekkürler · AI Overflow", {"size": 20, "bold": True, "color": RED2})])
notes(s, "4:55–5:00 · Sloganla kapatın. Bağlantıları sunumdan önce doldurun; şifre, anahtar veya gerçek müşteri verisi görünmediğini kontrol edin.")

prs.save(OUT)
print("OK", OUT)
