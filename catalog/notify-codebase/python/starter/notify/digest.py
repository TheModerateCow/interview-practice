"""The daily digest."""

from __future__ import annotations

from .clock import DAY_SECONDS, local_midnight
from .models import HELD, DigestLine, UnknownUser
from .store import Store


def build_digest(store: Store, id: str, now: int) -> list[DigestLine]:
    """The user's held notifications from their local day before the one containing `now`."""
    raise NotImplementedError
