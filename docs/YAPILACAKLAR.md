# Mercek — Yapılacaklar

Yeni sıfırdan başlanan sürüm (`frontend/`, `backend/`) için takip listesi. Tamamlanan madde `[x]` olur.

## Yapıldı
- [x] Backend: `POST /api/chat`, Foundry `gpt-5.5` bağlantısı
- [x] Frontend: tek sayfa Mercek sohbet ekranı
- [x] `kibana_sorgula` aracı: model kapsamı seçer, backend `datav2/kibana_logs.json`'da sorgular
- [x] Ekran ve kurumu anlamca seçme (açıklamalar + kurum listesi prompt'ta)
- [x] `LLM_DEBUG=true` ile modele giden/dönen içeriğin loglanması
- [x] `cagri_ara` aracı: geçmiş kapanmış çağrılar ve çözümleri → çözüm önerisi
- [x] Giriş ekranı: demo kullanıcı seçimi, imzalı oturum token'ı; sohbetteki kullanıcı token'dan
- [x] Konuşma hafızası (ilk sürüm): frontend son 20 mesajı gönderir, "Yeni sohbet" sıfırlar

## Sırada
- [ ] Frontend: cevaplardaki Markdown'ı biçimlendirme (`**kalın**`, madde işaretleri şu an düz metin görünüyor)

## Sonra
- [ ] Konuşma geçmişini sunucuda tutma (Azure SQL ile birlikte)
- [ ] Azure SQL: `datav2` JSON'larını SQL'e taşıma (`backend/app/repositories/datav2.py` yerine SQL deposu)
- [ ] Azure'a yükleme (App Service: `mercek-web`, `mercek-api`) ve `.github/workflows/ci-cd.yml`
- [ ] KVKK: modele gitmeden önce kişisel veri maskeleme
