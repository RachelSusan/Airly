"""Rule-based chat replies (used when Gemini is unavailable)."""

from typing import Any

import pytest

from app.ai.fallback import chat_reply

LEAD = "The air now is Poor (AQI 240)."


def _window(start: str, day: str = "Thu 26 Nov") -> dict[str, Any]:
    return {
        "start": start,
        "end": "5:00 PM",
        "day": day,
        "advice": "caution",
        "avg_aqi": 180,
        "category": "Moderate",
        "guidance": "Keep it light.",
    }


def _facts(**overrides: Any) -> dict[str, Any]:
    facts: dict[str, Any] = {
        "now": {"category": "Poor", "aqi": 240},
        "today": "Thu 26 Nov",
        "location": {"name": "Delhi, India"},
        "best_windows": {
            "walk": _window("3:00 PM"),
            "jog": _window("7:00 AM", day="Fri 27 Nov"),
            "play": None,
        },
        "ventilation": {
            "open_windows_now": False,
            "reason": "Outdoor air is Poor.",
            "airing_time": "3:00 PM",
        },
        "commute": {"best_departure_window": {"start": "8:00 AM"}},
    }
    facts.update(overrides)
    return facts


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Which city am I in?", f"You're seeing live air quality for Delhi, India. {LEAD}"),
        (
            "Should I open my windows?",
            "Not right now. Outdoor air is Poor. Best time to air out: about 3:00 PM.",
        ),
        (
            "Can my kids play outside?",
            f"{LEAD} There's no suitable time for outdoor play in the next 24 hours; "
            "plan something indoors.",
        ),
        (
            "Is it safe to jog?",
            f"{LEAD} For a jog, Fri 27 Nov, 7:00 AM to 5:00 PM is the best time, with care "
            "(AQI 180, Moderate). Keep it light.",
        ),
        (
            "Can I go for a walk?",
            f"{LEAD} For a walk, 3:00 PM to 5:00 PM is the best time, with care "
            "(AQI 180, Moderate). Keep it light.",
        ),
        (
            "When should I commute?",
            f"{LEAD} The cleanest time to travel near your usual time is 8:00 AM.",
        ),
        (
            "Do I need an N95?",
            f"{LEAD} Outdoors, a well-fitted N95 mask filters far more fine particles "
            "than a cloth mask.",
        ),
        (
            "Tell me a joke",
            f"{LEAD} I can help with outdoor activities, children's play, windows, masks "
            "and commuting. Try asking one of those.",
        ),
    ],
)
def test_chat_reply_answers_each_topic(question: str, expected: str) -> None:
    assert chat_reply(question, _facts()) == expected


def test_chat_reply_without_place_name() -> None:
    reply = chat_reply("where am i", _facts(location={}))
    assert reply == f"{LEAD} Your exact place name wasn't shared, only your approximate location."


def test_chat_reply_ventilation_open_without_airing_time() -> None:
    ventilation = {"open_windows_now": True, "reason": "Air is clean.", "airing_time": None}
    assert (
        chat_reply("fresh air?", _facts(ventilation=ventilation)) == "Yes, open them. Air is clean."
    )


def test_chat_reply_commute_without_profile() -> None:
    reply = chat_reply("best time to drive?", _facts(commute=None))
    assert reply == f"{LEAD} Add your commute in the profile for travel advice."


def test_chat_reply_first_matching_topic_wins() -> None:
    # "window" is checked before "walk", as in the original keyword order
    assert chat_reply("walk or open a window?", _facts()).startswith("Not right now.")
