"""datav2 tablolarını okur, Azure SQL şemasını üretir (build_schema.py ve load_sql.py ortak).

- Tablo = `datav2/<ad>.json` (dizi). `*.stats.json` (özet) ve `kibana_logs_partNN.json`
  (aynı verinin parçaları) tablo değildir.
- `datav2/ui/scenarios.ts` (Joyride turları) çalıştırılmadan, nesne sabiti olarak ayrıştırılır →
  `scenarios` tablosu.
- Kolon tipleri veriden çıkarılır; boş tablolar (prevented_calls) SCHEMA.md'deki tanımla eklenir.
"""

import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "datav2"

# Boş başlayan tablolar: tip veriden çıkarılamaz (datav2/SCHEMA.md).
MANUAL_TABLES: dict[str, list[tuple[str, str]]] = {
    "prevented_calls": [
        ("prevented_id", "INT IDENTITY(1,1) NOT NULL PRIMARY KEY"),
        ("ts", "DATETIMEOFFSET(3) NULL"),
        ("user_name", "NVARCHAR(50) NULL"),
        ("screen_code", "NVARCHAR(20) NULL"),
        ("error_code", "NVARCHAR(100) NULL"),
        ("rule_id", "NVARCHAR(20) NULL"),
        ("kibana_correlation_id", "NVARCHAR(64) NULL"),
    ],
}
EXTRA_SQL = ["CREATE INDEX ix_kibana_logs_screen_time ON dbo.kibana_logs (screen_id, log_time);"]

NVARCHAR_SIZES = (20, 50, 100, 200, 500, 1000, 2000, 4000)
_DATETIME_TZ = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.(\d{1,7}))?(Z|[+-]\d{2}:\d{2})$")
_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.(\d{1,7}))?$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


# --- Okuma -----------------------------------------------------------------------------------


def read_tables(data_dir: Path = DATA_DIR) -> dict[str, list[dict]]:
    tables: dict[str, list[dict]] = {}
    for path in sorted(data_dir.glob("*.json")):
        name = path.stem
        if name.endswith(".stats") or re.fullmatch(r"kibana_logs_part\d+", name):
            continue
        rows = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(rows, list):
            continue
        tables[name] = rows
    scenarios_ts = data_dir / "ui" / "scenarios.ts"
    if scenarios_ts.exists():
        items = parse_ts_array(scenarios_ts.read_text(encoding="utf-8"), "scenarios")
        tables["scenarios"] = scenario_rows(items)
    for name in tables:
        if not _NAME.match(name):
            raise ValueError(f"Geçersiz tablo adı: {name}")
    return tables


def scenario_rows(items: list[dict]) -> list[dict]:
    """Bir tur = bir satır; eşleşme (match) kolonlara açılır, adımlar JSON olarak durur."""
    rows = []
    for order, item in enumerate(items, start=1):
        match = item.get("match") or {}
        rows.append(
            {
                "scenario_id": item["id"],
                "sort_order": order,
                "screen_code": item.get("screen"),
                "title": item.get("title"),
                "description": item.get("description"),
                "outcome": item.get("outcome"),
                "match_screen": match.get("screen"),
                "match_error_number": match.get("errorNumber"),
                "match_error_code": match.get("errorCode"),
                "steps": item.get("steps") or [],
            }
        )
    return rows


# --- scenarios.ts ayrıştırıcı (kod çalıştırmaz) ----------------------------------------------

_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v", "0": "\0"}


