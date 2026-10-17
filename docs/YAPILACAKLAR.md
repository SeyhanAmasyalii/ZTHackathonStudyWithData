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
- [x] Cevap biçimlendirme: kalın, kod, madde/numaralı liste, başlık (bağımlılıksız, HTML çalıştırmaz)
- [x] Azure App Service (prova, kişisel abonelik, F1): `mercek-api`, `mercek-web` portaldan; paket `scripts/package_azure.py`, yükleme Cloud Shell. Rehber: `docs/AZURE-APP-SERVICE.md`
- [x] Azure SQL: `db/schema.sql`, `scripts/load_sql.py` (JSON → SQL), backend `SQL_SERVER` varsa SQL'den okur (yoksa/ulaşamazsa JSON). Rehber: `docs/AZURE-SQL.md`

## Sırada
- [ ] Azure SQL'i portalda açıp veriyi yükleme ve App Service'e bağlama (prova)
- [ ] Gerçek modelle anlam eşleştirme değerlendirmesi (15–20 cümle → beklenen ekran/kurum)

## Sonra
- [ ] Konuşma geçmişini sunucuda tutma (Azure SQL ile birlikte)
- [ ] `.github/workflows/ci-cd.yml` (arkadaş yapıyor)
- [ ] Azure AI Search: benzer çözüm arama aracı
- [ ] KVKK: modele gitmeden önce kişisel veri maskeleme
