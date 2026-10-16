from datetime import datetime

import pytest

from app.config import TURKEY_TZ
from app.repositories.datav2 import load_error_logs
from app.services.tools import ToolContext, kibana_sorgula, run_tool

NOW = datetime(2026, 10, 17, 9, 15, tzinfo=TURKEY_TZ)


@pytest.fixture
def context(data_dir):
    return ToolContext(user_name="elif", now=NOW, logs=load_error_logs(data_dir))


def test_only_error_levels_loaded(data_dir):
    logs = load_error_logs(data_dir)
    assert len(logs) == 2002
    assert {entry.log_level for entry in logs} == {"Warning", "Error"}


def test_elif_last_30_minutes_on_odmttlmt(context):
    result = kibana_sorgula(
        {
            "screen_code": "ODMTTLMT",
            "start_time": "2026-10-17T08:45",
            "end_time": "2026-10-17T09:15",
            "only_mine": True,
        },
        context,
    )
    assert result["total"] == 7
    assert result["distinct_customers"] == 7
    assert result["by_error"] == [
        {
            "screen_code": "ODMTTLMT",
            "error_number": 110731,
            "error_code": "INSTITUTION_TIMEOUT",
            "institution_code": "GAZ02",
            "count": 7,
        }
    ]
    newest = result["samples"][0]
    assert newest["log_time"] == "2026-10-17T08:57:46"
    assert newest["message"] == "GAZ02 kurum servisi 8000 ms içinde yanıt vermedi."


def test_iski_13_digits_everyone_last_7_days(context):
    result = kibana_sorgula(
        {
            "screen_code": "odmttlmt",
            "institution_code": "SU01",
            "keyword": "13 HANE",
            "start_time": "2026-10-10T09:15",
            "end_time": "2026-10-17T09:15",
            "only_mine": False,
        },
        context,
    )
    assert result["total"] == 158
    assert result["distinct_customers"] == 157
    assert [group["error_number"] for group in result["by_error"]] == [110412]
    assert len(result["samples"]) == 20


def test_elif_has_no_krdtkull_errors(context):
    result = kibana_sorgula(
        {
            "screen_code": "KRDTKULL",
            "start_time": "2026-10-17T08:45",
            "end_time": "2026-10-17T09:15",
            "only_mine": True,
        },
        context,
    )
    assert result["total"] == 0
    assert result["samples"] == []


def test_range_is_clipped_to_7_days_and_now(context):
    result = kibana_sorgula(
        {"start_time": "2026-09-01T00:00", "end_time": "2026-12-31T00:00", "only_mine": False},
        context,
    )
    assert result["query"]["end_time"] == "2026-10-17T09:15"
    assert result["query"]["start_time"] == "2026-10-10T09:15"


def test_user_name_comes_from_context_not_model(context):
    mine = kibana_sorgula(
        {"start_time": "2026-10-17T08:00", "end_time": "2026-10-17T09:15", "only_mine": True},
        context,
    )
    other = ToolContext(user_name="zeynep", now=NOW, logs=context.logs)
    theirs = kibana_sorgula(
        {"start_time": "2026-10-17T08:00", "end_time": "2026-10-17T09:15", "only_mine": True},
        other,
    )
    assert mine["total"] == 8
    assert theirs["total"] == 0


@pytest.mark.parametrize(
    ("arguments", "error"),
    [
        ('{"start_time": "dün", "end_time": "2026-10-17T09:15", "only_mine": true}', "biçimi"),
        (
            '{"start_time": "2026-10-17T09:15", "end_time": "2026-10-17T08:00", "only_mine": true}',
            "önce olmalı",
        ),
        (
            '{"start_time": "2026-10-17T08:00", "end_time": "2026-10-17T09:15", "only_mine": true,'
            ' "error_number": "abc"}',
            "tam sayı",
        ),
        ("not json", "geçerli JSON"),
        ("[1, 2]", "nesne"),
    ],
)
def test_invalid_arguments_return_error(context, arguments, error):
    result = run_tool("kibana_sorgula", arguments, context)
    assert error in result["error"]


def test_unknown_tool(context):
    assert run_tool("sil_her_seyi", "{}", context) == {"error": "Bilinmeyen araç: sil_her_seyi"}


def test_without_screen_filter_finds_own_recent_errors(context):
    """ "fatura ödemede sorun yaşıyorum": ekran filtresi olmadan kendi son 30 dakikası."""
    result = kibana_sorgula(
        {"start_time": "2026-10-17T08:45", "end_time": "2026-10-17T09:15", "only_mine": True},
        context,
    )
    assert result["total"] == 7
    assert result["by_error"][0]["screen_code"] == "ODMTTLMT"
