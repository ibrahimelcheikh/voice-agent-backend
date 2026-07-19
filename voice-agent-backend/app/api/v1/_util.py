"""Shared helpers for /api/v1."""
from datetime import datetime


def rel_time(dt) -> str:
    """Human 'x min ago' string from a timestamp (best-effort)."""
    if not dt:
        return ""
    try:
        delta = datetime.utcnow() - dt.replace(tzinfo=None)
    except Exception:
        return ""
    secs = int(delta.total_seconds())
    if secs < 60:
        return "just now"
    mins = secs // 60
    if mins < 60:
        return f"{mins} min ago"
    hrs = mins // 60
    if hrs < 24:
        return f"{hrs} hr{'s' if hrs != 1 else ''} ago"
    days = hrs // 24
    return f"{days} day{'s' if days != 1 else ''} ago"
