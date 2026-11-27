"""Human-friendly 12-hour time and date labels used in facts, tools and fallbacks."""

from __future__ import annotations

from datetime import date, datetime

NOON_HOUR = 12


def clock(moment: datetime) -> str:
    """12-hour clock time, e.g. ``"4:00 PM"`` or ``"11:30 AM"``."""
    hour = moment.hour % NOON_HOUR or NOON_HOUR
    return f"{hour}:{moment.minute:02d} {'AM' if moment.hour < NOON_HOUR else 'PM'}"


def day_label(day: date | datetime) -> str:
    """Short date, e.g. ``"Thu 26 Nov"``."""
    return f"{day:%a} {day.day} {day:%b}"


def relative_day(moment: datetime, today: date) -> str:
    """``"Today"``, ``"Tomorrow"`` or the short date for later days."""
    delta = (moment.date() - today).days
    if delta == 0:
        return "Today"
    if delta == 1:
        return "Tomorrow"
    return day_label(moment)
