# Mercek'i Copilot'a yazdırma — adım adım yol rehberi

> **Nerede:** hackathon bilgisayarı, kod dizini **`C:\Users\hackadmin\AIOverflow`**, git dalı **`seyhan`**.
> **Ne:** Mercek'in backend (FastAPI) ve frontend (Next.js) kodunu GitHub Copilot'a (Agent modu) faz faz yazdırmak.
> **Bu belgede:** 1) adım adım yol, 2) Ek A: sistem talimatı (`.github/copilot-instructions.md`), 3) Ek B: 14 faz istemi.
> Azure kurulumu ayrı belgede: `docs/HACKATHON-KURULUM.md` (aşağıda hangi fazdan önce hangi bölümün gerektiği yazılı).

---

## Adım 1 — Bilgisayar ve VS Code hazırlığı (15 dk)

1. CMD'de araçları kontrol edin; eksikse kurun (kurulumdan sonra **yeni** CMD açın):

   | Araç | Kontrol | Kurulum |
   |---|---|---|
   | Git | `git --version` | `winget install -e --id Git.Git` |
   | uv | `uv --version` | `winget install -e --id astral-sh.uv` |
   | Python 3.12 | `python --version` | `uv python install 3.12` |
   | Node.js 22 | `node --version` | `winget install -e --id OpenJS.NodeJS.LTS` |
   | Azure CLI | `az --version` | `winget install -e --id Microsoft.AzureCLI` |
   | VS Code | — | `winget install -e --id Microsoft.VisualStudioCode` |

2. VS Code → **Uzantılar** (Ctrl+Shift+X) → **GitHub Copilot** ve **GitHub Copilot Chat** kurulu olsun →
   sol alttaki hesap simgesinden GitHub'a giriş yapın (Copilot lisansı olan hesap).
