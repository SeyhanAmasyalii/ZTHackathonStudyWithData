// Joyride senaryoları — datav2 ile uyumlu sürüm (17.10.2026)
//
// Uyum notları
// - Ekran kodları 9 ekranlık katalogla aynı: KRTTBASV, KRTTGUNC, KRDTKULL, MUSTTANM, MUSTGUNC, HSPTVDSZ,
//   ODMTTLMT, KRDTTAHS, PRMTGENL. Eski kodlar kaldırıldı: ODMTFATR → ODMTTLMT, MVTTGUNC → MUSTGUNC,
//   MVTTBASV → MUSTTANM, KRDTHSLT → KRDTTAHS.
// - Müşteri, kredi ve şube değerleri datav2'den: Elif 10000004 (gelir 38.000, kredisi yok), Zeynep 10000005
//   (KRD00006571 gecikmede), Kerem 10000006 (KRD00006218 normal), şube 102 Levent.
// - Hata numaraları error_handling_rules ile aynı (ör. 120218, 110731, 110412, 120640, 160110).
// - Log bağlantısı `transaction.id` değil `correlation_id`.
// - E-postalar `@ornek.test`, telefonlar `0532 000 xx xx` biçiminde. Kimlik numarası yalnızca tur değeridir;
//   loga ve Foundry'ye yazılmaz (MUSTTANM'de KPS doğrulaması için algoritmaya uygun test numarası).
// - Senaryo A, B, C ve M1.5 ("Bana göster") turları eklendi.
// - `match`: turun hangi hatayla ilgili olduğu ({ screen, errorNumber, errorCode }). Mercek bir çağrının
//   logundaki ekran + hata numarasıyla tur seçer (deterministik). Başarılı akışlarda `match: null`.
//   Scenario tipine eklenmeli: match: { screen: string; errorNumber: number; errorCode: string } | null
// - Teknik hatalar (19xx) için tur yok: kullanıcının yapabileceği bir şey yoktur.
//
// Gerekli data-tour hedefleri (ekran başına önek)
//   krt-*  KRTTBASV / KRTTGUNC      krd-*  KRDTKULL        mtn-*  MUSTTANM      mus-*  MUSTGUNC
//   hsp-*  HSPTVDSZ                 odm-*  ODMTTLMT        tah-*  KRDTTAHS      prm-*  PRMTGENL
//   Yeni hedefler: odm-existing-orders, odm-cancel-order, hsp-purpose, hsp-fund-source, hsp-currency-EUR,
//   mtn-serial, mtn-existing-customer, krt-employment(-status), krt-occupation, krt-employer, krt-product-classic
//   code-bar-input, code-bar-submit (ekran kodu çubuğu)

