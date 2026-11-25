"""In-memory users, per-user log and the indexes the fan-out checks on every send."""

from __future__ import annotations

from collections import defaultdict, deque

from .models import Record, User


def dedupe_id(user: str, key: str) -> str:
    """The index key for a user's dedupe key."""
    return key


class Store:
    def __init__(self) -> None:
        self._users: dict[str, User] = {}
        self._seen: dict[str, int] = {}  # dedupe_id -> `at` of the last accepted notification
        self._recent: defaultdict[tuple[str, str], deque[int]] = defaultdict(deque)  # delivery times, oldest first
        self._logs: defaultdict[str, list[Record]] = defaultdict(list)  # per user, oldest first

    def user(self, id: str) -> User | None:
        return self._users.get(id)

    def put_user(self, u: User) -> None:
        self._users[u.id] = u

    def set_channels(self, id: str, chans: list[str]) -> None:
        self._users[id].channels = chans

    def last_accepted(self, user: str, key: str) -> int | None:
        """When the user last had a non-duplicate notification with this dedupe key."""
        return self._seen.get(dedupe_id(user, key))

    def accept(self, user: str, key: str, at: int) -> None:
        self._seen[dedupe_id(user, key)] = at

    def deliveries_since(self, user: str, ch: str, since: int) -> int:
        """Count the user's deliveries on `ch` with time > since."""
        return sum(1 for r in self._logs[user] if r.notification.at > since and ch in r.result.channels)

    def delivered(self, user: str, ch: str, at: int) -> None:
        self._recent[(user, ch)].append(at)

    def record(self, r: Record) -> None:
        self._logs[r.notification.user].append(r)

    def log(self, user: str) -> list[Record]:
        """The user's records, oldest first."""
        return self._logs[user]
