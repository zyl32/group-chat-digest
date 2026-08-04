"""ICS export service for Group Chat Digest.

Generates RFC 5545-compliant VCALENDAR/VTODO byte streams for export to
calendar applications (Apple Calendar, Google Calendar).
"""
from datetime import datetime

__all__ = ["export_ics"]


def export_ics(todos: list[dict]) -> bytes:
    """Render todos as an ICS VCALENDAR byte stream.

    Args:
        todos: List of dicts with keys 'who' (str|None), 'what' (str),
            'due_at' (datetime|None). datetime should be tz-aware UTC for
            correct DTSTART formatting.

    Returns:
        UTF-8 encoded ICS bytes.
    """
    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//group-chat-digest//EN",
    ]
    for i, t in enumerate(todos, 1):
        lines += [
            "BEGIN:VTODO",
            f"UID:todo-{i}@group-chat-digest",
            f"SUMMARY:{_escape(t['what'])}",
        ]
        if t.get("due_at"):
            lines.append(f"DTSTART:{_fmt_dt(t['due_at'])}")
        if t.get("who"):
            lines.append(f"ATTENDEE:{_escape(t['who'])}")
        lines.append("END:VTODO")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines).encode("utf-8")


def _fmt_dt(dt: datetime) -> str:
    """Format datetime as UTC ICS DTSTART value: YYYYMMDDTHHMMSSZ."""
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _escape(s: str) -> str:
    """Escape ICS-special characters per RFC 5545: backslash, semicolon, comma, newline."""
    return (
        s.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )
