# Mercek — Kullanıcı Bazında Demo Soruları

Demo kullanıcılarının Mercek'e sorabileceği sorular, beklenen yanıtların özeti ve bunları taşıyan sentetik veri. Sayılar `datav2/` verisinden alındı (veri sonu **17.10.2026 09:00**). Demo kayıtları (CAG-2051, CAG-2052, TLP-1043/1044/1045, prevented_calls) dosyalarda yok; demo sırasında oluşur.

İşaretler: ⭐ ana demo sorusu · ➕ ek / yedek soru · 🔁 aynı soruyu farklı sözcüklerle sorma örnekleri (serbest metin çıkarımını göstermek için).

| Kullanıcı | Rol · birim | Mercek'e nereden ulaşır | Senaryolar |
|---|---|---|---|
| **Elif** Demir | Şube müşteri temsilcisi · Kızılay (601) | Ekrandaki **"Sorun yaşıyorum"** butonu | A, B, C |
| **Zeynep** Arslan | Çağrı merkezi temsilcisi (9009) | Mercek sohbet | B, telefon biçimi |
| **Kerem** Aydın | Platform yöneticisi · L2 destek (9010) | Mercek sohbet + Çağrılar + Kural önerileri | B, C, F, G, ölçüm |
| **Fatma** Öztürk | Bölüm başkanı · Kredi Tahsilatları (9001) | Talep Yönlendirme | D |
| **Hakan** Çelik | Bölüm başkanı · Bireysel Krediler (9002) | Talep Yönlendirme | E |
| **Ayşe** Kaya | Kıdemli iş analisti (teknoloji) | Talep Yönlendirme | D, E, G |

---

## 1. Elif — Şube müşteri temsilcisi

### A · KRDTKULL · "Hata mı, kural mı?"
⭐ **"Müşteriye kredi kullandıramıyorum, kullandır butonu kapalı. Bu bir sistem hatası mı?"** (Sorun yaşıyorum butonundan)

- **Beklenen yanıt:** Bu bir sistem hatası değil, **iş kuralı** (120218 AFFORDABILITY_EXCEEDED). 400.000 TL / 3 ay taksiti **144.185,92 TL**; aylık gelirin %50'si **19.000 TL** (38.000 × %50).
- **Öneri:** **330.000 TL / 36 ay**, taksit **18.772,19 TL** (en yüksek tutar ≈ 334.004 TL).
- **Sonuç:** Çağrı açılmaz → `prevented_calls` +1.

➕ **"Bu müşteriye en fazla ne kadar kredi kullandırabilirim?"** → ≈ 334.004 TL; yuvarlanmış öneri 330.000 TL / 36 ay. Hesabı kod yapar, AI açıklar.

➕ **"Bana göster."** → Joyride turu ekranı 330.000 TL / 36 ay değerleriyle doldurur (M1.5).

➕ **"Vadeyi kısaltırsam ne kadar çekebilir?"** → Kod seçilen vade için yeniden hesaplar; Mercek sonucu açıklar.

🔁 "Kredi neden geçmiyor?" · "Ekranda gelir uyarısı çıktı, çağrı açayım mı?"

### C · ODMTTLMT · İSKİ 13 hane
⭐ **"Müşteri İSKİ su faturası için talimat vermek istiyor, abone numarası kabul edilmiyor."**

- **Beklenen yanıt:** Ekran "abone numarası geçersiz" diyor (110412) ve kural bunu kullanıcı hatası sayıyor. Ancak örüntü farklı:
  - 01.10 öncesinde bu hata **0**, sonrasında **412**.
  - Hataların **%97,1**'i (400) İSKİ'de ve **hepsi 13 haneli** numara.
- **Sonuç:** Sorun müşteride ya da temsilcide değil. Mercek ana kayıt **CAG-2052**'yi açar.
- **Müşteriye söylenecek:** "Kurumun numara biçimi değişti, düzeltme üzerinde çalışılıyor."

🔁 "İSKİ numarası 13 hane, ekran 12'den fazla almıyor" · "Su faturası talimatı hata veriyor"

### B · ODMTTLMT · Başkentgaz (şubeden)
➕ **"Başkentgaz talimatında abone doğrulanamıyor, 'kurumdan yanıt alınamadı' diyor."**

- **Beklenen yanıt:** Kurum kaynaklı zaman aşımı (110731). Son 30 dakikada **46** işlem etkilendi (8'i Elif'in kayıtları).
- **Çağrı:** Açık ana kayda bağlanır; yeni çağrı açılmaz.

---

## 2. Zeynep — Çağrı merkezi temsilcisi

### B · Başkentgaz zaman aşımı
⭐ **"Müşteri arıyor, doğalgaz faturası için otomatik talimat veremiyormuş. Ekranda kurumdan yanıt alınamadı yazıyormuş."**

- **Mercek'in metinden çıkardıkları:** ekran **ODMTTLMT**, kurum **Başkentgaz (GAZ02)**, müşteri no (varsa).
- **Logdaki bulgu:** Müşterinin başarısız işlemi ve yaygın sorun. 08:30–09:00 arasında **46** zaman aşımı, 46 farklı müşteri. GAZ02'de daha önce hiç zaman aşımı görülmemiş ve bu artış bilinen bakım penceresinin de dışında.
- **Çağrı:** İlk vakada **CAG-2051** ana kaydı açılır (FATURA_ODEME, öncelik 2). Sonraki vakalar **CAG-2051-NN** olarak bu kayda bağlanır (Mükerrer Çağrı / Ana Kayda Bağlandı).

⭐ **"Müşteriye ne söylemeliyim?"** → Hazır açıklama: "Kurumun sisteminde geçici bir sorun var, talimatınız kaydedilmedi; sorun giderilince tekrar deneyebilirsiniz." Hiçbir teknik ayrıntı içermez.

➕ **"Bu sorun için açık bir kayıt var mı?"** → CAG-2051 ve şu ana kadar bağlanan vaka sayısı.

🔁 "Başkentgaz talimatı olmuyor" · "Gaz faturası talimatı hata, müşteri sinirli"

### Kuralı olmayan hata · MUSTGUNC telefon biçimi
➕ **"Müşteri cep telefonunu güncelleyemiyor, numara geçersiz diyor."**

- **Beklenen yanıt:** Bu hata için tanımlı kural yok (PHONE_FORMAT_INVALID). Son 30 günde **60** log ve **15** çağrı var. Hazır çözüm şablonu: **SOL-027** (telefon biçimi).
- Mercek doğru biçimi açıklar ve Kerem'e **kural önerisi** oluşturur.

---

## 3. Kerem — L2 destek / platform yöneticisi

### F · Günlük durum
⭐ **"Bugün en çok sorun yaşanan ekran hangisi?"** → **ODMTTLMT**: 17.10'da **48** uyarı ve hata. Bunların 46'sı Başkentgaz zaman aşımı; diğer ekranlarda sorun yok. Açık ana kayıt: CAG-2051.

🔁 "Bugün durum nasıl?" · "Son bir saatte artan hata var mı?"

### B · Bilinen çözüm
⭐ **"CAG-2051 için benzer geçmiş çözüm var mı?"** → **SOL-031** (Dış Kurum Kaynaklı / Kurum Servis Kesintisi), eşleşme ≥ %90. Bu şablonla kapanmış **6** geçmiş çağrı var. Mercek çözüm adımlarını bu olaya uyarlar.

### C · Kök neden
⭐ **"İSKİ çağrıları neden tekrar tekrar geliyor?"**

- **Kayıtlı çağrılar:** **12** İSKİ çağrısı var. **10**'u SOL-005 "kullanıcı hatası" şablonuyla **yanlış** kapatılmış, **2**'si açık.
- **Örüntü:** Hata 01.10'dan beri İSKİ'de ve yalnızca 13 haneli numaralarda görülüyor.
- **Kök neden:** Ortak duyuru kutusundaki **EML-0022** (12.09) ve **EML-0027** (26.09 hatırlatma). İkisi de **işlenmemiş**.

⭐ **"Bunu kodda nerede düzeltmeliyim?"**

- **Nerede:** "6–12 hane" kuralı iki yerde sabit yazılı: frontend formu `bill-order-form.tsx` ve backend doğrulaması `odm.py`.
- **Acil düzeltme:** İSKİ için 13 haneye izin vermek.
- **Kalıcı öneri:** Hane sayısını **PRMTGENL**'de kurum bazlı parametre yapmak.

➕ **"Başka kurumlarda da böyle bir değişiklik var mı?"** (G) → **EML-0031**: ASKİ de **01.01.2027**'den itibaren 13 haneye geçiyor. Henüz hata yok; proaktif talep önerilir (bkz. Ayşe, TLP-1045).

### Kural önerileri (AI önerir, insan onaylar)
⭐ **"Onay bekleyen kural önerisi var mı?"** → MUSTGUNC · PHONE_FORMAT_INVALID: 60 log, 15 çağrı. Önerilen kural: iş hatası, çağrı açılmasın, ipucu: doğru telefon biçimi.

- Kerem **onaylar** → kural `error_handling_rules`'a `source = mercek` olarak eklenir.

### Ölçüm (M1.6)
➕ **"Mercek bugüne kadar ne kazandırdı?"**

- **Pilot (15–16.10):** **62** çağrıda öneri verildi. Kapanan **28** çağrıda öneri aynen kullanıldı ve çözüm süresi yarıya indi.
- **Demo sırasında:** önlenen çağrı (A) ve birleştirilen vakalar (B).

➕ **"Geçmişte kaç uygunluk (gelir oranı) çağrısı açılmış?"** → **106**. Bunların hepsi Mercek ile önlenebilecek çağrılar.

---

## 4. Fatma — Kredi Tahsilatları Bölüm Başkanı (talep sahibi)

### D · Taksit hatırlatma
⭐ **Talep metni:** "Daha önce gecikme yapmış müşterilere taksit tarihinden birkaç gün önce otomatik hatırlatma e-postası gitsin. Temsilciler de ekrandan seçtikleri müşteriye anında hatırlatma gönderebilsin."

