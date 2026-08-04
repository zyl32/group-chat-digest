from datetime import datetime, timezone

import pytest

from app.services.export import export_ics


def test_ics_basic():
    todos = [
        {"who": "张三", "what": "交报告", "due_at": datetime(2026, 8, 10, 9, 0, tzinfo=timezone.utc)},
    ]
    out = export_ics(todos)
    text = out.decode("utf-8")
    assert "BEGIN:VCALENDAR" in text
    assert "END:VCALENDAR" in text
    assert "交报告" in text
    assert "DTSTART:20260810T090000Z" in text


def test_ics_no_due():
    todos = [{"who": "李四", "what": "买咖啡", "due_at": None}]
    out = export_ics(todos)
    assert "买咖啡".encode("utf-8") in out


def test_ics_empty_list():
    """Empty todo list produces just VCALENDAR wrapper."""
    out = export_ics([])
    text = out.decode("utf-8")
    assert "BEGIN:VCALENDAR" in text
    assert "END:VCALENDAR" in text
    assert "BEGIN:VTODO" not in text


def test_ics_multiple_todos():
    """Multiple todos produce multiple VTODO blocks with sequential UIDs."""
    todos = [
        {"who": "张三", "what": "task1", "due_at": None},
        {"who": "李四", "what": "task2", "due_at": datetime(2026, 8, 11, 10, 0, tzinfo=timezone.utc)},
    ]
    out = export_ics(todos)
    text = out.decode("utf-8")
    assert text.count("BEGIN:VTODO") == 2
    assert "UID:todo-1@group-chat-digest" in text
    assert "UID:todo-2@group-chat-digest" in text


def test_ics_escapes_special_chars():
    """Commas, semicolons, backslashes, newlines in what/who are escaped per RFC 5545."""
    todos = [{"who": "a;b,c\\d\n", "what": "x;y,z\\z\n", "due_at": None}]
    out = export_ics(todos)
    text = out.decode("utf-8")
    # Backslash first, then others — verify escape sequences present
    assert "\\\\" in text  # escaped backslash
    assert "\\;" in text   # escaped semicolon
    assert "\\," in text   # escaped comma
    assert "\\n" in text   # escaped newline (literal)


def test_ics_non_utc_timezone_normalizes_to_utc():
    """Non-UTC tz-aware datetime is converted to UTC before formatting."""
    from zoneinfo import ZoneInfo
    todos = [{"who": None, "what": "x",
              "due_at": datetime(2026, 8, 10, 1, 0, tzinfo=ZoneInfo("America/New_York"))}]
    out = export_ics(todos).decode("utf-8")
    # 01:00 EDT (UTC-4 in August) == 05:00 UTC
    assert "DTSTART:20260810T050000Z" in out


def test_ics_naive_datetime_raises():
    """Naive datetime (no tzinfo) raises ValueError, not silent wrong output."""
    todos = [{"who": None, "what": "x", "due_at": datetime(2026, 8, 10, 9, 0)}]
    with pytest.raises(ValueError, match="tz-aware"):
        export_ics(todos)
