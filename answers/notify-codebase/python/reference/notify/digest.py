"""The daily digest."""

from __future__ import annotations

from .clock import DAY_SECONDS, local_midnight
from .models import HELD, DigestLine, UnknownUser
from .store import Store


def build_digest(store: Store, id: str, now: int) -> list[DigestLine]:
    """The user's held notifications from their local day before the one containing `now`."""
    u = store.user(id)
    if u is None:
        raise UnknownUser(id)
    to = local_midnight(now, u.offset_min)
    start = to - DAY_SECONDS
    lines: dict[str, DigestLine] = {}
    for r in store.log(id):
        n = r.notification
        if r.result.status != HELD or n.at < start or n.at >= to:
            continue
        line = lines.setdefault(n.topic, DigestLine(n.topic, 0, ""))
        line.count += 1
        line.latest = n.title
    return sorted(lines.values(), key=lambda line: (-line.count, line.topic))
