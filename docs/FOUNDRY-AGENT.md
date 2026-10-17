# Mercek — Foundry Agent Service (agent ile çalıştırma)

> Hedef: backend modeli doğrudan çağırmak yerine Foundry'de tanımlı **Mercek çağrı agent'ını** (`mercek-cagri`; ileride modül başına bir agent: ör. `mercek-talep`) çağırsın.
> Araçlar (`kibana_sorgula`, `cagri_ara`, `hata_ara`, `benzer_cozum_ara`) **yine backend'de** çalışır: agent hangi aracı
> çağıracağına karar verir, sayım/eşik/müşteri listesi kodda kalır. Geri dönüş tek ayar: `LLM_MODE=chat`.

## Nasıl çalışır

```
Kullanıcı → backend (KVKK, oturum) → Foundry agent "mercek-cagri" (talimat + araç tanımları, model gpt-5.5)
                                       ↓ function_call (ör. kibana_sorgula)
                                     backend aracı çalıştırır → function_call_output → agent → cevap
```

- **Talimat** `prompts/mercek-chat.md`'den gelir; portalda elle yazılmaz. `scripts/setup_agent.py` agent'ın yeni sürümünü oluşturur.
  Saat ve kullanıcının görevi her turda ayrı bir **BAĞLAM** mesajıyla gider (kullanıcı kodu gitmez).
- **Hafıza:** model önceki turları Foundry'den hatırlar (`previous_response_id`; konuşmanın son cevap kimliği SQL'de
  `conversations.agent_response_id`). Foundry kaydı bulunamazsa SQL'deki son 20 mesaj yeniden gönderilir.
- **SQL'de kalanlar:** ekranda görünen mesajlar (sayfa yenilenince geri gelir), konuşmanın sahibi (yalnızca sahibi görür),
  L2 "Etkilenen müşteriler" düğmesi, `audit_log`. Araç adımları Foundry'deki izde (tracing) görünür.
- Foundry'nin hazır AI Search aracı **kullanılmaz**: %75 eşiği ve skor hesabı bizim araçlarımızda.

Aşağıda `<foundry>` = Foundry kaynağı (ör. `seyhanamasyali-7898-resource`), `<proje>` = Foundry projesi, `<api>` = backend App Service.

## 1. Foundry projesi ve endpoint (5 dk)

1. `https://ai.azure.com` → aynı hesapla giriş → üstteki seçiciden `<foundry>` altındaki projeyi seçin
   (yoksa **+ Yeni proje / Create project**, kaynak `<foundry>`).
2. Projenin **Genel bakış / Overview** sayfası → **Proje uç noktası / Project endpoint**:
   `https://<foundry>.services.ai.azure.com/api/projects/<proje>`
