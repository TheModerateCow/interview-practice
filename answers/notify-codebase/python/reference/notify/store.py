"""In-memory users, per-user log and the indexes the fan-out checks on every send."""

from __future__ import annotations

from collections import defaultdict, deque

from .models import Record, User


def dedupe_id(user: str, key: str) -> str:
    """The index key for a user's dedupe key."""
    return user + "\x00" + key


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
        self._users[id].channels = list(chans)

    def last_accepted(self, user: str, key: str) -> int | None:
        """When the user last had a non-duplicate notification with this dedupe key."""
        return self._seen.get(dedupe_id(user, key))

    def accept(self, user: str, key: str, at: int) -> None:
        self._seen[dedupe_id(user, key)] = at

    def deliveries_since(self, user: str, ch: str, since: int) -> int:
        """Count the user's deliveries on `ch` with time > since."""
        # Sends for one user arrive in time order, so entries this old can go.
        q = self._recent[(user, ch)]
        while q and q[0] <= since:
            q.popleft()
        return len(q)

    def delivered(self, user: str, ch: str, at: int) -> None:
        self._recent[(user, ch)].append(at)

    def record(self, r: Record) -> None:
        self._logs[r.notification.user].append(r)

    def log(self, user: str) -> list[Record]:
        """The user's records, oldest first."""
        return self._logs[user]