def parse_ts_array(text: str, name: str) -> list:
    """`export const <name>: T[] = [ ... ];` içindeki diziyi JSON'a çevirip döner.

    Desteklenen: yorumlar, tırnaksız anahtarlar, "…"/'…' metinler, sayılar, true/false/null,
    sondaki virgüller. Şablon metni, fonksiyon, değişken gibi ifadeler hata verir.
    """
    match = re.search(rf"export\s+const\s+{re.escape(name)}\b[^=]*=\s*\[", text)
    if not match:
        raise ValueError(f"'{name}' dizisi bulunamadı")
    out: list[str] = []
    depth = 0
    i = match.end() - 1
    while i < len(text):
        char = text[i]
        if text.startswith("//", i):
            i = text.find("\n", i)
            i = len(text) if i < 0 else i
            continue
        if text.startswith("/*", i):
            i = text.index("*/", i) + 2
            continue
        if char in "\"'":
            value, i = _read_string(text, i)
            out.append(json.dumps(value, ensure_ascii=False))
            continue
        if char == "`":
            raise ValueError(f"Şablon metni desteklenmiyor (konum {i})")
        if char in "[{":
            depth += 1
            out.append(char)
        elif char in "]}":
            while out and out[-1].strip() == "":
                out.pop()
            if out and out[-1] == ",":
                out.pop()  # sondaki virgül
            out.append(char)
            depth -= 1
            if depth == 0:
                return json.loads("".join(out))
        elif char in ",:":
            out.append(char)
        elif char.isspace():
            out.append(" ")
        elif char.isalpha() or char in "_$":
            end = i
            while end < len(text) and (text[end].isalnum() or text[end] in "_$"):
                end += 1
            word = text[i:end]
            rest = text[end:].lstrip()
            if rest.startswith(":"):
                out.append(json.dumps(word))
            elif word in ("true", "false", "null"):
                out.append(word)
            else:
                raise ValueError(f"Desteklenmeyen ifade: {word} (konum {i})")
            i = end
            continue
        elif char.isdigit() or char == "-":
            number = re.match(r"-?\d+(\.\d+)?([eE][+-]?\d+)?", text[i:])
            if not number:
                raise ValueError(f"Geçersiz sayı (konum {i})")
            out.append(number.group(0))
            i += len(number.group(0))
            continue
        else:
            raise ValueError(f"Beklenmeyen karakter {char!r} (konum {i})")
        i += 1
    raise ValueError(f"'{name}' dizisi kapanmıyor")


def _read_string(text: str, start: int) -> tuple[str, int]:
    quote = text[start]
    chars: list[str] = []
    i = start + 1
    while i < len(text):
        char = text[i]
        if char == "\\":
            nxt = text[i + 1]
            if nxt == "u":
                chars.append(chr(int(text[i + 2 : i + 6], 16)))
                i += 6
                continue
            chars.append(_ESCAPES.get(nxt, nxt))
            i += 2
            continue
        if char == quote:
            return "".join(chars), i + 1
        if char == "\n":
            raise ValueError(f"Metin kapanmadan satır bitti (konum {start})")
        chars.append(char)
        i += 1
    raise ValueError(f"Metin kapanmıyor (konum {start})")


# --- Şema --------------------------------------------------------------------------------------


def columns_of(rows: list[dict]) -> list[str]:
    seen: dict[str, None] = {}
    for row in rows:
        for key in row:
            seen.setdefault(key, None)
    for key in seen:
        if not _NAME.match(key):
            raise ValueError(f"Geçersiz kolon adı: {key}")
    return list(seen)


def _fraction_digits(values: list[str], pattern: re.Pattern) -> int:
    digits = [len(m.group(2) or "") for m in map(pattern.match, values) if m]
    return max(3, max(digits, default=0))


def infer_type(values: list) -> str:
    """Kolon değerlerinden SQL tipi (NULL/NOT NULL ve anahtar hariç)."""
    present = [value for value in values if value is not None]
    if not present:
        return "NVARCHAR(100)"
    if any(isinstance(value, dict | list) for value in present):
        return "NVARCHAR(MAX)"  # iç içe JSON, metin olarak
    if all(isinstance(value, bool) for value in present):
        return "BIT"
    if all(isinstance(value, int) and not isinstance(value, bool) for value in present):
        return "INT" if max(abs(value) for value in present) < 2**31 else "BIGINT"
    if all(isinstance(value, int | float) and not isinstance(value, bool) for value in present):
        return "FLOAT"
    if all(isinstance(value, str) for value in present):
        if all(_DATETIME_TZ.match(value) for value in present):
            return f"DATETIMEOFFSET({_fraction_digits(present, _DATETIME_TZ)})"
        if all(_DATETIME.match(value) for value in present):
            return f"DATETIME2({_fraction_digits(present, _DATETIME)})"
        if all(_DATE.match(value) for value in present):
            return "DATE"
        longest = max(len(value) for value in present)
        for size in NVARCHAR_SIZES:
            if longest * 4 <= size:  # demoda eklenecek daha uzun kayıtlar için pay
                return f"NVARCHAR({size})"
        return "NVARCHAR(MAX)"
    kinds = sorted({type(value).__name__ for value in present})
    raise ValueError(f"Karışık tipler: {kinds}")


