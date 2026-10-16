# Mercek — Azure App Service'e yükleme (portal ile)

> Hedef: `mercek-api` (FastAPI) ve `mercek-web` (Next.js) Azure'da çalışsın; `https://<api>/api/health` → 200.
> Kaynaklar **portaldan** açılır ve ayarlanır. Kodu paketlemek için tek komut (`scripts/package_azure.py`), yüklemek için tarayıcıda sürükle-bırak (Kudu) yeterlidir. Azure CLI gerekmez.
> **Repoya hiçbir anahtar yazılmaz.** Anahtarlar yalnızca App Service → Ortam değişkenleri ekranına girilir.

## 0. Hazırlık (5 dk)

| Ne | Değer |
|---|---|
| Resource group | Takıma verilen resource group (hackathon kuralı: başka yerde kaynak açılmaz) |
| Bölge | Foundry kaynağıyla **aynı bölge** (ör. West Europe) |
| Uygulama adları | Azure genelinde benzersiz olmalı: `mercek-api-<takım>`, `mercek-web-<takım>` (ör. `mercek-api-aioverflow`) |
| Foundry | `chat` deploy'unun **uç noktası** ve **anahtarı** (Foundry → model → Uç noktayı görüntüle) |
| Bilgisayarda | Git, [uv](https://docs.astral.sh/uv/), Node.js 20+ (yerelde çalıştırırken kurulanlar) |

Aşağıda `<api>` = `mercek-api-<takım>`, `<web>` = `mercek-web-<takım>`.

## 1. App Service planı (3 dk)

Portal → **Kaynak oluştur** → **App Service planı**
- Resource group: takımınki · Ad: `mercek-plan` · İşletim sistemi: **Linux** · Bölge: Foundry ile aynı
- Fiyat: **Basic B1** (izin verilen en düşük ücretli plan; Free F1'de "Always On" yok)
  - Deneme için **Free F1** de olur: Always On yok (bir süre istek gelmezse uygulama uyur, ilk açılış 20–60 sn), günlük CPU kotası 60 dk. Bu durumda aşağıdaki "Always On" adımlarını atlayın.
- **Gözden geçir + oluştur**

## 2. Backend uygulaması `<api>` (5 dk)

Portal → **Kaynak oluştur** → **Web App**
- Ad: `<api>` · Yayımla: **Kod** · Çalışma zamanı yığını: **Python 3.12** · İşletim sistemi: Linux · Plan: `mercek-plan`
- **Oluştur** → kaynağa git

**Ayarlar → Yapılandırma → Genel ayarlar**
- Başlangıç komutu: `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Always On: **Açık** · HTTPS Only: **Açık** → Kaydet

**Ayarlar → Ortam değişkenleri → Uygulama ayarları** (her biri ayrı satır, sonra **Uygula**)

| Ad | Değer |
|---|---|
| `AZURE_OPENAI_ENDPOINT` | Foundry uç noktası (ör. `https://<kaynak>.openai.azure.com`) |
| `AZURE_OPENAI_API_KEY` | Foundry anahtarı |
| `CHAT_DEPLOYMENT` | `gpt-5.5` (Foundry'deki deploy adı) |
| `CORS_ORIGINS` | `https://<web>.azurewebsites.net` |
| `SESSION_SECRET` | Uzun rastgele bir metin. Üretmek için: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` (yüklemede `requirements.txt` kurulur) |

İsteğe bağlı: `DEMO_NOW` (varsayılan `2026-10-17T09:15:00+03:00`), `LLM_DEBUG` (**Azure'da `false` kalmalı**).

**İzleme → Sistem durumu denetimi** → Etkinleştir → Yol: `/api/health` → Kaydet

## 3. Frontend uygulaması `<web>` (5 dk)

Portal → **Kaynak oluştur** → **Web App**
- Ad: `<web>` · Yayımla: **Kod** · Çalışma zamanı yığını: **Node 22 LTS** · Linux · Plan: `mercek-plan`

**Genel ayarlar**
- Başlangıç komutu: `node server.js`
- Always On: **Açık** · HTTPS Only: **Açık**

**Ortam değişkenleri**

| Ad | Değer |
|---|---|
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `false` (paket hazır gelir, yeniden derlenmez) |
| `HOSTNAME` | `0.0.0.0` |

**Sistem durumu denetimi** → Yol: `/giris`

## 4. Paketleri üret (bilgisayarda, 3 dk)

Repo kökünde (Windows CMD):

```cmd
cd /d <repo-klasörü>
git pull
python scripts\package_azure.py --api-url https://<api>.azurewebsites.net
```

Sonuç: `dist\mercek-api.zip` ve `dist\mercek-web.zip`. Backend adresi frontend paketine **bu adımda gömülür**; adres değişirse bu komut tekrar çalıştırılır.

> `python` yoksa: `uv run --directory backend python ..\scripts\package_azure.py --api-url ...`

## 5. Paketleri yükle (tarayıcıda sürükle-bırak, 5 dk)

1. Tarayıcıda `https://<api>.scm.azurewebsites.net/ZipDeployUI` (Azure hesabıyla açılır).
2. `dist\mercek-api.zip` dosyasını sayfadaki dosya listesinin üzerine **sürükle-bırak**. İlk yüklemede `requirements.txt` kurulur (2–4 dk); ilerleme sayfada görünür.
3. Aynısını `https://<web>.scm.azurewebsites.net/ZipDeployUI` için `dist\mercek-web.zip` ile yap.

> Alternatif (CLI varsa): `az webapp deploy -g <rg> -n <api> --src-path dist\mercek-api.zip --type zip`
> Kalıcı çözüm: CI/CD workflow'u (`.github/workflows/ci-cd.yml`) aynı zip'leri her main push'ta yükler.

## 6. Kontrol

| Adres | Beklenen |
|---|---|
| `https://<api>.azurewebsites.net/api/health` | `{"status":"ok"}` |
| `https://<api>.azurewebsites.net/api/users` | Elif, Zeynep, Kerem |
| `https://<web>.azurewebsites.net` | Giriş ekranı → Elif → "ODMTTLMT ekranında hata alıyorum" → Mercek cevabı |

## 7. Sorun giderme

| Belirti | Bakılacak yer / çözüm |
|---|---|
| `/api/health` açılmıyor, "Application Error" | `<api>` → **Günlük akışı (Log stream)**. `ModuleNotFoundError` ise `SCM_DO_BUILD_DURING_DEPLOYMENT=true` mi? Paketi tekrar yükle |
| Giriş ekranında "Sunucuya ulaşılamadı" | `--api-url` doğru mu (https, sonda `/` yok)? Tarayıcı konsolunda **CORS** hatası varsa `<api>` → `CORS_ORIGINS` = `https://<web>.azurewebsites.net` |
| "Model bağlantısı yapılandırılmamış" | `AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_API_KEY` eksik |
| "Şu an yanıt üretilemiyor" | Uç nokta, anahtar ya da `CHAT_DEPLOYMENT` adı yanlış; Log stream'deki `Model çağrısı başarısız` satırı |
| Arada bir "Oturum geçersiz" | `SESSION_SECRET` tanımlı değil (her yeniden başlatmada yeni anahtar üretilir) |
| `ZipDeployUI` erişim hatası | Hesabın bu kaynakta yetkisi yok; resource group sahibine sor ya da CLI ile `az webapp deploy` |
| Web 503 / açılmıyor | `<web>` Log stream; başlangıç komutu `node server.js` ve `HOSTNAME=0.0.0.0` mi? |

## Notlar

- **Veri:** backend paketinde `data/` (datav2 JSON'ları) ve `prompts/` bulunur; `DATA_DIR`/`PROMPTS_DIR` ayarlamak gerekmez.
- **Managed Identity (sonra):** anahtar yerine `<api>` → Kimlik → Sistem tarafından atanan **Açık** + Foundry'de **Cognitive Services OpenAI User** rolü. Kod şu an anahtarla çalışır.
- **README:** her Azure kaynağının amacı README'deki tabloya yazılmalı (hackathon kılavuzu).
