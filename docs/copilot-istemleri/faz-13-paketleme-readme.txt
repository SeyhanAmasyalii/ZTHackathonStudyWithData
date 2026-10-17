- scripts/package_azure.py --api-url https://<api-adres> [--only api|web]:
  mercek-api.zip = backend/app + requirements.txt (uv export --no-dev --no-hashes) + data/ (backend'in okuduğu datav2 JSON'ları) + prompts/.
  mercek-web.zip = Next.js standalone (server.js) + .next/static + public. Build sırasında NEXT_PUBLIC_API_URL ve
  NEXT_PUBLIC_BUILD_ID ("<git kısa commit> · gg.aa ss:dd") gömülür; çıktıda sürüm yazdırılır. Gizli bilgi içermez.
- Frontend: home.tsx başlığın altında küçük "sürüm <BUILD_ID>" (Azure'da hangi sürümün çalıştığı görülür).
- README.md: amaç, mimari şema (Next.js → FastAPI → SQL / AI Search / Foundry agent), her Azure kaynağının amacı, yerel çalıştırma,
  testler, ortam değişkenleri tablosu (değer yok), rehber bağlantıları (docs/HACKATHON-KURULUM.md).
- Yükleme Cloud Shell'den: az webapp deploy … --type zip; frontend her zaman --clean true + az webapp restart.

Kabul: paketler üretilir; Azure'da /api/health 200, sayfanın sol üstünde paketlemedeki sürüm; docs/HACKATHON-KURULUM.md §9 kontrolleri geçer.