3. **Modeller + uç noktalar** altında `gpt-5.5` dağıtımı görünmeli (agent'ın modeli `CHAT_DEPLOYMENT` ile aynı ad).

## 2. Yetki: kendi hesabınız (yerelde kurulum ve deneme için)

Agent SDK'sı **yalnızca Microsoft Entra** ile çalışır (anahtar yok).
- Azure portal → `<foundry>` (Foundry kaynağı) → **Erişim denetimi (IAM)** → **+ Ekle → Rol ataması ekle** →
  rol: **Azure AI User** (listede yoksa **Azure AI Developer**; aramaya `Azure AI` yazın) → Üyeler: **Kullanıcı, grup…** → kendi hesabınız →
  **Gözden geçir + ata**. Kaynağın sahibiyseniz (Owner) genelde gerekmez; `setup_agent.py` 403 verirse bu rolü ekleyin.
- Bilgisayarda Azure CLI yoksa: `winget install -e --id Microsoft.AzureCLI` → **yeni** CMD penceresi açın.
- Giriş: `az login --tenant <kiracı-kimliği>` (kiracı kimliği: portal → Microsoft Entra ID → Genel Bakış → Kiracı Kimliği).
  Yalnızca `az login` "MFA gerekli … No subscriptions found" derse kiracıyı vererek tekrar girin; MFA tarayıcıda tamamlanır.
  Tarayıcı açılmazsa: `az login --tenant <kiracı-kimliği> --use-device-code`.
  Kontrol: `az account show --query "{abonelik:name, kiraci:tenantId}" -o table`.

## 3. Agent'ı kur (bilgisayarda, repo kökünde, 1 dk)

`backend\.env`'e ekleyin:
```
FOUNDRY_PROJECT_ENDPOINT=https://<foundry>.services.ai.azure.com/api/projects/<proje>
FOUNDRY_AGENT_NAME=mercek-cagri
```
```cmd
git pull
uv sync --directory backend
uv run --directory backend python ..\scripts\setup_agent.py
```
Beklenen:
```
✓ Agent 'mercek-cagri' sürüm 1 · model gpt-5.5 · araçlar: kibana_sorgula, cagri_ara, hata_ara, benzer_cozum_ara
Deneme: Ben Mercek; ... kibana_sorgula, cagri_ara ... araçlarını kullanabilirim.
```
Araç listesi `.env`'deki AI Search ayarlarına göre çıkar (`SEARCH_ENDPOINT`, `SEARCH_SOLUTION_INDEX`).
**Prompt ya da araç değişince betiği tekrar çalıştırın** (yeni sürüm oluşur, backend en son sürümü kullanır).

Portalda kontrol: `https://ai.azure.com` → üstte proje (`<proje>`) → sol menü **Aracılar** → `mercek-cagri`
(yeşil tik = hazır). Sekmeler: **Deneme alanı · Ayrıntılar · İzlemeler · İçgörüler · İzleme · Değerlendirme · İyileştir**.
**Ayrıntılar**'da talimat ve araçlar görünür. Buradan **düzenlemeyin / Kaydet'e basmayın**: betik bir sonraki çalışmada yeni sürümle ezer.
> **Deneme alanı**'nda agent'a soru sorulabilir ama araçlarımız orada **çalışmaz** (araçları backend çalıştırır); agent araç
> çağırmak istediğinde portal sonucu bekler. Gerçek deneme Mercek arayüzünden yapılır.

## 4. Yerelde agent modunda dene

`backend\.env`'e: `LLM_MODE=agent` → backend'i yeniden başlatın (`uv run uvicorn app.main:app --reload --port 8000`).
- Elif → "ODMTTLMT ekranında hata alıyorum" → aynı cevap (7 hata, GAZ02 110731, SOL-031); terminalde `Araç çağrısı: ... ad=kibana_sorgula`.
- Aynı sohbette "Peki nasıl çözerim?" → önceki konuyu hatırlar (geçmiş gönderilmeden, Foundry'den).
- F5 → konuşma ekrana geri gelir (SQL).
- Terminalde `AGENT'A GİDEN` blokları yalnızca `LLM_DEBUG=true` iken görünür; ikinci soruda `"previous_response_id": "resp_…"` dolu olmalı.
  Deneme bitince `LLM_DEBUG` satırını silin (kullanıcı mesajlarını da loglar; Azure'da hep kapalı).

### 4.1 Foundry'de izleme (jüriye gösterilecek ekran, 5 dk, bir kez)

Agent'ın çalıştırma ve belirteç (token) sayıları **İzleme** sekmesinde kendiliğinden görünür ("Aracı çalıştırmaları",
"Toplam belirteç kullanımı"). Her konuşmanın adım adım izi (hangi araç, hangi sırayla, kaç saniye) için **Application Insights** bağlanır:

1. ai.azure.com → **Aracılar** → `mercek-cagri` → **İzleme** sekmesi → üstteki "Başlamak için bir App Insights kaynağı oluşturun
   veya bağlayın" bandında **Bağla**.
2. Açılan **İzleyici ayarları** penceresi → *Application insights kaynak adı*: **Yeni kaynak oluştur** · *Ad*: `mercek-appinsights` ·
   *Log Analytics Çalışma Alanı*: önerilen (varsayılan `…workspace-…`) · *Kimlik Doğrulama Türü*: **Proje Yönetilen Kimliği** (anahtarsız; prova seçimi) ya da listede **Microsoft Entra ID**
   varsa onu, yoksa **API Anahtarı** (anahtar Foundry'nin bağlantısında saklanır, repoya/koda girmez) → **Oluştur**.
   Var olan bir Application Insights varsa listeden onu seçin. (Kullandıkça ödenir; demo hacminde maliyet ihmal edilebilir.)
   - Pencerenin altındaki **gizlilik bildirimi**: izlerde kullanıcı mesajları ve araç sonuçları saklanır; projede
     *Log Analytics Reader* rolü olan herkes görür. Mercek'te araç sonuçlarında kişisel veri yok ve kullanıcı metni Foundry'ye
     gitmeden taranıyor; yine de bu rolü yalnızca takıma verin (KVKK).
3. Mercek'te birkaç soru sorun → 2–5 dk sonra **İzlemeler** sekmesi: her çalıştırma satırına tıklayınca girdiler, `function_call`
   (ör. `kibana_sorgula`), backend'in döndürdüğü `function_call_output` ve cevap sırayla görünür.
   **İzleme** sekmesinde çalıştırma sayısı, gecikme, belirteç ve hata oranı grafikleri.
4. **Değerlendirme** sekmesi (isteğe bağlı): otomatik kalite/güvenlik değerlendirmesi planlanabilir; demo için şart değil.

Not: araç sonuçları (ör. log sayıları) izde görünür; içerikte kişisel veri yoktur (araçlar müşteri bilgisi döndürmez,
etkilenen müşteri listesi modele gitmez).

Eski yola dönmek: `LLM_MODE=chat` (ya da satırı silin) → yeniden başlatın.

## 5. Azure'a (App Service)

1. **Kimlik yetkisi:** `<foundry>` → **Erişim denetimi (IAM)** → **Rol ataması ekle** → **Azure AI User**
   (portal listesinde yoksa — prova portalında çıkmadı — **Azure AI Developer**; 403 sürerse ek olarak **Cognitive Services User**) →
   Erişim ata: **Yönetilen kimlik** → **App Service** → `<api>` → **Gözden geçir + ata** (5–10 dk'da etkinleşir).
2. `<api>` → **Ayarlar → Ortam değişkenleri** → ekleyin → **Uygula**:

   | Ad | Değer |
   |---|---|
   | `LLM_MODE` | `agent` |
   | `FOUNDRY_PROJECT_ENDPOINT` | `https://<foundry>.services.ai.azure.com/api/projects/<proje>` |
   | `FOUNDRY_AGENT_NAME` | `mercek-cagri` |

   `AZURE_OPENAI_*` kalsın (geri dönüş için).
3. API paketini yeniden yükleyin (yeni paket `azure-ai-projects`): `docs/AZURE-APP-SERVICE.md` (yalnızca API).
4. SQL'de yeni kolon: `uv run --directory backend python ..\scripts\setup_app_tables.py` (bir kez; `agent_response_id` eklenir).
5. Kontrol: Günlük akışında `ManagedIdentityCredential` + `Araç çağrısı`; cevap gelir.

## Sorun giderme

| Belirti | Çözüm |
|---|---|
| `'az' is not recognized` | Azure CLI kurulu değil ya da kurulumdan sonra yeni CMD açılmadı (§2) |
| `az login`: `AADSTS50076 ... multi-factor authentication` / `No subscriptions found` | `az login --tenant <kiracı-kimliği>` ile MFA'yı tamamlayın (§2) |
| `setup_agent.py`: `DefaultAzureCredential failed to retrieve a token` | `az login` yapılmamış |
| Sohbette "Şu an yanıt üretilemiyor", günlükte `400 ... Invalid value: ''. Supported values are: 'additional_tools', ...` | Eski kod: agent girdilerinde `type` yok. `git pull` (düzeltildi) |
| `setup_agent.py`: `✗ Agent oluşturulamadı: 403` | Hesabınızda `<foundry>` üzerinde **Azure AI User** yok (§2) ya da yanlış kiracıdasınız |
| `✗ Agent oluşturulamadı: 404` | `FOUNDRY_PROJECT_ENDPOINT` yanlış (sonunda `/api/projects/<proje>` olmalı) |
| `... deployment ... not found` | Projede `gpt-5.5` dağıtımı yok ya da `CHAT_DEPLOYMENT` adı farklı |
| Sohbette "Şu an yanıt üretilemiyor", günlükte `Agent çağrısı başarısız: PermissionDeniedError` | App Service kimliğine Azure AI User verilmemiş/etkinleşmemiş (§5.1) |
| Günlükte `Agent yapılandırması eksik: Eksik ortam değişkeni: FOUNDRY_PROJECT_ENDPOINT` | §5.2 ayarı eksik |
| Günlükte `Agent önceki cevabı bulamadı; geçmiş yeniden gönderiliyor` | Sorun değil: Foundry kaydı yoktu, SQL'deki geçmişle devam edildi |
| Agent modunda sorun ve demo yaklaşıyor | `LLM_MODE=chat` → Uygula (uygulama yeniden başlar), her şey eski yolla çalışır |
