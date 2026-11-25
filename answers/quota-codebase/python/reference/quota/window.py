"""Fixed-window arithmetic and the burst rollover rule."""

from .models import Plan


def window_start(now: int, window: int) -> int:
    """Start of the fixed window that contains now.

    Windows are aligned to the epoch, so every key on a plan resets together."""
    return now - now % window


def reset_in(now: int, window: int) -> int:
    """Seconds remaining until the window containing now ends."""
    return window_start(now, window) + window - now


def rollover(p: Plan, prev_used: int) -> int:
    """Units that carry into a window from the one before it: whatever the key
    left unused there, up to the plan's burst allowance."""
    unused = max(p.limit - prev_used, 0)
    return min(unused, p.burst)


def capacity(p: Plan, prev_used: int) -> int:
    """Units a key may spend in a window, given what it spent in the window before."""
    return p.limit + rollover(p, prev_used)
