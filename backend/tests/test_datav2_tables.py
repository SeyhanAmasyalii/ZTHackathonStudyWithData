"""scripts/datav2_tables.py (şema üretimi, scenarios.ts ayrıştırma) ve load_sql yardımcıları."""

import sys

import pytest

from app.config import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "scripts"))
import datav2_tables as dt  # noqa: E402
import load_sql  # noqa: E402


def test_parse_ts_array_handles_comments_keys_and_trailing_commas():
    text = """
    // yorum
    export const scenarios: Scenario[] = [
      { id: "a", url: "https://x.test/y", n: -12.5, ok: true, match: null,
        /* not */ s: 'tek "tırnak"', },
      { id: "b\\"c", steps: [{ actions: [] },], },
    ];
    """
    assert dt.parse_ts_array(text, "scenarios") == [
        {
            "id": "a",
            "url": "https://x.test/y",
            "n": -12.5,
            "ok": True,
            "match": None,
            "s": 'tek "tırnak"',
        },
        {"id": 'b"c', "steps": [{"actions": []}]},
    ]


@pytest.mark.parametrize("bad", ["[ undefinedValue ]", "[ `x` ]", "[ fn() ]"])
def test_parse_ts_array_rejects_code(bad):
    with pytest.raises(ValueError):
        dt.parse_ts_array(f"export const scenarios = {bad};", "scenarios")


def test_real_scenarios_file_parses():
    rows = dt.read_tables()["scenarios"]
    ids = [row["scenario_id"] for row in rows]
    assert len(ids) == len(set(ids)) > 0
    with_match = [row for row in rows if row["match_error_number"] is not None]
    assert with_match and all(row["match_screen"] for row in with_match)


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([1, 2, None], "INT"),
        ([1, 3_000_000_000], "BIGINT"),
        ([1, 2.5], "FLOAT"),
        ([True, False], "BIT"),
        (["2026-09-16T01:43:43.349+03:00", "2026-09-16T01:43:43Z"], "DATETIMEOFFSET(3)"),
        (["2026-09-16T01:43:43.1234567+03:00"], "DATETIMEOFFSET(7)"),
        (["2026-09-16T01:43:43"], "DATETIME2(3)"),
        (["2026-09-16"], "DATE"),
        (["abc"], "NVARCHAR(20)"),
        (["x" * 300], "NVARCHAR(2000)"),
        (["x" * 1500], "NVARCHAR(MAX)"),
        ([{"a": 1}, [1]], "NVARCHAR(MAX)"),
        ([None], "NVARCHAR(100)"),
    ],
)
def test_infer_type(values, expected):
    assert dt.infer_type(values) == expected


def test_infer_type_rejects_mixed():
    with pytest.raises(ValueError):
        dt.infer_type(["a", 1])


def test_build_and_parse_schema_round_trip():
    tables = {
        "pairs": [{"a": "x", "b": "y", "n": 1}, {"a": "x", "b": "z", "n": None}],
        "items": [{"item_id": "I1", "tags": ["t"]}],
    }
    text = dt.build_schema(tables)
    assert "CONSTRAINT pk_pairs PRIMARY KEY ([a], [b])" in text
    assert "CONSTRAINT pk_items PRIMARY KEY ([item_id])" in text
    schema = dt.parse_schema(text)
    assert schema["pairs"] == {"a": "NVARCHAR(20)", "b": "NVARCHAR(20)", "n": "INT"}
    assert schema["items"]["tags"] == "NVARCHAR(MAX)"
    assert schema["prevented_calls"]["prevented_id"] == "INT IDENTITY"
    assert "DROP TABLE IF EXISTS dbo.items;" in dt.schema_batches(text)[0]


def test_committed_schema_is_up_to_date():
    committed = (REPO_ROOT / "db" / "schema.sql").read_text(encoding="utf-8")
    assert committed == dt.build_schema(dt.read_tables()), "python scripts/build_schema.py"


def test_schema_covers_every_datav2_table():
    tables = dt.read_tables()
    assert {"customers", "loans", "announcements", "scenarios", "kibana_logs"} <= set(tables)
    assert not any(name.startswith("kibana_logs_part") for name in tables)
    assert not any(name.endswith(".stats") for name in tables)


def test_insert_sql_skips_identity_and_marks_nested_json():
    types = {"id": "INT IDENTITY", "name": "NVARCHAR(20)", "steps": "NVARCHAR(MAX)"}
    statement = load_sql.insert_sql("t", types, {"steps"})
    assert statement == (
        "INSERT INTO dbo.t ([name], [steps]) SELECT [name], [steps] FROM OPENJSON(?) WITH ("
        "[name] NVARCHAR(20) '$.\"name\"', [steps] NVARCHAR(MAX) '$.\"steps\"' AS JSON)"
    )


def test_rows_payload_is_ascii():
    payload = load_sql.rows_payload([{"name": "Doğalgaz", "x": 1}], ["name"])
    assert payload.isascii() and "Do\\u011falgaz" in payload


@pytest.mark.parametrize(
    ("expected", "actual", "sql_type", "nested", "result"),
    [
        (
            "2026-09-16T09:51:35+03:00",
            "2026-09-16T09:51:35.000+03:00",
            "DATETIMEOFFSET(3)",
            False,
            True,
        ),
        ("2026-09-16T09:51:35+03:00", "2026-09-16T06:51:35Z", "DATETIMEOFFSET(3)", False, True),
        (
            "2026-09-16T09:51:35+03:00",
            "2026-09-16T09:51:36+03:00",
            "DATETIMEOFFSET(3)",
            False,
            False,
        ),
        (1500, 1500.0, "FLOAT", False, True),
        (["a"], '["a"]', "NVARCHAR(MAX)", True, True),
        ("Doğalgaz", "Dogalgaz", "NVARCHAR(50)", False, False),
        (None, None, "INT", False, True),
        (None, 0, "INT", False, False),
    ],
)
def test_same(expected, actual, sql_type, nested, result):
    assert load_sql.same(expected, actual, sql_type, nested) is result
