"""Inhaled PM2.5 dose and exposure change. See docs/impact_methodology.md, section 4."""

from __future__ import annotations

from enum import StrEnum


class BreathingActivity(StrEnum):
    """Activity level that sets the breathing rate."""

    REST = "rest"
    WALK = "walk"
    CYCLE = "cycle"
    JOG = "jog"


class Protection(StrEnum):
    """Protective measure that reduces the PM2.5 actually inhaled."""

    NONE = "none"
    CLOTH_MASK = "cloth_mask"
    N95 = "n95"
    INDOORS_CLOSED = "indoors_closed"
    INDOORS_HEPA = "indoors_hepa"


# Adult breathing rates, m³/h (US EPA Exposure Factors Handbook 2011, ch. 6, rounded).
BREATHING_RATE_M3_PER_H: dict[BreathingActivity, float] = {
    BreathingActivity.REST: 0.5,
    BreathingActivity.WALK: 1.2,
    BreathingActivity.CYCLE: 2.0,
    BreathingActivity.JOG: 3.0,
}

# Fraction of PM2.5 removed (default assumptions; real-world values vary).
PROTECTION_FACTOR: dict[Protection, float] = {
    Protection.NONE: 0.0,
    Protection.CLOTH_MASK: 0.2,
    Protection.N95: 0.8,
    Protection.INDOORS_CLOSED: 0.4,
    Protection.INDOORS_HEPA: 0.65,
}


def inhaled_dose_ug(
    pm2_5: float,
    activity: BreathingActivity,
    hours: float,
    protection: Protection = Protection.NONE,
) -> float:
    """Return the PM2.5 inhaled in micrograms.

    Raises:
        ValueError: for negative concentration or non-positive duration.
    """
    if pm2_5 < 0 or hours <= 0:
        raise ValueError("pm2_5 must be >= 0 and hours > 0")
    rate = BREATHING_RATE_M3_PER_H[activity]
    return pm2_5 * rate * hours * (1 - PROTECTION_FACTOR[protection])


def exposure_change_pct(old_dose: float, new_dose: float) -> float:
    """Percentage change from ``old_dose`` to ``new_dose`` (negative means less exposure).

    Raises:
        ValueError: if ``old_dose`` is not positive.
    """
    if old_dose <= 0:
        raise ValueError("old_dose must be positive")
    return round((new_dose - old_dose) / old_dose * 100, 1)
