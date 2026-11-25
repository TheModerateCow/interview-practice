"""An in-memory configuration store for a platform team."""

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class _Entry:
    value: str
    expires_at: int = 0  # 0 means it never expires

    def live(self, ts: int) -> bool:
        return self.expires_at == 0 or ts < self.expires_at


class Store:
    """A key maps to a set of named fields. Timestamps only ever increase."""

    def __init__(self):
        self.records: dict[str, dict[str, _Entry]] = {}
        self.history: dict[tuple[str, str], list[tuple[int, _Entry | None]]] = {}
        self.backups: dict[str, dict[str, dict[str, tuple[str, int]]]] = {}

    def _lookup(self, ts, key, field):
        e = self.records.get(key, {}).get(field)
        return e if e is not None and e.live(ts) else None

    def _put(self, ts, key, field, e):
        self.records.setdefault(key, {})[field] = e
        self.history.setdefault((key, field), []).append((ts, e))

    def _remove(self, ts, key, field):
        del self.records[key][field]
        if not self.records[key]:
            del self.records[key]
        self.history.setdefault((key, field), []).append((ts, None))

    # ---- level 1

    def set(self, ts: int, key: str, field: str, value: str) -> bool:
        had = self._lookup(ts, key, field) is not None
        self._put(ts, key, field, _Entry(value))
        return not had

    def get(self, ts: int, key: str, field: str) -> str | None:
        e = self._lookup(ts, key, field)
        return None if e is None else e.value

    def delete(self, ts: int, key: str, field: str) -> bool:
        if self._lookup(ts, key, field) is None:
            return False
        self._remove(ts, key, field)
        return True

    def compare_and_set(self, ts: int, key: str, field: str, expected: str, value: str) -> bool:
        e = self._lookup(ts, key, field)
        if e is None or e.value != expected:
            return False
        self._put(ts, key, field, replace(e, value=value))
        return True

    # ---- level 2

    def scan(self, ts: int, key: str) -> list[str]:
        return self.scan_prefix(ts, key, "")

    def scan_prefix(self, ts: int, key: str, prefix: str) -> list[str]:
        fields = self.records.get(key, {})
        return [f"{f}={fields[f].value}" for f in sorted(fields) if f.startswith(prefix) and fields[f].live(ts)]

    def list_keys(self, ts: int, prefix: str) -> list[str]:
        return sorted(k for k in self.records if k.startswith(prefix) and self.scan_prefix(ts, k, ""))

    # ---- level 3

    def set_with_ttl(self, ts: int, key: str, field: str, value: str, ttl: int) -> bool:
        had = self._lookup(ts, key, field) is not None
        self._put(ts, key, field, _Entry(value, ts + ttl))
        return not had

    def remaining_ttl(self, ts: int, key: str, field: str) -> int:
        e = self._lookup(ts, key, field)
        if e is None:
            return -1
        if e.expires_at == 0:
            return 0
        return e.expires_at - ts

    # ---- level 4

    def backup(self, ts: int) -> str:
        b: dict[str, dict[str, tuple[str, int]]] = {}
        for k, fields in self.records.items():
            for f, e in fields.items():
                if not e.live(ts):
                    continue
                b.setdefault(k, {})[f] = (e.value, e.expires_at - ts if e.expires_at else 0)
        bid = f"b{len(self.backups) + 1}"
        self.backups[bid] = b
        return bid

    def restore(self, ts: int, backup_id: str) -> bool:
        b = self.backups.get(backup_id)
        if b is None:
            return False
        for k in list(self.records):
            for f in list(self.records[k]):
                if f not in b.get(k, {}):
                    self._remove(ts, k, f)
        for k, fields in b.items():
            for f, (value, remaining) in fields.items():
                self._put(ts, k, f, _Entry(value, ts + remaining if remaining else 0))
        return True

    def get_at(self, ts: int, key: str, field: str, at_ts: int) -> str | None:
        last = None
        for t, e in self.history.get((key, field), []):
            if t <= at_ts:
                last = e
        if last is None or not last.live(at_ts):
            return None
        return last.value
