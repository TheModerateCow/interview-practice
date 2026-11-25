"""A public library's lending desk: copies of titles, members, loans with due dates
and late fines, and each member's borrowing history."""

from dataclasses import dataclass, field

MAX_LOANS = 3  # copies a member can have on loan at once
LOAN_DAYS = 14  # a copy checked out on day t is due on day t + LOAN_DAYS
FINE_PER_DAY = 25  # late fine in cents per day past the due date
FINE_CAP = 1000  # cap per loan


@dataclass
class _Loan:
    copy_id: str
    title: str
    member: str
    out: int
    due: int
    back: int = -1  # -1 while the copy is still out
    renewals: int = 0


@dataclass
class _Copy:
    id: str
    title: str
    current: "_Loan | None" = None


@dataclass
class _Member:
    loans: list = field(default_factory=list)  # every checkout, oldest first

    def on_loan(self) -> list:
        return [l for l in self.loans if l.back == -1]

    def has_title(self, title: str) -> bool:
        return any(l.title == title for l in self.on_loan())


class Library:
    """Holds every copy and member. Timestamps passed to its methods only ever increase."""

    def __init__(self) -> None:
        self._copies: dict[str, _Copy] = {}
        self._members: dict[str, _Member] = {}
        self._checkouts: dict[str, int] = {}  # successful checkouts per title

    def add_member(self, ts: int, member_id: str) -> bool:
        if member_id in self._members:
            return False
        self._members[member_id] = _Member()
        return True

    def add_copy(self, ts: int, copy_id: str, title: str) -> bool:
        if copy_id in self._copies:
            return False
        self._copies[copy_id] = _Copy(copy_id, title)
        return True

    def checkout(self, ts: int, member_id: str, title: str) -> str:
        m = self._members.get(member_id)
        if m is None or len(m.on_loan()) >= MAX_LOANS or m.has_title(title):
            return ""
        best = None
        for c in self._copies.values():
            if c.title == title and c.current is None and (best is None or c.id < best.id):
                best = c
        if best is None:
            return ""
        l = _Loan(best.id, title, member_id, ts, ts + LOAN_DAYS)
        best.current = l
        m.loans.append(l)
        self._checkouts[title] = self._checkouts.get(title, 0) + 1
        return best.id

    def return_copy(self, ts: int, copy_id: str) -> bool:
        c = self._copies.get(copy_id)
        if c is None or c.current is None:
            return False
        c.current.back = ts
        c.current = None
        return True

    def borrower(self, ts: int, copy_id: str) -> str:
        c = self._copies.get(copy_id)
        return c.current.member if c is not None and c.current is not None else ""

    def available(self, ts: int, title: str) -> int:
        n = 0
        for c in self._copies.values():
            if c.title == title and c.current is None:
                n += 1
        return n

    def loans_of(self, ts: int, member_id: str) -> list[str]:
        m = self._members.get(member_id)
        return sorted(l.copy_id for l in m.on_loan()) if m else []

    def popular(self, ts: int, n: int) -> list[str]:
        """Up to n titles as "title(checkouts)", most checkouts first, ties by title."""
        titles = sorted(self._checkouts, key=lambda t: (-self._checkouts[t], t))
        return [f"{t}({self._checkouts[t]})" for t in titles[:n]]

    def due_date(self, ts: int, copy_id: str) -> int:
        c = self._copies.get(copy_id)
        return c.current.due if c is not None and c.current is not None else -1

    def renew(self, ts: int, copy_id: str) -> int:
        c = self._copies.get(copy_id)
        if c is None or c.current is None:
            return -1
        l = c.current
        if ts > l.due or l.renewals >= 2:
            return -1
        l.renewals += 1
        l.due += LOAN_DAYS
        return l.due

    def fines(self, ts: int, member_id: str) -> int:
        total = 0
        m = self._members.get(member_id)
        if m:
            for l in m.loans:
                if l.back != -1 and l.back > l.due:
                    total += min(FINE_CAP, FINE_PER_DAY * (l.back - l.due))
        return total

    def history(self, ts: int, member_id: str) -> list[str]:
        m = self._members.get(member_id)
        return [l.title for l in m.loans] if m else []

    def merge(self, ts: int, keep_id: str, drop_id: str) -> bool:
        k, d = self._members.get(keep_id), self._members.get(drop_id)
        if k is None or d is None or keep_id == drop_id:
            return False
        if len(k.on_loan()) + len(d.on_loan()) > MAX_LOANS:
            return False
        for l in d.on_loan():
            if k.has_title(l.title):
                return False
        for l in d.loans:
            l.member = keep_id
        k.loans.extend(d.loans)
        k.loans.sort(key=lambda l: l.out)  # stable
        del self._members[drop_id]
        return True
