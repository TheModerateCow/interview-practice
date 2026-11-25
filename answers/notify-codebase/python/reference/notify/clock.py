"""Local-time arithmetic."""

from __future__ import annotations

from .models import User

DAY_SECONDS = 24 * 60 * 60


def local_hour(at: int, offset_min: int) -> int:
    """The hour (0-23) on the user's wall clock at UTC time `at`."""
    wall = at + offset_min * 60
    return wall % DAY_SECONDS // 3600


def in_quiet_hours(u: User, at: int) -> bool:
    """Whether `at` falls in the user's quiet hours. A range like 22 -> 7 wraps past midnight."""
    if u.quiet_from == u.quiet_to:
        return False
    h = local_hour(at, u.offset_min)
    if u.quiet_from < u.quiet_to:
        return u.quiet_from <= h < u.quiet_to
    return h >= u.quiet_from or h < u.quiet_to


def local_midnight(at: int, offset_min: int) -> int:
    """The UTC time at which the user's local day containing `at` began."""
    shift = offset_min * 60
    return at - (at + shift) % DAY_SECONDS
