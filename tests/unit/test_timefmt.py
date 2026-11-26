from datetime import date, datetime

import pytest

from app.engine.timefmt import clock, day_label, relative_day


@pytest.mark.parametrize(
    ("hour", "minute", "expected"),
    [
        (0, 0, "12:00 AM"),
        (9, 5, "9:05 AM"),
        (12, 0, "12:00 PM"),
        (16, 30, "4:30 PM"),
        (23, 59, "11:59 PM"),
    ],
)
def test_clock_is_12_hour(hour: int, minute: int, expected: str) -> None:
    assert clock(datetime(2026, 11, 26, hour, minute)) == expected


def test_day_label() -> None:
    assert day_label(date(2026, 11, 26)) == "Thu 26 Nov"


def test_relative_day() -> None:
    today = date(2026, 11, 26)
    assert relative_day(datetime(2026, 11, 26, 9), today) == "Today"
    assert relative_day(datetime(2026, 11, 27, 9), today) == "Tomorrow"
    assert relative_day(datetime(2026, 11, 29, 9), today) == "Sun 29 Nov"
