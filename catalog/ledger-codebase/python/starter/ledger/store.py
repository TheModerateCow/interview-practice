"""In-memory journal with per-account running balances."""

import bisect
import dataclasses
from typing import NamedTuple

from .journal import Entry, NotFound


class Line(NamedTuple):
    """One posting as it appears on an account statement."""

    ts: int
    entry_id: str
    amount: int
    balance: int  # the account's balance right after this posting


def _ts(line: Line) -> int:
    return line.ts


class Store:
    """Every entry in posting order, plus a per-account index of lines with running
    balances so balance queries don't replay the journal."""

    def __init__(self) -> None:
        self.entries: list[Entry] = []
        self.lines: dict[tuple[str, str], list[Line]] = {}
        self.head_ts = 0
        self.payouts: dict = {}

    def append(self, e: Entry) -> Entry:
        """Record an already-validated entry and return it with its id set."""
        e.id = f"e{len(self.entries) + 1}"
        self.entries.append(e)
        for p in e.postings:
            ls = self.lines.setdefault((p.account, p.currency), [])
            bal = p.amount + (ls[-1].balance if ls else 0)
            ls.append(Line(e.ts, e.id, p.amount, bal))
        self.head_ts = e.ts
        return e

    def history(self, b: tuple[str, str]) -> list[Line]:
        """An account's lines, oldest first."""
        return self.lines.setdefault(b, [])

    def balance_at(self, b: tuple[str, str], ts: int) -> int:
        """The account's balance after every posting with ts <= the given ts."""
        ls = self.lines.get(b, [])
        i = bisect.bisect_right(ls, ts, key=_ts)
        return ls[i - 1].balance if i else 0

    def balance(self, b: tuple[str, str]) -> int:
        """The account's current balance."""
        ls = self.lines.get(b)
        return ls[-1].balance if ls else 0

    def update_payout(self, payout_id: str, fn) -> None:
        """Run fn on a copy of the stored payout and keep the copy only if fn succeeds,
        so a rejected transition leaves the payout as it was."""
        p = self.payouts.get(payout_id)
        if p is None:
            raise NotFound(f"payout {payout_id!r}")
        nxt = dataclasses.replace(p)
        fn(nxt)
        p = nxt
