# Mercek — Azure App Service'e yükleme (portal ile)

> Hedef: `mercek-api` (FastAPI) ve `mercek-web` (Next.js) Azure'da çalışsın; `https://<api>/api/health` → 200.
> Kaynaklar **portaldan** açılır ve ayarlanır. Kodu paketlemek için tek komut (`scripts/package_azure.py`), yüklemek için portaldaki Cloud Shell yeterlidir. Bilgisayara Azure CLI kurmak gerekmez.
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

> **Adres:** Oluştururken "Güvenli benzersiz varsayılan ana bilgisayar adı" **Etkin** ise (varsayılan) adres
> `mercek-api-<takım>-<rastgele>.<bölge>-01.azurewebsites.net` biçiminde olur. Gerçek adresi uygulamanın
> **Genel Bakış → Varsayılan etki alanı** satırından kopyalayın; aşağıda `<api>.azurewebsites.net` yazan her yerde
> (CORS, `--api-url`, `scm` adresi) bu adresi kullanın. Kudu adresi: `https://<ad>-<rastgele>.scm.<bölge>-01.azurewebsites.net`.
>
> **Temel kimlik doğrulaması kapalı** uyarısı sorun değil: Cloud Shell'deki `az webapp deploy` Azure hesabıyla girer.
> (CI/CD publish profile kullanacaksa bu ayar açılmalı ya da OIDC kullanılmalı.)

## 1. App Service planı (3 dk)

Portal → **Kaynak oluştur** → **App Service planı**
- Resource group: takımınki · Ad: `mercek-plan` · İşletim sistemi: **Linux** · Bölge: Foundry ile aynı
- Fiyat: **Basic B1** (izin verilen en düşük ücretli plan; Free F1'de "Always On" yok)
  - Deneme için **Free F1** de olur: Always On yok (bir süre istek gelmezse uygulama uyur, ilk açılış 20–60 sn), günlük CPU kotası 60 dk. Sistem durumu denetimi de B1 ister. Bu durumda aşağıdaki "Always On" ve "Sistem durumu denetimi" adımlarını atlayın (`/api/health` yine çalışır).
- **Gözden geçir + oluştur**

## 2. Backend uygulaması `<api>` (5 dk)

Portal → **Kaynak oluştur** → **Web App**
- Ad: `<api>` · Yayımla: **Kod** · Çalışma zamanı yığını: **Python 3.12** · İşletim sistemi: Linux · Plan: `mercek-plan`
- **Oluştur** → kaynağa git

**Ayarlar → Yapılandırma → Yığın ayarları** → **Önyükleme komutu** (başlangıç komutu): `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000` → Uygula

**Ayarlar → Yapılandırma → Genel ayarlar** → Always On: **Açık** · Yalnızca HTTPS: **Açık** → Uygula

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

**Yapılandırma → Sistem durumu denetimi** (ya da İzleme → Sistem durumu denetimi) → Etkinleştir → Yol: `/api/health` → Kaydet

## 3. Frontend uygulaması `<web>` (5 dk)

Portal → **Kaynak oluştur** → **Web App**
- Ad: `<web>` · Yayımla: **Kod** · Çalışma zamanı yığını: **Node 22 LTS** · Linux · Plan: `mercek-plan`

**Yapılandırma → Yığın ayarları** → Önyükleme komutu: `node server.js`
**Yapılandırma → Genel ayarlar** → Always On: **Açık** · Yalnızca HTTPS: **Açık**

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

## 5. Paketleri yükle (tarayıcıda Cloud Shell, 5 dk)

> Linux App Service'te Kudu'nun sürükle-bırak sayfası (`/ZipDeployUI`) **yok** ("No route registered"). Yükleme portalın içindeki Cloud Shell'den yapılır; bilgisayara kurulum gerekmez.

1. Portal üst çubuğu → **Cloud Shell** simgesi (`>_`) → **Bash** → "Depolama hesabı gerekmez" (geçici oturum) → Uygula.
2. Cloud Shell araç çubuğu → **Dosyaları yönet → Karşıya yükle** → `dist\mercek-api.zip` (sonra `dist\mercek-web.zip`).
3. Komutlar (`-n` uygulamanın **adı**dır, uzun adres değil):
   ```bash
   az webapp deploy -g <rg> -n <api> --src-path mercek-api.zip --type zip
   az webapp deploy -g <rg> -n <web> --src-path mercek-web.zip --type zip
   ```
   İlk backend yüklemesinde `requirements.txt` kurulur (2–4 dk).

> Bilgisayarda Azure CLI varsa aynı komutlar `--src-path dist\mercek-api.zip` ile çalışır.
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
| `az webapp deploy` yetki hatası | Hesabın bu kaynakta yetkisi yok; resource group sahibine sor |
| Web 503 / açılmıyor | `<web>` Log stream; başlangıç komutu `node server.js` ve `HOSTNAME=0.0.0.0` mi? |

## Notlar

- **Veri:** backend paketinde `data/` (datav2 JSON'ları) ve `prompts/` bulunur; `DATA_DIR`/`PROMPTS_DIR` ayarlamak gerekmez.
- **Managed Identity (sonra):** anahtar yerine `<api>` → Kimlik → Sistem tarafından atanan **Açık** + Foundry'de **Cognitive Services OpenAI User** rolü. Kod şu an anahtarla çalışır.
- **README:** her Azure kaynağının amacı README'deki tabloya yazılmalı (hackathon kılavuzu).
