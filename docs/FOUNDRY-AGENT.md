# Mercek — Foundry Agent Service (agent ile çalıştırma)

> Hedef: backend modeli doğrudan çağırmak yerine Foundry'de tanımlı **Mercek agent'ını** çağırsın.
> Araçlar (`kibana_sorgula`, `cagri_ara`, `hata_ara`, `benzer_cozum_ara`) **yine backend'de** çalışır: agent hangi aracı
> çağıracağına karar verir, sayım/eşik/müşteri listesi kodda kalır. Geri dönüş tek ayar: `LLM_MODE=chat`.

## Nasıl çalışır

```
Kullanıcı → backend (KVKK, oturum) → Foundry agent "mercek" (talimat + araç tanımları, model gpt-5.5)
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
  rol: **Azure AI User** (Türkçe portalda "Azure AI Kullanıcısı"; aramaya `Azure AI` yazın) → Üyeler: **Kullanıcı, grup…** → kendi hesabınız →
  **Gözden geçir + ata**. Kaynağın sahibiyseniz (Owner) genelde gerekmez; `setup_agent.py` 403 verirse bu rolü ekleyin.
- Bilgisayarda bir kez: `az login` (Azure CLI). Birden fazla kiracı varsa: `az login --tenant <kiracı-kimliği>`.

## 3. Agent'ı kur (bilgisayarda, repo kökünde, 1 dk)

`backend\.env`'e ekleyin:
```
FOUNDRY_PROJECT_ENDPOINT=https://<foundry>.services.ai.azure.com/api/projects/<proje>
FOUNDRY_AGENT_NAME=mercek
```
```cmd
git pull
uv sync --directory backend
uv run --directory backend python ..\scripts\setup_agent.py
```
Beklenen:
```
✓ Agent 'mercek' sürüm 1 · model gpt-5.5 · araçlar: kibana_sorgula, cagri_ara, hata_ara, benzer_cozum_ara
Deneme: Ben Mercek; ... kibana_sorgula, cagri_ara ... araçlarını kullanabilirim.
```
Araç listesi `.env`'deki AI Search ayarlarına göre çıkar (`SEARCH_ENDPOINT`, `SEARCH_SOLUTION_INDEX`).
**Prompt ya da araç değişince betiği tekrar çalıştırın** (yeni sürüm oluşur, backend en son sürümü kullanır).

Portalda kontrol: ai.azure.com → proje → **Agents** → `mercek` → talimat ve araçlar görünür (buradan düzenlemeyin; betik ezer).

## 4. Yerelde agent modunda dene

`backend\.env`'e: `LLM_MODE=agent` → backend'i yeniden başlatın (`uv run uvicorn app.main:app --reload --port 8000`).
- Elif → "ODMTTLMT ekranında hata alıyorum" → aynı cevap (7 hata, GAZ02 110731, SOL-031); terminalde `Araç çağrısı: ... ad=kibana_sorgula`.
- Aynı sohbette "Peki nasıl çözerim?" → önceki konuyu hatırlar (geçmiş gönderilmeden, Foundry'den).
- F5 → konuşma ekrana geri gelir (SQL).
- ai.azure.com → proje → **Agents → mercek → Traces / İzleme** (ya da Konuşmalar): turlar ve araç çağrıları.

Eski yola dönmek: `LLM_MODE=chat` (ya da satırı silin) → yeniden başlatın.

## 5. Azure'a (App Service)

1. **Kimlik yetkisi:** `<foundry>` → **Erişim denetimi (IAM)** → **Rol ataması ekle** → **Azure AI User** →
   Erişim ata: **Yönetilen kimlik** → **App Service** → `<api>` → **Gözden geçir + ata** (5–10 dk'da etkinleşir).
2. `<api>` → **Ayarlar → Ortam değişkenleri** → ekleyin → **Uygula**:

   | Ad | Değer |
   |---|---|
   | `LLM_MODE` | `agent` |
   | `FOUNDRY_PROJECT_ENDPOINT` | `https://<foundry>.services.ai.azure.com/api/projects/<proje>` |
   | `FOUNDRY_AGENT_NAME` | `mercek` |

   `AZURE_OPENAI_*` kalsın (geri dönüş için).
3. API paketini yeniden yükleyin (yeni paket `azure-ai-projects`): `docs/AZURE-APP-SERVICE.md` (yalnızca API).
4. SQL'de yeni kolon: `uv run --directory backend python ..\scripts\setup_app_tables.py` (bir kez; `agent_response_id` eklenir).
5. Kontrol: Günlük akışında `ManagedIdentityCredential` + `Araç çağrısı`; cevap gelir.

## Sorun giderme

| Belirti | Çözüm |
|---|---|
| `setup_agent.py`: `DefaultAzureCredential failed to retrieve a token` | `az login` yapılmamış |
| `setup_agent.py`: `✗ Agent oluşturulamadı: 403` | Hesabınızda `<foundry>` üzerinde **Azure AI User** yok (§2) ya da yanlış kiracıdasınız |
| `✗ Agent oluşturulamadı: 404` | `FOUNDRY_PROJECT_ENDPOINT` yanlış (sonunda `/api/projects/<proje>` olmalı) |
| `... deployment ... not found` | Projede `gpt-5.5` dağıtımı yok ya da `CHAT_DEPLOYMENT` adı farklı |
| Sohbette "Şu an yanıt üretilemiyor", günlükte `Agent çağrısı başarısız: PermissionDeniedError` | App Service kimliğine Azure AI User verilmemiş/etkinleşmemiş (§5.1) |
| Günlükte `Agent yapılandırması eksik: Eksik ortam değişkeni: FOUNDRY_PROJECT_ENDPOINT` | §5.2 ayarı eksik |
| Günlükte `Agent önceki cevabı bulamadı; geçmiş yeniden gönderiliyor` | Sorun değil: Foundry kaydı yoktu, SQL'deki geçmişle devam edildi |
| Agent modunda sorun ve demo yaklaşıyor | `LLM_MODE=chat` → Uygula (uygulama yeniden başlar), her şey eski yolla çalışır |
