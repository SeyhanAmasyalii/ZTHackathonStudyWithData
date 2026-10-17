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
- [x] Konuşma geçmişi, kullanıcılar ve KVKK erişim kaydı Azure SQL'de (`app_users`, `audit_log`, `conversations`, `conversation_messages`); sayfa yenilenince sohbet geri gelir. Kurulum: `scripts/setup_app_tables.py`, rehber `docs/AZURE-SQL.md` §5
- [x] Cevap biçimlendirme: kalın, kod, madde/numaralı liste, başlık (bağımlılıksız, HTML çalıştırmaz)
- [x] Azure App Service (prova, kişisel abonelik, F1): `mercek-api`, `mercek-web` portaldan; paket `scripts/package_azure.py`, yükleme Cloud Shell. Rehber: `docs/AZURE-APP-SERVICE.md`
- [x] Azure SQL: datav2'nin 21 tablosu (+ `scenarios.ts`) tüm kolonlarıyla; şema `scripts/build_schema.py` → `db/schema.sql`, yükleme+doğrulama `scripts/load_sql.py`; backend `SQL_SERVER` varsa SQL'den okur (yoksa/ulaşamazsa JSON). Rehber: `docs/AZURE-SQL.md`

- [x] Etkilenen müşteri listesi (L2): cevabın altında düğme, `POST /api/affected-customers`; iletişim izni (izinsizde maske), veri en aza indirme, erişim kaydı; liste modele gitmez

## Sırada
- [x] Azure SQL App Service'e bağlandı (prova): Günlük akışında `Veri kaynağı: Azure SQL (mercekdb)`, sohbet SQL verisiyle çalışıyor
- [x] SQL'e Managed Identity ile şifresiz bağlantı (prova; App Settings'te SQL parolası yok). Rehber: `docs/AZURE-SQL.md` §4
- [ ] (Ek puan) Foundry'ye de Managed Identity ile bağlanma (anahtar yerine)
- [ ] Gerçek modelle anlam eşleştirme değerlendirmesi (15–20 cümle → beklenen ekran/kurum)

## Sonra
- [ ] `.github/workflows/ci-cd.yml` (arkadaş yapıyor)
- [x] Azure AI Search: `hata_ara` (loglar, `mercek-loglar`; SQL görünümünden indexer, 5 dk; SQL Basic) — prova: "abone numarasını sistem kabul etmiyor" → ODMTTLMT 110412, 165 kayıt, SOL-005 temkinli. Rehber: `docs/AZURE-AI-SEARCH.md`
- [x] (Ek puan) AI Search sorgusu Managed Identity ile (Search Index Data Reader, `SEARCH_API_KEY` yok; prova: `hata_ara` 200). Rehber: `docs/AZURE-AI-SEARCH.md` §5
- [x] Azure AI Search: `benzer_cozum_ara` (kod): 37 hazır çözüm + kapanmış çağrı notları tek indekste (`mercek-cozumler`, SQL görünümü `v_cozum_sablonlari`, 5 dk); eşleşme yüzdesi ve %75 eşiği kodda. Rehber: `docs/AZURE-AI-SEARCH.md` §6
- [ ] `benzer_cozum_ara` prova: indeksi kur, `--dene` ile eşik ölçeğini doğrula, App Service'e `SEARCH_SOLUTION_INDEX`
- [ ] Duyuru + işlenmemiş e-posta araması (tek indeks; Free'de 3. indeks)
- [ ] KVKK: modele gitmeden önce kişisel veri maskeleme
