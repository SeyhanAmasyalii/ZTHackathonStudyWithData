"""Çözüm akışı bağlantıları: eşleşen hazır çözümün ekran turu (incidents.scenario_path).

Bağlantıyı model yazmaz; kod, bu turdaki araç sonuçlarından (cagri_ara'nın kapanmış çağrı
çözümleri, benzer_cozum_ara'nın eşiği geçen sonuçları) seçer ve yalnızca veride kayıtlı, https
adresleri döner. Frontend cevabın altında "Akışı izle" bağlantısı olarak gösterir.
"""

from collections.abc import Iterable
from typing import Any
from urllib.parse import urlparse

from app.repositories.datav2 import Incident

MAX_LINKS = 2


def safe_url(value: str | None) -> str | None:
    """Yalnızca https, kullanıcı adı/parola içermeyen, mutlak adresler."""
    if not value or len(value) > 1000:
        return None
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return None
    return parsed.geturl()


def scenario_map(incidents: Iterable[Incident]) -> dict[str, str]:
    """Hazır çözüm → akış adresi (o çözümle kapanmış çağrılarda kayıtlı ilk geçerli adres)."""
    mapping: dict[str, str] = {}
    for incident in incidents:
        template_id = incident.solution_template_id
        if not template_id or template_id in mapping:
            continue
        url = safe_url(incident.scenario_path)
        if url:
            mapping[template_id] = url
    return mapping


def scenario_links(
    trace: list[tuple[str, dict[str, Any]]], mapping: dict[str, str]
) -> list[dict[str, str]]:
    """Bu turda önerilen çözümlerin akış bağlantıları (en yeni araç sonucundan başlayarak)."""
    candidates: list[tuple[str, str]] = []
    for name, result in reversed(trace):
        if "error" in result:
            continue
        if name == "cagri_ara":
            candidates += [
                (item.get("solution_template_id") or "", item.get("title") or "")
                for item in result.get("by_solution", [])
            ]
        elif name == "benzer_cozum_ara":
            candidates += [
                (item.get("solution_template_id") or "", item.get("title") or "")
                for item in result.get("results", [])
                if item.get("above_threshold")
            ]
    links: list[dict[str, str]] = []
    for template_id, title in candidates:
        url = mapping.get(template_id)
        if url and all(link["solution_template_id"] != template_id for link in links):
            links.append({"solution_template_id": template_id, "title": title, "url": url})
        if len(links) == MAX_LINKS:
            break
    return links