def primary_key(rows: list[dict], columns: list[str], types: dict[str, str]) -> list[str]:
    """İlk kolon ya da ilk iki kolon satırları tekil ve boşsuz tanımlıyorsa anahtar odur."""
    for size in (1, 2):
        key = columns[:size]
        if len(key) < size or any(types[column].endswith("(MAX)") for column in key):
            continue
        values = [tuple(row.get(column) for column in key) for row in rows]
        if None not in {v for value in values for v in value} and len(set(values)) == len(rows):
            return key
    return []


def build_schema(tables: dict[str, list[dict]]) -> str:
    lines = [
        "-- Mercek: datav2 tablolarının Azure SQL şeması (T-SQL).",
        "-- ÜRETİLMİŞ DOSYA: elle değiştirmeyin. Yeniden üretmek için (repo kökünden):",
        "--   python scripts/build_schema.py",
        "-- Kolon tipleri JSON verisinden çıkarılır; boş tablolar datav2/SCHEMA.md'deki tanımla.",
        "-- scripts/load_sql.py tabloları silip yeniden oluşturur; toplu ifadeler GO ile ayrılır.",
        "",
    ]
    names = sorted(set(tables) | set(MANUAL_TABLES))
    for name in names:
        lines.append(f"DROP TABLE IF EXISTS dbo.{name};")
    lines += ["GO", ""]
    for name in names:
        rows = tables.get(name) or []
        if not rows:
            definitions = [f"[{column}] {sql_type}" for column, sql_type in MANUAL_TABLES[name]]
        else:
            columns = columns_of(rows)
            types = {column: infer_type([row.get(column) for row in rows]) for column in columns}
            key = primary_key(rows, columns, types)
            definitions = [
                f"[{column}] {types[column]} {'NOT NULL' if column in key else 'NULL'}"
                for column in columns
            ]
            if key:
                definitions.append(
                    f"CONSTRAINT pk_{name} PRIMARY KEY ({', '.join(f'[{c}]' for c in key)})"
                )
        lines.append(f"CREATE TABLE dbo.{name} (")
        lines.append(",\n".join(f"    {definition}" for definition in definitions))
        lines += [");", "GO", ""]
    for statement in EXTRA_SQL:
        lines += [statement, "GO", ""]
    return "\n".join(lines)


_CREATE = re.compile(r"CREATE TABLE dbo\.(\w+) \((.*?)\n\);", re.S)
_COLUMN = re.compile(r"^\s*\[(\w+)\]\s+([A-Z0-9]+(?:\([^)]*\))?)(.*)$")


def parse_schema(text: str) -> dict[str, dict[str, str]]:
    """schema.sql → {tablo: {kolon: tip}}; IDENTITY kolonların tipi "INT IDENTITY" olur."""
    tables: dict[str, dict[str, str]] = {}
    for name, body in _CREATE.findall(text):
        columns = {}
        for line in body.split("\n"):
            column = _COLUMN.match(line)
            if column:
                identity = " IDENTITY" if "IDENTITY" in column.group(3) else ""
                columns[column.group(1)] = column.group(2) + identity
        tables[name] = columns
    return tables


def schema_batches(text: str) -> list[str]:
    batches = re.split(r"^\s*GO\s*$", text, flags=re.MULTILINE | re.IGNORECASE)
    return [batch.strip() for batch in batches if batch.strip() and not _only_comments(batch)]


def _only_comments(batch: str) -> bool:
    return all(not line.strip() or line.strip().startswith("--") for line in batch.split("\n"))