- **Mercek'in analizi:** İki bileşen çıkarır:
  - günlük çalışan bir **batch işi**
  - **KRDTTAHS** ekranına **"Hatırlatma gönder"** butonu
- **Departmanlar:** **Kredi Takip** ana, **Müşteri Yönetim** etkileşimli.
- **Tahmin:** **18 a/g**, benzer taleplerden (TLP-0871, 0915, 0962, 1004, 1019).

⭐ **"Bu talep gerçekten gerekli mi, kaç müşteriyi ilgilendiriyor?"** → Son 12 ayda **2.340** müşteri, **3.249** kredi gecikmiş. Bugün **1.562** kredi gecikmede.

⭐ **"Bu müşterilerin hepsine e-postayla ulaşabilir miyiz?"**

- **Beklenen yanıt:** Hayır. Hedef grubun **%42**'sinin e-posta izni ya da adresi yok.
- **Öneri:** **SMS** kanalını kapsama eklemek (ADD-SMS, +2 a/g).
- **Sonuç:** Fatma kabul eder → **20 a/g**.

➕ **"Ne zaman biter, neden hemen başlamıyor?"**

- **Neden başlamıyor:** Kredi Takip 12.10–08.11 arasında **%100 dolu**. Ekip **TLP-1021**'de, yıl sonu regülasyon işinde.
- **Takvim:** **09.11**'de başlar. Bitiş SMS olmadan **02.12**, SMS ile **04.12**.

---

## 5. Hakan — Bireysel Krediler Bölüm Başkanı (talep sahibi)

### E · Acil taksit erteleme (gerçek afet, il ya da tarih gösterilmez)
⭐ **Talep metni:** "Etkilenen bölgedeki müşterilerimizin kredi taksitlerini erteleyebilmemiz için iki hafta içinde bir ekran lazım."

- **Ekran:** Erteleme ekranı katalogda yok, **yeni ekran** gerekir.
- **Etki:** Bölgede **4.870** kredili müşteri var.
- **Benzer talepler:** TLP-0588, 0712, 0846. Tahmin **15 a/g**.

⭐ **"İki haftada yetişir mi?"**

- **Çatışma:** Kredi Takip **TLP-1021**'de dolu, bu bir kapasite çatışması. Mercek seçenekleri sunar; örneğin E'ye öncelik verilir ve TLP-1021 ile TLP-1043 kayar.
- **Takvim:** 19.10'da başlar, **30.10**'da biter.

⭐ **"Müşterilere nasıl haber verelim?"**

- **Öneri:** Kimse aramadan önce **proaktif SMS** göndermek (ADD-PROAKTIF-SMS, +2 a/g).
- **Erişim:** **3.973** müşterinin SMS izni var; en az bir kanal izni olan **4.516**.
- **Sonuç:** **17 a/g**, bitiş **02.11**.

➕ **"Gözden kaçırdığımız risk var mı?"** → Bölgede son günlerde **37** adres değişikliği var (MUSTGUNC logları). Erteleme hakkı adres tarihine göre mi belirlenecek? Ayrıca D ile gönderim altyapısı ortak kullanılabilir.

---

## 6. Ayşe — Kıdemli iş analisti

➕ **"Bu talep için iş birimine sormam gereken açık sorular neler?"**

- **D:** hatırlatma kaç gün önce gitsin, SMS metni kimin onayında olacak.
- **E:** hak kriteri ne olacak, adres değişikliği nasıl ele alınacak.

➕ **"Benzer geçmiş talepler ve gerçekleşen eforları neler?"**

- **D'ye benzeyenler:** TLP-0871 (14), 0915 (11), 0962 (9), 1004 (6), 1019 (8 a/g).
- **E'ye benzeyenler:** TLP-0588 (15), 0712 (13), 0846 (17 a/g).
- **Not:** Yalnızca `tamamlandi` durumundaki talepler sayılır.

⭐ **"Mercek'in kendisinin önerdiği talep var mı?"** (G)

- **Talep:** **TLP-1045**. ASKİ'nin 01.01.2027'deki 13 hane geçişi için hata oluşmadan önce açılan bir düzeltme talebi; kaynağı EML-0031, durumu öneri.
- **Plan:** **~4 a/g**, FATURA_ODEME, **19.10 → 23.10**.

---

## 7. Mehmet — Banka müşterisi (Mercek'i kullanmaz)
Mehmet doğalgaz faturası için talimat vermeye çalışır ve hata alır (B). Ardından çağrı merkezini arar. Onun **canlı isteği** demoda yeni bir log üretir, Zeynep'in sorusunu da bu tetikler.

---

## 8. Demo öncesi kontrol

- `demo_reset.py` çalıştırılmış olmalı. Bu adım 17.10 09:00 sonrası logları, CAG-2051*, CAG-2052 ve prevented_calls kayıtlarını siler.
- Sorular serbest metindir; 🔁 örnekleri, Mercek'in farklı ifadelerden aynı bağlamı çıkardığını göstermek için kullanılır.
- Rakamlar hep **koddan** gelir. AI yalnızca açıklar; yanıttaki her sayı girdide bulunmalıdır.
