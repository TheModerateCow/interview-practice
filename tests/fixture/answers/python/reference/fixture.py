"""Reference for the harness fixture (canonical: expected values come from here)."""
from dataclasses import dataclass
from typing import List, Optional


class InvalidAmountError(Exception): pass
class InsufficientFundsError(Exception): pass
class InvalidWindowError(Exception): pass
class WalletFrozenError(Exception): pass
class InvalidOwnerError(Exception): pass


@dataclass
class Entry:
    account_id: str
    amount_cents: int


def net_by_account(entries: List[Entry]) -> List[Entry]:
    tot = {}
    for e in entries: tot[e.account_id] = tot.get(e.account_id, 0) + e.amount_cents
    return [Entry(a, tot[a]) for a in sorted(tot)]


def max_window(values: List[int], k: int) -> int:
    if not 1 <= k <= len(values): raise InvalidWindowError(f"k={k}")
    s = best = sum(values[:k])
    for i in range(k, len(values)):
        s += values[i] - values[i - k]
        best = max(best, s)
    return best


def first_negative(values: List[int]) -> Optional[int]:
    return next((i for i, v in enumerate(values) if v < 0), None)


def grid(n: int) -> List[List[int]]:
    return [[r * n + c + 1 for c in range(n)] for r in range(n)]


class Wallet:
    def __init__(self, owner: str):
        if owner == "": raise InvalidOwnerError()
        self._owner, self._bal, self._hist, self._frozen = owner, 0, [], False

    def _check(self, cents):
        if self._frozen: raise WalletFrozenError()
        if cents <= 0: raise InvalidAmountError(str(cents))

    def deposit(self, cents: int) -> None:
        self._check(cents); self._bal += cents; self._hist.append(f"+{cents}")

    def withdraw(self, cents: int) -> int:
        self._check(cents)
        if cents > self._bal: raise InsufficientFundsError(str(cents))
        self._bal -= cents; self._hist.append(f"-{cents}")
        return self._bal

    def balance(self) -> int: return self._bal
    def owner_name(self) -> str: return self._owner
    def history(self) -> List[str]: return list(self._hist)
    def freeze(self) -> None: self._frozen = True
    def frozen(self) -> bool: return self._frozen