3. Azure girişi (Faz 6'dan sonra gerekecek, şimdiden yapın): `az login --tenant <kiracı>` → MFA → hackathon aboneliği.

## Adım 2 — Repo ve `seyhan` dalı (5 dk)

CMD:
```cmd
cd /d C:\Users\hackadmin\AIOverflow
git status
git fetch origin
```
- Repo yoksa önce: `git clone <hackathon-repo-adresi> C:\Users\hackadmin\AIOverflow`
- **`seyhan` dalı uzakta varsa:** `git checkout seyhan` ve `git pull`
- **Yoksa** main'den açın:
  ```cmd
  git checkout main
  git pull
  git checkout -b seyhan
  git push -u origin seyhan
  ```
Kontrol: `git branch --show-current` → `seyhan`. Bütün fazlar bu dalda commit'lenir; main'e en sonda PR ile gider.

## Adım 3 — Girdileri kopyala (kod değil, Copilot'ın okuyacağı veri ve rehberler) (10 dk)

Girdiler prova reposunda (`SeyhanAmasyalii/ZTHackathonStudyWithData`, main dalı). Geçici bir klasöre indirip kopyalayın:
```cmd
cd /d C:\Users\hackadmin
git clone https://github.com/SeyhanAmasyalii/ZTHackathonStudyWithData.git mercek-prova
robocopy mercek-prova\datav2  AIOverflow\datav2  /E
robocopy mercek-prova\prompts AIOverflow\prompts mercek-chat.md
robocopy mercek-prova\docs    AIOverflow\docs    /E
```
- `robocopy` 0–7 arası çıkış kodlarında başarılıdır (kopyalanan dosya sayısını yazar).
- Prova reposu özel (private) ise önce hesabınıza erişim verilmeli; yoksa dosyaları zip olarak indirip aynı klasörlere koyun.
- **`prompts/mercek-chat.md` aynen kopyalanmalı**: Mercek'in davranışı bu dosyaya bağlı; Copilot onu yeniden yazmaz.
- Kod klasörlerini (`backend/`, `frontend/`, `scripts/`, `db/`) **kopyalamayın**; onları Copilot yazacak.

Kontrol: `dir AIOverflow\datav2\kibana_logs.json` ve `dir AIOverflow\prompts\mercek-chat.md` dosyaları görünmeli.

## Adım 4 — Sistem talimatını yerleştir (5 dk)

1. VS Code → **Dosya → Klasör Aç** → `C:\Users\hackadmin\AIOverflow`.
2. `.github\copilot-instructions.md` dosyasını açın (yoksa oluşturun: `.github` klasörü → Yeni Dosya).
   - Dosyada CodeQL / güvenlik / hackathon kuralları **varsa silmeyin**; **Ek A**'daki metni dosyanın **sonuna** ekleyin.
   - Yoksa Ek A'nın tamamını yapıştırın.
3. `.github\workflows\` altındaki CodeQL dosyasına **dokunmayın**.
4. Commit:
   ```cmd
   cd /d C:\Users\hackadmin\AIOverflow
   git add datav2 prompts docs .github\copilot-instructions.md
   git commit -m "Mercek girdileri: datav2, prompt, rehberler, Copilot talimatı"
   git push
   ```

## Adım 5 — Copilot Agent modunu aç (2 dk)

1. VS Code → **Copilot Chat** paneli (Ctrl+Alt+I) → üstteki mod seçiciden **Agent**.
2. Model seçicide en güçlü modeli seçin.
3. Copilot terminal komutu çalıştırmak istediğinde **Devam / Allow** deyin (testleri kendisi çalıştıracak).
   Her komutu okuyun: `git push`, dosya silme ya da `.env`'e yazma isterse reddedin.

## Adım 6 — Fazları sırayla çalıştır (her faz için aynı döngü)

Her faz için:
1. Copilot Chat'te **Yeni sohbet** (+ simgesi) açın.
2. Fazın istemini kopyalayıp yapıştırın → Enter. **En kolayı:** VS Code'da `docs\copilot-istemleri\faz-NN-….txt` dosyasını açın
   (Adım 3'te `docs` ile birlikte geldi) → Ctrl+A, Ctrl+C. PDF'teki (Ek B) metin de aynıdır, ama PDF'ten kopyalarken satır sonları kayabilir.
3. Copilot dosyaları yazar ve kontrolleri çalıştırır. Bittiğinde **son çıktıyı okuyun**: testler ve lint yeşil mi?
4. Fazın sonundaki **Kabul** satırını kendiniz deneyin (komut ya da tarayıcı).
5. Bir şey eksik ya da kırmızıysa **aynı sohbette** yazın:
   *"Kabul kriteri karşılanmadı: <hata çıktısını yapıştır>. Düzelt, testleri tekrar çalıştır ve çıktıyı göster."*
6. Yeşilse commit + push (CMD):
   ```cmd
   cd /d C:\Users\hackadmin\AIOverflow
   git add -A
   git status
   git commit -m "Faz N: <konu>"
   git push
   ```
   `git status` listesinde `.env` dosyası **olmamalı** (olursa commit etmeyin; `.gitignore`'u kontrol ettirin).
7. Sonraki faza geçin.

### Fazlar ve ön koşulları

| Faz | Konu | Önce gereken | Kabul nasıl denenir |
|---|---|---|---|
| 0 | Proje iskeleti | — | `cd backend && uv run pytest` · yeni CMD: `uv run uvicorn app.main:app --port 8000` → tarayıcı `http://localhost:8000/api/health` |
| 1 | datav2 kataloğu | — | `uv run pytest` |
| 2 | Demo girişi | — | `uv run pytest` · `http://localhost:8000/api/users` |
| 3 | Sohbet | Foundry modeli + `backend\.env`'de `AZURE_OPENAI_*` (Kurulum §2) | `uv run pytest` |
| 4 | Araçlar | Faz 3 | `uv run pytest` |
| 5 | Frontend | Faz 4 | backend açık + `cd frontend && npm run dev` → `http://localhost:3000` → Elif → "ODMTTLMT ekranında hata alıyorum" |
| 6 | Azure SQL | SQL sunucusu + `.env` SQL satırları (Kurulum §3.1–3.3) | `uv run --directory backend python ..\scripts\load_sql.py` |
| 7 | Uygulama tabloları | Faz 6 | `uv run --directory backend python ..\scripts\setup_app_tables.py` · sohbette F5 → konuşma geri gelir |
| 8 | Etkilenen müşteriler | Faz 7 | Kerem → K8 sorusu → "Etkilenen müşteriler (31)" |
| 9 | `hata_ara` | AI Search + `.env` SEARCH satırları + embedding modeli (Kurulum §4.1–4.3) | `uv run --directory backend python ..\scripts\build_search_index.py --indeks loglar` |
| 10 | `benzer_cozum_ara` | Faz 9 | `uv run --directory backend python ..\scripts\build_search_index.py --indeks cozumler` ve `--dene "…"` |
| 11 | Akışı izle | Faz 10 | E1 sorusu → "▶ Akışı izle · SOL-031" |
| 12 | Foundry agent | Foundry proje uç noktası + `az login` (Kurulum §2.4, §6) | `uv run --directory backend python ..\scripts\setup_agent.py` · `.env`'e `LLM_MODE=agent` → E1 |
| 13 | Paketleme, README | Hepsi | `python scripts\package_azure.py --api-url https://<api-adres>` |

Fazların tamamı ~7–8 saat sürer. Zaman darsa öncelik: **0 → 5** (çalışan sohbet), sonra **6–7**, **9–10**, **12**; 8 ve 11 en sona.

## Adım 7 — Yerelde çalıştırma (her faz denemesinde)

İki CMD penceresi:
```cmd
cd /d C:\Users\hackadmin\AIOverflow\backend
uv run uvicorn app.main:app --reload --port 8000
```
```cmd
cd /d C:\Users\hackadmin\AIOverflow\frontend
copy .env.example .env.local
npm run dev
```
Tarayıcı: `http://localhost:3000`. Deneme soruları ve beklenen cevaplar: `docs/MERCEK-TEST-SORULARI.md`.

## Adım 8 — Bitiş: PR ve Azure

1. Tüm fazlar yeşil → GitHub'da `seyhan` → `main` **Pull Request** açın; CodeQL ve CI kontrolleri geçince birleştirin.
2. Azure'a kurulum ve yükleme: `docs/HACKATHON-KURULUM.md` (§5 App Service, §7 roller, §8 ortam değişkenleri, §9 paketle-yükle, §10 kontrol).

## Copilot takıldığında

| Belirti | Ne yazmalı |
|---|---|
| Next.js 15 API'siyle yazdı, build hatası | "Next.js 16 kullanıyoruz. node_modules/next/dist/docs/ altındaki ilgili rehberi oku ve kodu ona göre düzelt." |
| Sayıyı model yazıyor / prompt'a sayı koydu | "Sistem talimatı: hesabı kod yapar. Sayıyı araç sonucundan al, kodda hesapla; prompt'tan kaldır." |
| SQL'i string birleştirerek yazdı | "Parametreli sorguya çevir (? parametreleri / OPENJSON). String birleştirme yok." |
| Anahtar/parola koda yazıldı | "Değeri sil, <PLACEHOLDER> yaz; değer ortam değişkeninden okunsun. git diff'te secret kalmadığını göster." |
| Test gerçek servisi çağırıyor | "Testte FakeLLMClient / FakeAgent / httpx.MockTransport kullan; ağ çağrısı olmasın." |
| Bağımlılığı sürümsüz ekledi | "Sürümü tam sabitle (==, package.json'da ^ yok) ve gerekçesini yaz." |
| `dangerouslySetInnerHTML` kullandı | "Kaldır; markdown.ts ayrıştırıcısıyla React öğeleri üret." |
| Fazı yarım bıraktı | "Kalan maddeleri listele, sırayla tamamla, sonunda tüm kontrolleri çalıştır ve çıktıyı göster." |
| Sohbet çok uzadı, saçmalıyor | Yeni sohbet açın, aynı faz istemini tekrar yapıştırın ve "Önceki denemede yazılan dosyalar var; eksikleri tamamla" ekleyin. |
