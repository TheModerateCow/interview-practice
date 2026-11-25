"""The notification fan-out for one region."""

from __future__ import annotations

from dataclasses import replace

from .clock import in_quiet_hours
from .digest import build_digest
from .models import (
    CAP_WINDOW,
    DEDUPE_WINDOW,
    DUPLICATE,
    HELD,
    HOURLY_CAP,
    SENT,
    BadChannel,
    BadNotification,
    BadOffset,
    BadQuietHours,
    DigestLine,
    DuplicateUser,
    Notification,
    Record,
    Result,
    UnknownUser,
    User,
)
from .store import Store


class Service:
    def __init__(self) -> None:
        self._store = Store()

    def add_user(self, id: str, offset_min: int) -> None:
        """Register a user at a fixed UTC offset. New users get email only and no quiet hours."""
        if offset_min < -720 or offset_min > 840:
            raise BadOffset(offset_min)
        if self._store.user(id) is not None:
            raise DuplicateUser(id)
        self._store.put_user(User(id, offset_min))

    def user(self, id: str) -> User:
        """A copy of the user's current settings."""
        u = self._store.user(id)
        if u is None:
            raise UnknownUser(id)
        return replace(u, channels=list(u.channels))

    def set_channels(self, id: str, chans: list[str]) -> None:
        """Replace the user's enabled channels. An empty list means everything goes to the digest."""
        if self._store.user(id) is None:
            raise UnknownUser(id)
        seen: set[str] = set()
        for ch in chans:
            if ch not in HOURLY_CAP or ch in seen:
                raise BadChannel(ch)
            seen.add(ch)
        self._store.set_channels(id, chans)

    def set_quiet_hours(self, id: str, start: int, end: int) -> None:
        """Set the local hours [start, end) during which only urgent notifications go out.

        start == end turns quiet hours off.
        """
        u = self._store.user(id)
        if u is None:
            raise UnknownUser(id)
        if not (0 <= start <= 23 and 0 <= end <= 23):
            raise BadQuietHours((start, end))
        u.quiet_from, u.quiet_to = start, end

    def send(self, n: Notification) -> Result:
        """Fan one notification out to the user's channels and log the result.

        Sends for one user must come in time order.
        """
        u = self._store.user(n.user)
        if u is None:
            raise UnknownUser(n.user)
        if not n.topic or not n.key:
            raise BadNotification(n)
        last = self._store.last_accepted(n.user, n.key)
        if last is not None and n.at - last < DEDUPE_WINDOW:
            res = Result(DUPLICATE)
            self._store.record(Record(n, res))
            return res
        self._store.accept(n.user, n.key, n.at)
        res = Result(HELD)
        if n.urgent or not in_quiet_hours(u, n.at):
            for ch in u.channels:
                if self._store.deliveries_since(n.user, ch, n.at - CAP_WINDOW) < HOURLY_CAP[ch]:
                    self._store.delivered(n.user, ch, n.at)
                    res.channels.append(ch)
            if res.channels:
                res.status = SENT
        self._store.record(Record(n, res))
        return res

    def digest(self, id: str, now: int) -> list[DigestLine]:
        """The user's daily digest of held notifications. See problem.md."""
        return build_digest(self._store, id, now)