export const scenarios: Scenario[] = [
  // --- KRTTBASV ---------------------------------------------------------------
  {
    id: "krt-gold-onay",
    title: "Gold kart başvurusu onaylanır",
    description: "Gelir yeterli, talep edilen limit tam onaylanır.",
    screen: "KRTTBASV",
    outcome: "success",
    match: null,
    steps: [
      {
        target: "krt-products",
        title: "Kart seçimi",
        content: "Müşteri Gold kartı seçiyor. Gold kart için alt gelir sınırı 20.000 ₺, üst limit 75.000 ₺.",
        actions: [{ type: "click", target: "krt-product-gold" }],
      },
      {
        target: "krt-income",
        title: "Gelir beyanı",
        content: "Aylık net gelir 45.000 ₺ olarak giriliyor. Onaylanabilecek limit gelirin en fazla 3 katıdır.",
        actions: [{ type: "fill", target: "krt-income", value: "45000" }],
      },
      {
        target: "krt-limit",
        title: "Limit talebi",
        content: "Müşteri 30.000 ₺ limit talep ediyor. Gelir ve kart limiti bu talebi karşılıyor.",
        placement: "left",
        actions: [{ type: "fill", target: "krt-limit", value: "30000" }],
      },
      {
        target: "krt-statement-day",
        title: "Hesap kesim günü",
        content: "Hesap kesim günü ayın 15'i olarak seçiliyor.",
        placement: "left",
        actions: [{ type: "fill", target: "krt-statement-day", value: "15" }],
      },
      {
        target: "krt-consents",
        title: "Onaylar",
        content: "KVKK ve ön bilgilendirme onayları zorunlu; ikisi de işaretleniyor.",
        placement: "left",
        actions: [
          { type: "check", target: "krt-kvkk" },
          { type: "check", target: "krt-preinfo" },
        ],
      },
      {
        target: "krt-result",
        title: "Sonuç: Onay",
        content: "Başvuru gönderildi ve 30.000 ₺ limitle onaylandı. İşlemin logu Kibana'da correlation_id ile izlenebilir.",
        actions: [{ type: "click", target: "krt-submit" }],
      },
    ],
  },
  {
    id: "krt-gelir-yetersiz",
    title: "Platinum kart: gelir yetersiz",
    description: "Gelir, Platinum kart alt sınırının altında olduğu için başvuru reddedilir.",
    screen: "KRTTBASV",
    outcome: "rejected",
    match: { screen: "KRTTBASV", errorNumber: 130305, errorCode: "INSUFFICIENT_INCOME" },
    steps: [
      {
        target: "krt-products",
        title: "Platinum kart",
        content: "Müşteri Platinum kartı seçiyor. Bu kart için en az 60.000 ₺ aylık net gelir gerekiyor.",
        actions: [{ type: "click", target: "krt-product-platinum" }],
      },
      {
        target: "krt-income",
        title: "Düşük gelir beyanı",
        content: "Beyan edilen gelir 30.000 ₺ — alt sınırın altında.",
        actions: [{ type: "fill", target: "krt-income", value: "30000" }],
      },
      {
        target: "krt-limit",
        title: "Yüksek limit talebi",
        content: "Müşteri 100.000 ₺ limit talep ediyor.",
        placement: "left",
        actions: [
          { type: "fill", target: "krt-limit", value: "100000" },
          { type: "check", target: "krt-kvkk" },
          { type: "check", target: "krt-preinfo" },
        ],
      },
      {
        target: "krt-result",
        title: "Sonuç: Ret",
        content: "Başvuru 130305 INSUFFICIENT_INCOME ile reddedildi. Bu bir iş kuralıdır; müşteriye Gold veya Klasik kart önerilebilir.",
        actions: [{ type: "click", target: "krt-submit" }],
      },
    ],
  },

  // --- KRTTGUNC ---------------------------------------------------------------
  {
    id: "krt-kart-guncelle",
    title: "Limit, kesim günü ve ekstre tercihi güncelleme",
    description: "1137 numaralı kartın limiti artırılır, hesap kesim günü ve ekstre tercihi değiştirilir.",
    screen: "KRTTGUNC",
    outcome: "success",
    match: null,
    steps: [
      {
        target: "krt-cards",
        title: "Kart seçimi",
        content: "Güncellenecek kart listeden seçiliyor. Bu örnekte 1137 numaralı kart.",
        placement: "left",
        actions: [{ type: "click", target: "krt-card-1137" }],
      },
      {
        target: "krt-limit",
        title: "Limit artırım talebi",
        content: "Mevcut limit 15.000 ₺; talep edilen limit 30.000 ₺ olarak giriliyor.",
        placement: "left",
        actions: [{ type: "fill", target: "krt-limit", value: "30000" }],
      },
      {
        target: "krt-statement-day",
        title: "Hesap kesim günü",
        content: "Hesap kesim günü 5. günden 20. güne alınıyor.",
        placement: "left",
        actions: [{ type: "fill", target: "krt-statement-day", value: "20" }],
      },
      {
        target: "krt-statement-pref",
        title: "Ekstre tercihi",
        content: "Ekstre gönderimi postadan e-postaya alınıyor.",
        placement: "left",
        actions: [{ type: "click", target: "krt-statement-email" }],
      },
      {
        target: "krt-consents",
        title: "Değişiklik özeti ve onay",
        content: "Değişen alanlar özette vurgulanıyor. KVKK ve güncelleme talimatı onayları işaretleniyor.",
        placement: "left",
        actions: [
          { type: "check", target: "krt-kvkk" },
          { type: "check", target: "krt-consent" },
        ],
      },
      {
        target: "krt-result",
        title: "Sonuç: Güncelleme",
        content: "Değişiklikler kaydedildi ve sonuç ekranda gösteriliyor.",
        actions: [{ type: "click", target: "krt-submit" }],
      },
    ],
  },
  {
    id: "krt-limit-red",
    title: "Limit artışı reddedilir",
    description: "Son 6 ayda geç ödemesi olan kartta limit artışı kural gereği yapılmaz.",
    screen: "KRTTGUNC",
    outcome: "rejected",
    match: { screen: "KRTTGUNC", errorNumber: 130412, errorCode: "LIMIT_INCREASE_REJECTED" },
    steps: [
      {
        target: "krt-cards",
        title: "Kart seçimi",
        content: "Geçmişinde geç ödeme olan 4821 numaralı kart seçiliyor.",
        placement: "left",
        actions: [{ type: "click", target: "krt-card-4821" }],
      },
      {
        target: "krt-limit",
        title: "Limit artırım talebi",
        content: "Limit 40.000 ₺'den 60.000 ₺'ye çıkarılmak isteniyor.",
        placement: "left",
        actions: [
          { type: "fill", target: "krt-limit", value: "60000" },
          { type: "check", target: "krt-kvkk" },
          { type: "check", target: "krt-consent" },
        ],
      },
      {
        target: "krt-result",
        title: "Sonuç: Ret",
        content: "Talep 130412 LIMIT_INCREASE_REJECTED ile reddedildi. Sistem hatası değil, iş kuralı.",
        actions: [{ type: "click", target: "krt-submit" }],
      },
    ],
  },
  {
    id: "krt-degisiklik-yok",
    title: "Değişiklik yapmadan gönderme",
    description: "Hiçbir alan değiştirilmeden gönderilirse sistem işlem yapmaz ve bilgi verir.",
    screen: "KRTTGUNC",
    outcome: "info",
    match: null,
    steps: [
      {
        target: "krt-cards",
        title: "Kart seçimi",
        content: "4821 numaralı kart seçiliyor. Form kartın mevcut değerleriyle dolar.",
        placement: "left",
        actions: [{ type: "click", target: "krt-card-4821" }],
      },
      {
        target: "krt-consents",
        title: "Onaylar",
        content: "Onaylar işaretleniyor, ancak hiçbir alan değiştirilmedi.",
        placement: "left",
        actions: [
          { type: "check", target: "krt-kvkk" },
          { type: "check", target: "krt-consent" },
        ],
      },
      {
        target: "krt-result",
        title: "Sonuç: Değişiklik yok",
        content: "Mevcut değerlerle gönderim yapıldı. Güncelleme oluşturulmadı ve 'Değişiklik yapılmadı' bilgisi gösteriliyor.",
        actions: [{ type: "click", target: "krt-submit" }],
      },
    ],
  },

  // --- KRDTKULL ---------------------------------------------------------------
  {
    id: "krd-36-ay",
    title: "36 ay vadeli ihtiyaç kredisi",
    description: "Elif Demir (10000004) için 120.000 ₺ kredi hesaplanır, ödeme planı incelenir ve kullandırılır.",
    screen: "KRDTKULL",
    outcome: "success",
    match: null,
    steps: [
      {
        target: "krd-customer",
        title: "Müşteri",
        content: "Müşteri numarası 10000004 (Elif Demir, aylık gelir 38.000 ₺, mevcut kredisi yok).",
        placement: "right",
        actions: [{ type: "fill", target: "krd-customer", value: "10000004" }],
      },
      {
        target: "krd-amount",
        title: "Kredi tutarı",
        content: "Kredi tutarı 120.000 ₺ olarak giriliyor.",
        placement: "right",
        actions: [{ type: "fill", target: "krd-amount", value: "120000" }],
      },
      {
        target: "krd-term",
        title: "Vade",
        content: "Vade 36 ay seçiliyor. 12 ayın üzerindeki vadelerde aylık faiz %3,49.",
        placement: "right",
        actions: [{ type: "fill", target: "krd-term", value: "36" }],
      },
      {
        target: "krd-summary",
        title: "Kredi özeti",
        content: "Taksit, toplam geri ödeme ve yıllık maliyet anlık hesaplanıyor. Taksite KKDF (%15) ve BSMV (%15) dahil.",
      },
      {
        target: "krd-plan",
        title: "Ödeme planı",
        content: "Her taksitte anapara, faiz ve vergi ayrı ayrı görülüyor. Son satırda kalan anapara sıfırlanır.",
        placement: "left",
      },
      {
        target: "krd-contract",
        title: "Sözleşme onayı",
        content: "Genel kredi sözleşmesi onaylanıyor.",
        placement: "right",
        actions: [{ type: "check", target: "krd-contract" }],
      },
      {
        target: "krd-result",
        title: "Kredi kullandırıldı",
        content: "Tahsis ücreti düşüldükten sonra tutar alacak hesabına geçti. İlk taksit bir ay sonra.",
        actions: [{ type: "click", target: "krd-submit" }],
      },
    ],
  },
  {
    id: "krd-gelir-orani",
    title: "Senaryo A: Taksit/gelir oranı aşımı",
    description: "Elif Demir (gelir 38.000 ₺) için 400.000 ₺ / 3 ay; taksit gelirin %50'sini aşar.",
    screen: "KRDTKULL",
    outcome: "rejected",
    match: { screen: "KRDTKULL", errorNumber: 120218, errorCode: "AFFORDABILITY_EXCEEDED" },
    steps: [
      {
        target: "krd-customer",
        title: "Müşteri",
        content: "Müşteri numarası 10000004 (Elif Demir, aylık gelir 38.000 ₺). Gelirin %50'si 19.000 ₺.",
        placement: "right",
        actions: [{ type: "fill", target: "krd-customer", value: "10000004" }],
      },
      {
        target: "krd-amount",
        title: "Yüksek tutar",
        content: "Kredi tutarı 400.000 ₺ olarak giriliyor.",
        placement: "right",
        actions: [{ type: "fill", target: "krd-amount", value: "400000" }],
      },
      {
        target: "krd-term",
        title: "Kısa vade",
        content: "Vade 3 ay seçiliyor. 6 aya kadar vadelerde aylık faiz %3,09.",
        placement: "right",
        actions: [{ type: "fill", target: "krd-term", value: "3" }],
      },
      {
        target: "krd-summary",
        title: "Yüksek taksit",
        content: "Aylık taksit 144.185,92 ₺; müşterinin gelirinin yarısını (19.000 ₺) aşıyor.",
      },
      {
        target: "krd-warning",
        title: "Uygunluk kontrolü",
        content: "Sistem kullandırımı engelledi: 120218 AFFORDABILITY_EXCEEDED. Bu bir iş kuralıdır, çağrı açmaya gerek yok. Vade uzatılarak veya tutar düşürülerek tekrar denenebilir.",
        placement: "right",
      },
    ],
  },
  {
    id: "krd-mercek-oneri",
    title: "Bana göster: Mercek'in önerdiği kredi",
    description: "M1.5 — Mercek'in A senaryosunda önerdiği 330.000 ₺ / 36 ay ekrana doldurulur.",
    screen: "KRDTKULL",
    outcome: "success",
    match: { screen: "KRDTKULL", errorNumber: 120218, errorCode: "AFFORDABILITY_EXCEEDED" },
    steps: [
      {
        target: "krd-customer",
        title: "Müşteri",
        content: "Aynı müşteri: 10000004 (Elif Demir, gelir 38.000 ₺).",
        placement: "right",
        actions: [{ type: "fill", target: "krd-customer", value: "10000004" }],
      },
      {
        target: "krd-amount",
        title: "Önerilen tutar",
        content: "36 ayda en yüksek uygun tutar yaklaşık 334.000 ₺. Mercek güvenli değer olarak 330.000 ₺ öneriyor.",
        placement: "right",
        actions: [{ type: "fill", target: "krd-amount", value: "330000" }],
      },
      {
        target: "krd-term",
        title: "Önerilen vade",
        content: "Vade 36 ay seçiliyor (aylık faiz %3,49).",
        placement: "right",
        actions: [{ type: "fill", target: "krd-term", value: "36" }],
      },
      {
        target: "krd-summary",
        title: "Uygun taksit",
        content: "Aylık taksit 18.772,19 ₺; gelirin %50'si olan 19.000 ₺'nin altında. Uygunluk kontrolü geçiyor.",
      },
      {
        target: "krd-contract",
        title: "Sözleşme onayı",
        content: "Müşteri kabul ederse sözleşme onaylanır. Mercek öneri yapar; kullandırma kararı temsilcinindir.",
        placement: "right",
      },
    ],
  },

  // --- ODMTTLMT ---------------------------------------------------------------
  {
    id: "odm-talimat-iski",
    title: "Su faturası otomatik ödeme talimatı",
    description: "Mevcut İSKİ abonesi (12 haneli numara) için talimat tanımlanır.",
    screen: "ODMTTLMT",
    outcome: "success",
    match: null,
    steps: [
      {
        target: "odm-customer",
        title: "Müşteri",
        content: "Müşteri numarası 10000005 (Zeynep Arslan) giriliyor.",
        actions: [{ type: "fill", target: "odm-customer", value: "10000005" }],
      },
      {
        target: "odm-category",
        title: "Fatura türü",
        content: "Fatura türü olarak Su seçiliyor.",
        actions: [{ type: "fill", target: "odm-category", value: "Su" }],
      },
      {
        target: "odm-institution",
        title: "Kurum",
        content: "Kurum olarak İSKİ (SU01) seçiliyor.",
        actions: [{ type: "fill", target: "odm-institution", value: "SU01" }],
      },
      {
        target: "odm-subscriber",
        title: "Abone numarası",
        content: "Abone numarası giriliyor. Ekran 6–12 hane kabul ediyor; bu numara 12 hane.",
        actions: [{ type: "fill", target: "odm-subscriber", value: "410020873512" }],
      },
      {
        target: "odm-verify",
        title: "Kurumdan doğrulama",
        content: "Abone numarası İSKİ'nin servisinden doğrulanıyor.",
        actions: [{ type: "click", target: "odm-verify" }],
      },
      {
        target: "odm-account",
        title: "Ödeme hesabı",
        content: "Fatura bedeli Ana Hesap'tan ödenecek.",
        placement: "top",
        actions: [{ type: "fill", target: "odm-account", value: "acc-1" }],
      },
      {
        target: "odm-start-limit",
        title: "Başlangıç ve üst limit",
        content: "Talimat 01.11.2026'dan başlıyor; tek faturada en fazla 1.500 ₺ ödenir.",
        placement: "top",
        actions: [
          { type: "fill", target: "odm-start-date", value: "2026-11-01" },
          { type: "fill", target: "odm-upper-limit", value: "1500" },
        ],
      },
      {
        target: "odm-notification",
        title: "Bildirim tercihi",
        content: "Ödeme sonrası SMS bildirimi seçiliyor.",
        placement: "top",
        actions: [{ type: "click", target: "odm-notify-sms" }],
      },
      {
        target: "odm-result",
        title: "Talimat oluşturuldu",
        content: "Talimat özeti onaylandı ve talimat numarası üretildi.",
        actions: [{ type: "click", target: "odm-confirm" }],
      },
    ],
  },
  {
    id: "odm-baskentgaz-zaman-asimi",
    title: "Senaryo B: Başkentgaz yanıt vermiyor",
    description: "Abone doğrulamada kurum servisi 8.000 ms içinde yanıt vermez (110731 INSTITUTION_TIMEOUT).",
    screen: "ODMTTLMT",
    outcome: "rejected",
    match: { screen: "ODMTTLMT", errorNumber: 110731, errorCode: "INSTITUTION_TIMEOUT" },
    steps: [
      {
        target: "odm-customer",
        title: "Müşteri",
        content: "Kızılay şubesinde müşteri numarası 10004684 giriliyor.",
        actions: [{ type: "fill", target: "odm-customer", value: "10004684" }],
      },
      {
        target: "odm-category",
        title: "Fatura türü",
        content: "Fatura türü olarak Doğalgaz seçiliyor.",
        actions: [{ type: "fill", target: "odm-category", value: "Doğalgaz" }],
      },
      {
        target: "odm-institution",
        title: "Kurum",
        content: "Kurum olarak Başkentgaz (GAZ02) seçiliyor.",
        actions: [{ type: "fill", target: "odm-institution", value: "GAZ02" }],
      },
      {
        target: "odm-subscriber",
        title: "Abone numarası",
        content: "9 haneli tesisat numarası giriliyor; biçim doğru.",
        actions: [{ type: "fill", target: "odm-subscriber", value: "401234567" }],
      },
      {
        target: "odm-verify",
        title: "Sonuç: Kurumdan yanıt alınamadı",
        content: "Doğrulama 504 ile düştü: 110731 INSTITUTION_TIMEOUT. Son 30 dakikada aynı hata 46 kez görüldü; kurum kaynaklı. 'Sorun yaşıyorum' ile Mercek'e sorulabilir.",
        actions: [{ type: "click", target: "odm-verify" }],
      },
    ],
  },
  {
    id: "odm-iski-13-hane",
    title: "Senaryo C: İSKİ 13 haneli abone numarası",
    description: "1 Ekim'den sonra verilen 13 haneli İSKİ numarası ekranın 6–12 hane kuralına takılır (110412).",
    screen: "ODMTTLMT",
    outcome: "rejected",
    match: { screen: "ODMTTLMT", errorNumber: 110412, errorCode: "SUBSCRIBER_NO_INVALID" },
    steps: [
      {
        target: "odm-customer",
        title: "Müşteri",
        content: "Kadıköy şubesinde yeni İSKİ abonesi bir müşteri (10034191) için işlem yapılıyor.",
        actions: [{ type: "fill", target: "odm-customer", value: "10034191" }],
      },
      {
        target: "odm-category",
        title: "Fatura türü",
        content: "Fatura türü olarak Su seçiliyor.",
        actions: [{ type: "fill", target: "odm-category", value: "Su" }],
      },
      {
        target: "odm-institution",
        title: "Kurum",
        content: "Kurum olarak İSKİ (SU01) seçiliyor.",
        actions: [{ type: "fill", target: "odm-institution", value: "SU01" }],
      },
      {
        target: "odm-subscriber",
        title: "13 haneli abone numarası",
        content: "Müşterinin faturasındaki 13 haneli numara giriliyor.",
        actions: [{ type: "fill", target: "odm-subscriber", value: "4100208735126" }],
      },
      {
        target: "odm-verify",
        title: "Sonuç: Abone numarası geçersiz",
        content: "Ekran 110412 SUBSCRIBER_NO_INVALID verdi: abone numarası 13 hane, ekran 6–12 hane kabul ediyor. Numara faturadakiyle aynı; sorun kullanıcıda değil.",
        actions: [{ type: "click", target: "odm-verify" }],
      },
    ],
  },

  // --- MUSTGUNC ---------------------------------------------------------------
  {
    id: "mus-adres",
    title: "Adres değişikliği",
    description: "Müşterinin yeni adresi ve iletişim izni güncellenir.",
    screen: "MUSTGUNC",
    outcome: "success",
    match: { screen: "MUSTGUNC", errorNumber: 150101, errorCode: "VALIDATION_ERROR" },
    steps: [
      {
        target: "mus-customer",
        title: "Müşteri",
        content: "Müşteri numarası 10000006 (Kerem Aydın) giriliyor.",
        actions: [{ type: "fill", target: "mus-customer", value: "10000006" }],
      },
      {
        target: "mus-identity",
        title: "Kimlik bilgileri",
        content: "Ad soyad ve müşteri no bu ekrandan değiştirilemez; şube işlemi gerektirir.",
      },
      {
        target: "mus-city",
        title: "İl",
        content: "Yeni il İstanbul olarak seçiliyor.",
        actions: [{ type: "fill", target: "mus-city", value: "İstanbul" }],
      },
      {
        target: "mus-district",
        title: "İlçe",
        content: "İlçe Beşiktaş olarak giriliyor. İlçe boş bırakılırsa kayıt 150101 VALIDATION_ERROR ile düşer.",
        actions: [{ type: "fill", target: "mus-district", value: "Beşiktaş" }],
      },
      {
        target: "mus-address",
        title: "Açık adres",
        content: "Yeni açık adres yazılıyor.",
        actions: [{ type: "fill", target: "mus-address", value: "Örnek Mah. Deneme Cad. No: 12" }],
      },
      {
        target: "mus-permissions",
        title: "İletişim izinleri",
        content: "Telefonla bilgilendirme izni açılıyor.",
        placement: "left",
        actions: [{ type: "check", target: "mus-perm-phone" }],
      },
      {
        target: "mus-result",
        title: "Güncelleme sonucu",
        content: "Bilgiler kaydedildi ve değişen alanlar listelendi. Not: Senaryoyu tekrar çalıştırırsanız 'Değişiklik yapılmadı' uyarısı görürsünüz.",
        placement: "left",
        actions: [{ type: "click", target: "mus-submit" }],
      },
    ],
  },
  {
    id: "mus-telefon-bicim",
    title: "Telefon numarası farklı biçimde girilir",
    description: "Boşluklu ve ülke kodsuz telefon ekran doğrulamasından geçer, arka uçta beklenmeyen hata verir (kural yok).",
    screen: "MUSTGUNC",
    outcome: "rejected",
    match: { screen: "MUSTGUNC", errorNumber: 150130, errorCode: "PHONE_FORMAT_INVALID" },
    steps: [
      {
        target: "mus-customer",
        title: "Müşteri",
        content: "Müşteri numarası 10000006 (Kerem Aydın) giriliyor.",
        actions: [{ type: "fill", target: "mus-customer", value: "10000006" }],
      },
      {
        target: "mus-phone",
        title: "Cep telefonu",
        content: "Yeni numara boşluklu ve ülke kodu olmadan giriliyor.",
        actions: [{ type: "fill", target: "mus-phone", value: "532 000 47 21" }],
      },
      {
        target: "mus-result",
        title: "Sonuç: Beklenmeyen hata",
        content: "Kayıt beklenmeyen bir hatayla düştü. Logda hata numarası yok; Mercek bunu PHONE_FORMAT_INVALID olarak sınıflar ve yeni kural önerir.",
        placement: "left",
        actions: [{ type: "click", target: "mus-submit" }],
      },
    ],
  },

  // --- HSPTVDSZ ---------------------------------------------------------------
  {
    id: "hsp-usd",
    title: "USD vadesiz hesap açılışı",
    description: "Döviz hesabı açılır; döviz işlem koşulları onayı istenir.",
    screen: "HSPTVDSZ",
    outcome: "success",
    match: null,
    steps: [
      {
        target: "hsp-customer",
        title: "Müşteri",
        content: "Müşteri numarası 10000006 (Kerem Aydın) giriliyor.",
        actions: [{ type: "fill", target: "hsp-customer", value: "10000006" }],
      },
      {
        target: "hsp-currency",
        title: "Döviz cinsi",
        content: "Hesap döviz cinsi olarak USD seçiliyor.",
        actions: [{ type: "click", target: "hsp-currency-USD" }],
      },
      {
        target: "hsp-branch",
        title: "Şube",
        content: "Hesap Levent Şubesi'ne (102) bağlanıyor.",
        actions: [{ type: "fill", target: "hsp-branch", value: "102" }],
      },
      {
        target: "hsp-name",
        title: "Hesap adı",
        content: "Hesaba müşterinin tanıyacağı bir ad veriliyor.",
        actions: [{ type: "fill", target: "hsp-name", value: "Dolar Birikim" }],
      },
      {
        target: "hsp-fx",
        title: "Döviz onayı",
        content: "TL dışı hesaplarda ek olarak döviz işlem koşullarının kabulü gerekiyor.",
        placement: "left",
        actions: [
          { type: "check", target: "hsp-contract" },
          { type: "check", target: "hsp-preinfo" },
          { type: "check", target: "hsp-fx" },
        ],
      },
      {
        target: "hsp-result",
        title: "Hesap açıldı",
        content: "Hesap numarası ve kontrol basamağı geçerli bir IBAN üretildi.",
        actions: [{ type: "click", target: "hsp-submit" }],
      },
    ],
  },

  // --- MUSTTANM ---------------------------------------------------------------
  {
    id: "mtn-yeni-musteri",
    title: "Yeni müşteri kaydı",
    description: "Kimlik doğrulanır; iletişim, adres ve mesleki bilgiler girilir; müşteri numarası üretilir.",
    screen: "MUSTTANM",
    outcome: "success",
    match: null,
    steps: [
      {
        target: "mtn-identity",
        title: "Kimlik bilgileri",
        content: "T.C. kimlik numarası (test numarası), doğum tarihi ve ad soyad giriliyor.",
        placement: "left",
        actions: [
          { type: "fill", target: "mtn-tckn", value: "10000000146" },
          { type: "fill", target: "mtn-birth-date", value: "1990-05-15" },
          { type: "fill", target: "mtn-first-name", value: "Ayşe" },
          { type: "fill", target: "mtn-last-name", value: "Yılmaz" },
        ],
      },
      {
        target: "mtn-verify",
        title: "Kimlik doğrulama",
        content: "Kimlik KPS servisinden doğrulanıyor (demo modunda sentetik yanıt).",
        placement: "left",
        actions: [{ type: "click", target: "mtn-verify" }],
      },
      {
        target: "mtn-contact",
        title: "İletişim ve adres",
        content: "E-posta, cep telefonu ve adres bilgileri giriliyor. Telefon 05XX formatında olmalı.",
        placement: "left",
        actions: [
          { type: "fill", target: "mtn-email", value: "ayse.yilmaz@ornek.test" },
          { type: "fill", target: "mtn-phone", value: "05320004721" },
          { type: "fill", target: "mtn-city", value: "İstanbul" },
          { type: "fill", target: "mtn-district", value: "Kadıköy" },
          { type: "fill", target: "mtn-address", value: "Örnek Mah. Deneme Sok. No: 7 D: 3" },
        ],
      },
      {
        target: "mtn-work",
        title: "Meslek ve gelir",
        content: "Meslek ve aylık net gelir giriliyor. Gelir, müşterinin finansal profilini belirler.",
        placement: "left",
        actions: [
          { type: "fill", target: "mtn-occupation", value: "Yazılım Mühendisi" },
          { type: "fill", target: "mtn-income", value: "65000" },
        ],
      },
      {
        target: "mtn-consents",
        title: "İzinler ve KVKK",
        content: "KVKK aydınlatma onayı zorunlu. SMS izni veriliyor; diğer iletişim izinleri isteğe bağlı.",
        placement: "left",
        actions: [
          { type: "check", target: "mtn-kvkk" },
          { type: "check", target: "mtn-perm-sms" },
        ],
      },
      {
        target: "mtn-result",
        title: "Sonuç: Kayıt oluşturuldu",
        content: "Müşteri kaydı oluşturuldu; müşteri numarası ve işlemin correlation_id'si gösteriliyor.",
        actions: [{ type: "click", target: "mtn-submit" }],
      },
    ],
  },
  {
    id: "mtn-18-yas-alti",
    title: "18 yaş altı müşteri reddi",
    description: "Doğum tarihine göre müşteri 18 yaşından küçük olduğu için kayıt yapılmaz.",
    screen: "MUSTTANM",
    outcome: "rejected",
    match: null,
    steps: [
      {
        target: "mtn-identity",
        title: "Doğum tarihi",
        content: "Doğum tarihi 2012 olarak giriliyor. Müşteri henüz 18 yaşında değil.",
        placement: "left",
        actions: [
          { type: "fill", target: "mtn-tckn", value: "10000000146" },
          { type: "fill", target: "mtn-birth-date", value: "2012-03-10" },
          { type: "fill", target: "mtn-first-name", value: "Can" },
          { type: "fill", target: "mtn-last-name", value: "Demir" },
        ],
      },
      {
        target: "mtn-contact",
        title: "İletişim bilgileri",
        content: "Diğer iletişim alanları doldurulur.",
        placement: "left",
        actions: [
          { type: "fill", target: "mtn-email", value: "can.demir@ornek.test" },
          { type: "fill", target: "mtn-phone", value: "05320009843" },
          { type: "fill", target: "mtn-city", value: "Ankara" },
          { type: "fill", target: "mtn-district", value: "Çankaya" },
          { type: "fill", target: "mtn-address", value: "Örnek Mah. Deneme Cad. No: 1" },
        ],
      },
      {
        target: "mtn-work",
        title: "Mesleki bilgiler",
        content: "Meslek ve gelir alanları doldurulur.",
        placement: "left",
        actions: [
          { type: "fill", target: "mtn-occupation", value: "Öğrenci" },
          { type: "fill", target: "mtn-income", value: "0" },
        ],
      },
      {
        target: "mtn-consents",
        title: "Onaylar",
        content: "KVKK onayı işaretlenip kayıt gönderiliyor.",
        placement: "left",
        actions: [{ type: "check", target: "mtn-kvkk" }],
      },
      {
        target: "mtn-result",
        title: "Sonuç: Ret",
        content: "Sunucu kaydı 'Müşteri en az 18 yaşında olmalı.' doğrulama mesajıyla reddetti. Bu bir iş kuralıdır; çağrı açmaya gerek yoktur.",
        actions: [{ type: "click", target: "mtn-submit" }],
      },
    ],
  },

  // --- KRDTTAHS ---------------------------------------------------------------
  {
    id: "tah-taksit-tahsilat",
    title: "Gecikmiş taksit tahsilatı",
    description: "Zeynep Arslan'ın (10000005) gecikmedeki kredisinin taksiti gecikme faiziyle tahsil edilir.",
    screen: "KRDTTAHS",
    outcome: "success",
    match: null,
    steps: [
      {
        target: "tah-customer",
        title: "Müşteri arama",
        content: "Müşteri numarası 10000005 ile aranıyor.",
        placement: "bottom",
        actions: [
          { type: "fill", target: "tah-customer", value: "10000005" },
          { type: "click", target: "tah-search" },
        ],
      },
      {
        target: "tah-loans",
        title: "Kredi seçimi",
        content: "Müşterinin kredisi KRD00006571 seçiliyor: 50.000 ₺, 12 ay, taksit 5.413,59 ₺, 3 taksit ödendi.",
        placement: "left",
        actions: [{ type: "click", target: "tah-loan-KRD00006571" }],
      },
      {
        target: "tah-installments",
        title: "Taksit listesi",
        content: "4. taksitin vadesi 12.10.2026; 5 gündür gecikmede.",
        placement: "left",
        actions: [{ type: "click", target: "tah-installment-4" }],
      },
      {
        target: "tah-late-fee",
        title: "Gecikme faizi",
        content: "Gecikme faizi gecikme gün sayısına göre hesaplanıp taksit tutarına ekleniyor.",
        placement: "left",
      },
      {
        target: "tah-account",
        title: "Tahsilat hesabı",
        content: "Tutar Ana Hesap'tan tahsil edilecek. Hesabın bakiyesi tutarı karşılıyor.",
        placement: "left",
        actions: [{ type: "fill", target: "tah-account", value: "acc-1" }],
      },
      {
        target: "tah-result",
        title: "Sonuç: Tahsilat tamamlandı",
        content: "Tahsilat dekontu oluşturuldu; tahsil edilen tutar ve kalan anapara gösteriliyor.",
        actions: [{ type: "click", target: "tah-submit" }],
      },
    ],
  },
  {
    id: "tah-kismi-tahsilat",
    title: "Kısmi tahsilat",
    description: "Kerem Aydın'ın (10000006) kredisinin vadesi gelmemiş taksitine kısmi ödeme alınır.",
    screen: "KRDTTAHS",
    outcome: "success",
    match: null,
    steps: [
      {
        target: "tah-customer",
        title: "Müşteri arama",
        content: "Müşteri numarası 10000006 ile aranıyor.",
        placement: "bottom",
        actions: [
          { type: "fill", target: "tah-customer", value: "10000006" },
          { type: "click", target: "tah-search" },
        ],
      },
      {
        target: "tah-loans",
        title: "Kredi seçimi",
        content: "KRD00006218 seçiliyor: 44.000 ₺, 12 ay, taksit 4.763,96 ₺, 6 taksit ödendi, sonraki vade 29.10.2026.",
        placement: "left",
        actions: [{ type: "click", target: "tah-loan-KRD00006218" }],
      },
      {
        target: "tah-type",
        title: "Kısmi tahsilat",
        content: "Tahsilat türü kısmi seçiliyor; 2.000 ₺ alınacak. Gecikme olmadığı için gecikme faizi yok.",
        placement: "left",
        actions: [
          { type: "click", target: "tah-type-partial" },
          { type: "fill", target: "tah-amount", value: "2000" },
        ],
      },
      {
        target: "tah-account",
        title: "Tahsilat hesabı",
        content: "Tutar Ana Hesap'tan karşılanıyor.",
        placement: "left",
        actions: [{ type: "fill", target: "tah-account", value: "acc-1" }],
      },
      {
        target: "tah-result",
        title: "Sonuç: Kısmi tahsilat",
        content: "2.000 ₺ tahsil edildi; taksitin kalan tutarı ve vade tarihi gösteriliyor.",
        actions: [{ type: "click", target: "tah-submit" }],
      },
    ],
  },
  {
    id: "tah-bakiye-yetersiz",
    title: "Tahsilat: bakiye yetersiz",
    description: "Seçilen hesabın bakiyesi taksiti karşılamadığı için tahsilat yapılamaz (120640).",
    screen: "KRDTTAHS",
    outcome: "rejected",
    match: { screen: "KRDTTAHS", errorNumber: 120640, errorCode: "INSUFFICIENT_BALANCE" },
    steps: [
      {
        target: "tah-customer",
        title: "Müşteri arama",
        content: "Müşteri numarası 10000005 ile aranıyor.",
        placement: "bottom",
        actions: [
          { type: "fill", target: "tah-customer", value: "10000005" },
          { type: "click", target: "tah-search" },
        ],
      },
      {
        target: "tah-loans",
        title: "Kredi seçimi",
        content: "Gecikmedeki kredi KRD00006571 seçiliyor.",
        placement: "left",
        actions: [{ type: "click", target: "tah-loan-KRD00006571" }],
      },
      {
        target: "tah-account",
        title: "Tahsilat hesabı",
        content: "Bakiyesi taksitten düşük olan Birikim Hesabı seçiliyor.",
        placement: "left",
        actions: [{ type: "fill", target: "tah-account", value: "acc-2" }],
      },
      {
        target: "tah-result",
        title: "Sonuç: Yetersiz bakiye",
        content: "Tahsilat 120640 INSUFFICIENT_BALANCE ile yapılamadı. Bakiyesi yeterli bir hesap seçilebilir.",
        actions: [{ type: "click", target: "tah-submit" }],
      },
    ],
  },
  {
    id: "tah-musteri-bulunamadi",
    title: "Müşteri bulunamadı",
    description: "Var olmayan bir müşteri numarasıyla arama yapılır.",
    screen: "KRDTTAHS",
    outcome: "rejected",
    match: null,
    steps: [
      {
        target: "tah-customer",
        title: "Müşteri numarası",
        content: "Sistemde olmayan bir müşteri numarası giriliyor.",
        placement: "bottom",
        actions: [{ type: "fill", target: "tah-customer", value: "99999999" }],
      },
      {
        target: "tah-search",
        title: "Arama",
        content: "Ara'ya basılıyor.",
        actions: [{ type: "click", target: "tah-search" }],
      },
      {
        target: "tah-customer",
        title: "Sonuç: Bulunamadı",
        content: "'Bu numaraya ait müşteri bulunamadı.' mesajı gösteriliyor. Kredi listesi açılmaz.",
        placement: "bottom",
      },
    ],
  },

  // --- PRMTGENL ---------------------------------------------------------------
  {
    id: "prm-dort-goz",
    title: "Parametre değişikliği ve dört göz onayı",
    description: "Ödeme ve Talimat grubunda varsayılan talimat üst limiti değiştirilir; ikinci kişinin onayına gider.",
    screen: "PRMTGENL",
    outcome: "info",
    match: { screen: "PRMTGENL", errorNumber: 160110, errorCode: "FOUR_EYES_REQUIRED" },
    steps: [
      {
        target: "prm-group",
        title: "Parametre grubu",
        content: "'Ödeme ve kurum' grubu seçiliyor; sahibi Ödeme ve Talimat departmanı (FATURA_ODEME).",
        actions: [{ type: "fill", target: "prm-group", value: "ODEME" }],
      },
      {
        target: "prm-search",
        title: "Parametreyi bul",
        content: "TALIMAT_UST_LIMIT_VARSAYILAN parametresi aranıyor; mevcut değer 1.000 ₺.",
        actions: [{ type: "fill", target: "prm-search", value: "TALIMAT_UST_LIMIT_VARSAYILAN" }],
      },
      {
        target: "prm-value",
        title: "Yeni değer ve geçerlilik",
        content: "Yeni değer 1.500 ₺, geçerlilik tarihi 01.11.2026.",
        placement: "left",
        actions: [
          { type: "fill", target: "prm-new-value", value: "1500" },
          { type: "fill", target: "prm-valid-from", value: "2026-11-01" },
        ],
      },
      {
        target: "prm-result",
        title: "Sonuç: Onay bekliyor",
        content: "Değişiklik kaydedilmedi, onaya gönderildi (160110 FOUR_EYES_REQUIRED). İkinci yetkili onaylayınca değişiklik geçmişinde görünür.",
        actions: [{ type: "click", target: "prm-submit" }],
      },
    ],
  },

  // --- Hata önleyici turlar ("Bana göster": doğru nasıl yapılır) ----------------
  {
    id: "odm-abone-bulunamadi",
    title: "Kurum aboneyi bulamıyor: yeni abonelik",
    description: "Yeni abonelikler kurum sistemine birkaç iş günü sonra düşer; erken girilen talimat 110520 alır.",
    screen: "ODMTTLMT",
    outcome: "info",
    match: { screen: "ODMTTLMT", errorNumber: 110520, errorCode: "SUBSCRIBER_NOT_FOUND" },
    steps: [
      {
        target: "odm-customer",
        title: "Müşteri",
        content: "Müşteri numarası 10000006 (Kerem Aydın) giriliyor.",
        actions: [{ type: "fill", target: "odm-customer", value: "10000006" }],
      },
      {
        target: "odm-institution",
        title: "Tür ve kurum",
        content: "Elektrik · Enerjisa Başkent (ELK02) seçiliyor.",
        actions: [
          { type: "fill", target: "odm-category", value: "Elektrik" },
          { type: "fill", target: "odm-institution", value: "ELK02" },
        ],
      },
      {
        target: "odm-subscriber",
        title: "Abone numarası",
        content: "Müşterinin geçen hafta açtırdığı aboneliğin numarası giriliyor; biçim doğru.",
        actions: [{ type: "fill", target: "odm-subscriber", value: "720045193" }],
      },
      {
        target: "odm-verify",
        title: "Kurum aboneyi bulamadı",
        content: "Doğrulama 110520 SUBSCRIBER_NOT_FOUND verdi. Numara hatalı değil; kayıt kurumda henüz oluşmamış. Müşteriye abonelik tarihini sorun; 2–3 iş günü sonra talimatı yeniden girin. Çağrı açmaya gerek yok.",
        actions: [{ type: "click", target: "odm-verify" }],
      },
    ],
  },
  {
    id: "odm-mukerrer-talimat",
    title: "Aynı abone için aktif talimat var",
    description: "Başka hesaptan aktif talimatı olan aboneye yeni talimat girilemez (110610); önce eskisi iptal edilir.",
    screen: "ODMTTLMT",
    outcome: "info",
    match: { screen: "ODMTTLMT", errorNumber: 110610, errorCode: "ORDER_ALREADY_EXISTS" },
    steps: [
      {
        target: "odm-customer",
        title: "Müşteri",
        content: "Müşteri numarası 10000005 (Zeynep Arslan) giriliyor.",
        actions: [{ type: "fill", target: "odm-customer", value: "10000005" }],
      },
      {
        target: "odm-existing-orders",
        title: "Mevcut talimatlar",
        content: "Önce müşterinin mevcut talimatlarına bakılıyor: İGDAŞ (GAZ01) için Birikim Hesabı'ndan aktif bir talimat var.",
        placement: "left",
      },
      {
        target: "odm-cancel-order",
        title: "Eski talimatı iptal et",
        content: "Yeni hesaptan ödenmesi isteniyorsa eski talimat iptal ediliyor. İptal edilmezse yeni talimat 110610 ORDER_ALREADY_EXISTS alır.",
        placement: "left",
        actions: [{ type: "click", target: "odm-cancel-order" }],
      },
      {
        target: "odm-institution",
        title: "Yeni talimat",
        content: "Doğalgaz · İGDAŞ (GAZ01) ve aynı abone numarasıyla yeni talimat Ana Hesap'tan tanımlanıyor.",
        actions: [
          { type: "fill", target: "odm-category", value: "Doğalgaz" },
          { type: "fill", target: "odm-institution", value: "GAZ01" },
          { type: "fill", target: "odm-subscriber", value: "305118274" },
          { type: "fill", target: "odm-account", value: "acc-1" },
        ],
      },
      {
        target: "odm-result",
        title: "Talimat oluşturuldu",
        content: "Eski talimat iptal edildiği için yeni talimat sorunsuz kaydedildi.",
        actions: [{ type: "click", target: "odm-confirm" }],
      },
    ],
  },
  {
    id: "hsp-zorunlu-bilgi",
    title: "Döviz hesabında fon kaynağı beyanı",
    description: "EUR hesap açılışında hesap amacı ve fon kaynağı boş bırakılırsa 140101 alınır.",
    screen: "HSPTVDSZ",
    outcome: "success",
    match: { screen: "HSPTVDSZ", errorNumber: 140101, errorCode: "VALIDATION_ERROR" },
    steps: [
      {
        target: "hsp-customer",
        title: "Müşteri",
        content: "Müşteri numarası 10000004 (Elif Demir) giriliyor.",
        actions: [{ type: "fill", target: "hsp-customer", value: "10000004" }],
      },
      {
        target: "hsp-currency",
        title: "Döviz cinsi",
        content: "Hesap döviz cinsi olarak EUR seçiliyor.",
        actions: [{ type: "click", target: "hsp-currency-EUR" }],
      },
      {
        target: "hsp-purpose",
        title: "Hesap amacı ve fon kaynağı",
        content: "Döviz hesaplarında hesap amacı ve fon kaynağı zorunlu. En sık atlanan alan bu; boş kalırsa açılış 140101 VALIDATION_ERROR ile durur.",
        placement: "left",
        actions: [
          { type: "fill", target: "hsp-purpose", value: "Birikim" },
          { type: "fill", target: "hsp-fund-source", value: "Maaş" },
        ],
      },
      {
        target: "hsp-fx",
        title: "Onaylar",
        content: "Sözleşme, ön bilgilendirme ve döviz işlem koşulları onaylanıyor.",
        placement: "left",
        actions: [
          { type: "check", target: "hsp-contract" },
          { type: "check", target: "hsp-preinfo" },
          { type: "check", target: "hsp-fx" },
        ],
      },
      {
        target: "hsp-result",
        title: "Hesap açıldı",
        content: "Zorunlu bilgiler tamam olduğu için hesap açıldı ve IBAN üretildi.",
        actions: [{ type: "click", target: "hsp-submit" }],
      },
    ],
  },
  {
    id: "mtn-kps-seri-no",
    title: "Kimlik doğrulama: yenilenmiş kimlik kartı",
    description: "Kimlik kartı yenilenen müşteride eski seri numarası girilirse KPS doğrulamaz (150210).",
    screen: "MUSTTANM",
    outcome: "success",
    match: { screen: "MUSTTANM", errorNumber: 150210, errorCode: "KPS_VERIFICATION_FAILED" },
    steps: [
      {
        target: "mtn-identity",
        title: "Kimlik bilgileri",
        content: "Kimlik numarası (test numarası), doğum tarihi ve ad soyad giriliyor.",
        placement: "left",
        actions: [
          { type: "fill", target: "mtn-tckn", value: "10000000146" },
          { type: "fill", target: "mtn-birth-date", value: "1990-05-15" },
          { type: "fill", target: "mtn-first-name", value: "Ayşe" },
          { type: "fill", target: "mtn-last-name", value: "Yılmaz" },
        ],
      },
      {
        target: "mtn-serial",
        title: "Seri numarası",
        content: "Seri numarası müşterinin elindeki güncel kimlik kartından giriliyor. Eski kartın seri numarası 150210 KPS_VERIFICATION_FAILED verir.",
        placement: "left",
        actions: [{ type: "fill", target: "mtn-serial", value: "A01Z00000" }],
      },
      {
        target: "mtn-verify",
        title: "Kimlik doğrulandı",
        content: "Güncel seri numarasıyla KPS doğrulaması başarılı (demo modunda sentetik yanıt).",
        placement: "left",
        actions: [{ type: "click", target: "mtn-verify" }],
      },
    ],
  },
  {
    id: "mtn-mukerrer-musteri",
    title: "Müşteri zaten kayıtlı",
    description: "Başka şubede tanımlanmış müşteri için yeni kayıt açılamaz (150220); mevcut kayıtla devam edilir.",
    screen: "MUSTTANM",
    outcome: "info",
    match: { screen: "MUSTTANM", errorNumber: 150220, errorCode: "CUSTOMER_ALREADY_EXISTS" },
    steps: [
      {
        target: "mtn-identity",
        title: "Kimlik bilgileri",
        content: "Müşterinin kimlik bilgileri giriliyor.",
        placement: "left",
        actions: [
          { type: "fill", target: "mtn-tckn", value: "10000000146" },
          { type: "fill", target: "mtn-birth-date", value: "1990-05-15" },
          { type: "fill", target: "mtn-first-name", value: "Ayşe" },
          { type: "fill", target: "mtn-last-name", value: "Yılmaz" },
        ],
      },
      {
        target: "mtn-verify",
        title: "Kayıtlı müşteri bulundu",
        content: "Doğrulama sırasında bu kimlikle kayıtlı bir müşteri bulundu (150220 CUSTOMER_ALREADY_EXISTS). Yeni kayıt açılmaz.",
        placement: "left",
        actions: [{ type: "click", target: "mtn-verify" }],
      },
      {
        target: "mtn-existing-customer",
        title: "Mevcut kayıtla devam",
        content: "Bilgileri değişmişse Müşteri Bilgileri Güncelleme (MUSTGUNC) ekranından güncellenir. Çağrı açmaya gerek yok.",
        placement: "left",
      },
    ],
  },
  {
    id: "krt-basvuru-eksik",
    title: "Kart başvurusunda iş bilgileri",
    description: "Çalışma durumu, meslek ve işyeri boş bırakılırsa başvuru gönderilemez (130101).",
    screen: "KRTTBASV",
    outcome: "success",
    match: { screen: "KRTTBASV", errorNumber: 130101, errorCode: "VALIDATION_ERROR" },
    steps: [
      {
        target: "krt-products",
        title: "Kart seçimi",
        content: "Müşteri Klasik kartı seçiyor.",
        actions: [{ type: "click", target: "krt-product-classic" }],
      },
      {
        target: "krt-employment",
        title: "Çalışma ve iş bilgileri",
        content: "Çalışma durumu, meslek ve işyeri zorunlu. En sık atlanan bölüm bu; boş kalırsa başvuru 130101 VALIDATION_ERROR ile döner.",
        placement: "left",
        actions: [
          { type: "fill", target: "krt-employment-status", value: "Ücretli" },
          { type: "fill", target: "krt-occupation", value: "Öğretmen" },
          { type: "fill", target: "krt-employer", value: "Örnek Eğitim Kurumu" },
        ],
      },
      {
        target: "krt-income",
        title: "Gelir ve limit",
        content: "Aylık net gelir 28.000 ₺, talep edilen limit 20.000 ₺.",
        actions: [
          { type: "fill", target: "krt-income", value: "28000" },
          { type: "fill", target: "krt-limit", value: "20000" },
        ],
      },
      {
        target: "krt-consents",
        title: "Onaylar",
        content: "KVKK ve ön bilgilendirme onayları işaretleniyor.",
        placement: "left",
        actions: [
          { type: "check", target: "krt-kvkk" },
          { type: "check", target: "krt-preinfo" },
        ],
      },
      {
        target: "krt-result",
        title: "Başvuru gönderildi",
        content: "Zorunlu alanlar tamam olduğu için başvuru alındı.",
        actions: [{ type: "click", target: "krt-submit" }],
      },
    ],
  },
  {
    id: "krt-kesim-gunu",
    title: "Hesap kesim günü aralığı",
    description: "Hesap kesim günü yalnızca 1–28 arasında seçilebilir; 29–31 girilirse 130102 alınır.",
    screen: "KRTTGUNC",
    outcome: "success",
    match: { screen: "KRTTGUNC", errorNumber: 130102, errorCode: "VALIDATION_ERROR" },
    steps: [
      {
        target: "krt-cards",
        title: "Kart seçimi",
        content: "1137 numaralı kart seçiliyor.",
        placement: "left",
        actions: [{ type: "click", target: "krt-card-1137" }],
      },
      {
        target: "krt-statement-day",
        title: "Hesap kesim günü",
        content: "Müşteri ay sonu istiyor. 31 girilirse 130102 VALIDATION_ERROR alınır; seçilebilecek en geç gün 28.",
        placement: "left",
        actions: [{ type: "fill", target: "krt-statement-day", value: "28" }],
      },
      {
        target: "krt-consents",
        title: "Onaylar",
        content: "KVKK ve güncelleme talimatı onayları işaretleniyor.",
        placement: "left",
        actions: [
          { type: "check", target: "krt-kvkk" },
          { type: "check", target: "krt-consent" },
        ],
      },
      {
        target: "krt-result",
        title: "Güncellendi",
        content: "Hesap kesim günü 28 olarak kaydedildi.",
        actions: [{ type: "click", target: "krt-submit" }],
      },
    ],
  },
  {
    id: "krd-vade-siniri",
    title: "Vade ürün sınırının dışında",
    description: "İhtiyaç kredisinde vade 3–36 ay arasıdır; 48 ay girilirse 120101 alınır.",
    screen: "KRDTKULL",
    outcome: "success",
    match: { screen: "KRDTKULL", errorNumber: 120101, errorCode: "VALIDATION_ERROR" },
    steps: [
      {
        target: "krd-customer",
        title: "Müşteri",
        content: "Müşteri numarası 10000006 (Kerem Aydın, gelir 98.000 ₺).",
        placement: "right",
        actions: [{ type: "fill", target: "krd-customer", value: "10000006" }],
      },
      {
        target: "krd-amount",
        title: "Kredi tutarı",
        content: "Kredi tutarı 200.000 ₺.",
        placement: "right",
        actions: [{ type: "fill", target: "krd-amount", value: "200000" }],
      },
      {
        target: "krd-term",
        title: "Vade sınırı",
        content: "Müşteri 48 ay istiyor, ancak ürünün en uzun vadesi 36 ay; 48 girilirse 120101 VALIDATION_ERROR alınır. Vade 36 ay seçiliyor.",
        placement: "right",
        actions: [{ type: "fill", target: "krd-term", value: "36" }],
      },
      {
        target: "krd-summary",
        title: "Kredi özeti",
        content: "Taksit ve toplam geri ödeme 36 aya göre hesaplandı; uygunluk kontrolü geçiyor.",
      },
    ],
  },
  {
    id: "tah-taksit-sirasi",
    title: "Taksitler sırayla tahsil edilir",
    description: "Gecikmedeki taksit dururken sonraki taksit seçilirse 120102 alınır; en eski taksitten başlanır.",
    screen: "KRDTTAHS",
    outcome: "success",
    match: { screen: "KRDTTAHS", errorNumber: 120102, errorCode: "VALIDATION_ERROR" },
    steps: [
      {
        target: "tah-customer",
        title: "Müşteri arama",
        content: "Müşteri numarası 10000005 ile aranıyor.",
        placement: "bottom",
        actions: [
          { type: "fill", target: "tah-customer", value: "10000005" },
          { type: "click", target: "tah-search" },
        ],
      },
      {
        target: "tah-loans",
        title: "Kredi seçimi",
        content: "Gecikmedeki kredi KRD00006571 seçiliyor.",
        placement: "left",
        actions: [{ type: "click", target: "tah-loan-KRD00006571" }],
      },
      {
        target: "tah-installments",
        title: "En eski taksit",
        content: "Müşteri 5. taksiti ödemek istiyor, ancak 4. taksit (vade 12.10.2026) gecikmede. 5. seçilirse 120102 VALIDATION_ERROR alınır; önce 4. taksit seçiliyor.",
        placement: "left",
        actions: [{ type: "click", target: "tah-installment-4" }],
      },
      {
        target: "tah-late-fee",
        title: "Gecikme faizi",
        content: "4. taksitin gecikme faizi tutara ekleniyor. Tahsilattan sonra 5. taksit seçilebilir.",
        placement: "left",
      },
    ],
  },

  // --- Genel ------------------------------------------------------------------
  {
    id: "ekran-kodu",
    title: "Ekran koduyla işlem açma",
    description: "Ekran kodu çubuğundan ODMTTLMT yazılarak fatura talimat ekranına geçilir.",
    screen: null,
    outcome: "info",
    match: null,
    steps: [
      {
        target: "code-bar-input",
        title: "Ekran kodu",
        content: "Her işlem ekranının 8 karakterlik bir kodu var: modül (3) + tip T/R (1) + işlem (4). ODMTTLMT yazılıyor.",
        actions: [{ type: "fill", target: "code-bar-input", value: "ODMTTLMT" }],
      },
      {
        target: "odm-category",
        title: "Fatura Talimat Bilgileri Giriş ekranı",
        content: "Enter'a basınca ilgili ekran açıldı. Menüde gezinmeden doğrudan işleme geçilebilir.",
        actions: [{ type: "click", target: "code-bar-submit" }],
      },
    ],
  },
];
