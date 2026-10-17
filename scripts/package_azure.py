"""Azure App Service için iki zip paketi üretir: dist/mercek-api.zip ve dist/mercek-web.zip.

Kullanım (repo kökünden):
    python scripts/package_azure.py --api-url https://<api-uygulama-adi>.azurewebsites.net

- mercek-api.zip: backend/app + requirements.txt (uv export) + data/ (datav2 JSON'ları) + prompts/.
  App Service (Python) zip'i açar, SCM_DO_BUILD_DURING_DEPLOYMENT=true ile requirements'ı kurar.
- mercek-web.zip: Next.js standalone çıktısı (server.js) + .next/static + public.
  NEXT_PUBLIC_API_URL build anında koda gömülür; bu yüzden --api-url zorunlu.

Gizli bilgi içermez; anahtarlar App Settings'te tanımlanır.
"""

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
BUILD = ROOT / "build"
DIST = ROOT / "dist"

# Backend'in okuduğu veri dosyaları (backend/app/repositories/datav2.py)
DATA_FILES = [
    "kibana_logs.json",
    "incidents.json",
    "solution_templates.json",
    "screens.json",
    "institutions.json",
    "institution_screens.json",
]


def run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    executable = shutil.which(command[0])
    if executable is None:
        sys.exit(f"Bulunamadı: {command[0]} (PATH'te olmalı)")
    print(f"> {' '.join(command)}  (klasör: {cwd.relative_to(ROOT)})")
    subprocess.run([executable, *command[1:]], cwd=cwd, env=env, check=True)


def zip_dir(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source).as_posix())
    print(f"✓ {target.relative_to(ROOT)} ({target.stat().st_size // 1024} KB)")


def ignore_cache(_dir: str, names: list[str]) -> list[str]:
    return [n for n in names if n in {"__pycache__", ".pytest_cache", ".ruff_cache"}]


def package_api() -> None:
    out = BUILD / "api"
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(BACKEND / "app", out / "app", ignore=ignore_cache)
    (out / "data").mkdir(parents=True)
    for name in DATA_FILES:
        shutil.copy2(ROOT / "datav2" / name, out / "data" / name)
    shutil.copytree(ROOT / "prompts", out / "prompts")
    run(
        [
            "uv",
            "export",
            "--no-dev",
            "--no-hashes",
            "--no-emit-project",
            "-o",
            str(out / "requirements.txt"),
        ],
        BACKEND,
    )
    zip_dir(out, DIST / "mercek-api.zip")


def build_id() -> str:
    """git kısa commit + paketleme zamanı, ör. 58a9741 · 17.10 06:20."""
    git = shutil.which("git")
    commit = "?"
    if git:
        result = subprocess.run(
            [git, "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True
        )
        commit = result.stdout.strip() or "?"
    return f"{commit} · {datetime.now().strftime('%d.%m %H:%M')}"


def package_web(api_url: str) -> None:
    env = {
        **os.environ,
        "NEXT_PUBLIC_API_URL": api_url.rstrip("/"),
        "NEXT_PUBLIC_BUILD_ID": build_id(),
    }
    print(f"Sürüm: {env['NEXT_PUBLIC_BUILD_ID']} (ekranın sol üstünde görünür)")
    run(["npm", "ci"], FRONTEND, env)
    run(["npm", "run", "build"], FRONTEND, env)
    standalone = FRONTEND / ".next" / "standalone"
    if not (standalone / "server.js").exists():
        sys.exit("server.js yok: next.config.ts içinde output: 'standalone' olmalı")
    out = BUILD / "web"
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(standalone, out)
    shutil.copytree(FRONTEND / ".next" / "static", out / ".next" / "static")
    if (FRONTEND / "public").is_dir():
        shutil.copytree(FRONTEND / "public", out / "public")
    zip_dir(out, DIST / "mercek-web.zip")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--api-url", help="Backend adresi, ör. https://mercek-api-xyz.azurewebsites.net"
    )
    parser.add_argument("--only", choices=["api", "web"], help="Yalnızca bir paketi üret")
    args = parser.parse_args()
    if args.only != "web":
        package_api()
    if args.only != "api":
        if not args.api_url:
            sys.exit("--api-url gerekli (frontend paketine gömülür)")
        package_web(args.api_url)


if __name__ == "__main__":
    main()
