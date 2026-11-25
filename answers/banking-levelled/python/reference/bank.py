"""The in-memory core of a retail bank: accounts, money movement, rankings,
scheduled payments, merges and balance history."""

import bisect
from dataclasses import dataclass


@dataclass
class _Account:
    balance: int = 0
    spent: int = 0  # withdrawals, transfers sent and scheduled payments made


@dataclass
class _Payment:
    account: str
    amount: int
    due: int
    status: str = "pending"


class Bank:
    """Holds accounts by id. Timestamps passed to its methods only ever increase."""

    def __init__(self) -> None:
        self._accounts: dict[str, _Account] = {}
        # per id: (ts, balance, open) points, ts nondecreasing
        self._history: dict[str, list[tuple[int, int, bool]]] = {}
        self._payments: list[_Payment] = []  # in the order they were scheduled
        self._by_id: dict[str, _Payment] = {}

    def _record(self, ts: int, id: str) -> None:
        a = self._accounts.get(id)
        self._history.setdefault(id, []).append((ts, a.balance if a else 0, a is not None))

    def _settle(self, ts: int) -> None:
        """Run every pending payment due at or before ts, earliest due first, ties in schedule order."""
        due = [p for p in self._payments if p.status == "pending" and p.due <= ts]
        due.sort(key=lambda p: p.due)  # stable
        for p in due:
            a = self._accounts.get(p.account)
            if a is None or a.balance < p.amount:
                p.status = "failed"
                continue
            a.balance -= p.amount
            a.spent += p.amount
            p.status = "paid"
            self._record(p.due, p.account)

    def open_account(self, ts: int, id: str) -> bool:
        self._settle(ts)
        if id in self._accounts:
            return False
        self._accounts[id] = _Account()
        self._record(ts, id)
        return True

    def deposit(self, ts: int, id: str, amount: int) -> int | None:
        self._settle(ts)
        a = self._accounts.get(id)
        if a is None:
            return None
        a.balance += amount
        self._record(ts, id)
        return a.balance

    def withdraw(self, ts: int, id: str, amount: int) -> int | None:
        self._settle(ts)
        a = self._accounts.get(id)
        if a is None or a.balance < amount:
            return None
        a.balance -= amount
        a.spent += amount
        self._record(ts, id)
        return a.balance

    def transfer(self, ts: int, from_: str, to: str, amount: int) -> int | None:
        self._settle(ts)
        src, dst = self._accounts.get(from_), self._accounts.get(to)
        if src is None or dst is None or from_ == to or src.balance < amount:
            return None
        src.balance -= amount
        src.spent += amount
        dst.balance += amount
        self._record(ts, from_)
        self._record(ts, to)
        return src.balance

    def balance(self, ts: int, id: str) -> int | None:
        self._settle(ts)
        a = self._accounts.get(id)
        return None if a is None else a.balance

    def top_spenders(self, ts: int, n: int) -> list[str]:
        """Up to n open accounts as "id:spent", most spent first, ties by id."""
        self._settle(ts)
        ids = sorted(self._accounts, key=lambda i: (-self._accounts[i].spent, i))
        return [f"{i}:{self._accounts[i].spent}" for i in ids[:n]]

    def accounts_above(self, ts: int, min: int) -> list[str]:
        """Every open account holding at least min, as "id:balance", largest first, ties by id."""
        self._settle(ts)
        ids = sorted((i for i, a in self._accounts.items() if a.balance >= min),
                     key=lambda i: (-self._accounts[i].balance, i))
        return [f"{i}:{self._accounts[i].balance}" for i in ids]

    def schedule_payment(self, ts: int, id: str, amount: int, delay: int) -> str | None:
        self._settle(ts)
        if id not in self._accounts:
            return None
        p = _Payment(id, amount, ts + delay)
        self._payments.append(p)
        pid = f"pay{len(self._payments)}"
        self._by_id[pid] = p
        return pid

    def cancel_payment(self, ts: int, id: str, payment_id: str) -> bool:
        self._settle(ts)
        p = self._by_id.get(payment_id)
        if p is None or p.status != "pending" or p.account != id:
            return False
        p.status = "cancelled"
        return True

    def payment_status(self, ts: int, payment_id: str) -> str:
        """"pending", "paid", "failed" or "cancelled"; "" for an unknown id."""
        self._settle(ts)
        p = self._by_id.get(payment_id)
        return p.status if p else ""

    def merge_accounts(self, ts: int, keep: str, absorb: str) -> bool:
        """Fold absorb into keep: balance, spending and pending payments. absorb is closed."""
        self._settle(ts)
        k, a = self._accounts.get(keep), self._accounts.get(absorb)
        if k is None or a is None or keep == absorb:
            return False
        k.balance += a.balance
        k.spent += a.spent
        for p in self._payments:
            if p.status == "pending" and p.account == absorb:
                p.account = keep
        del self._accounts[absorb]
        self._record(ts, keep)
        self._record(ts, absorb)
        return True

    def balance_at(self, ts: int, id: str, at_ts: int) -> int | None:
        """What the id's balance was right after everything at or before at_ts (at_ts <= ts)."""
        self._settle(ts)
        h = self._history.get(id, [])
        i = bisect.bisect_right(h, at_ts, key=lambda c: c[0])
        if i == 0 or not h[i - 1][2]:
            return None
        return h[i - 1][1]
