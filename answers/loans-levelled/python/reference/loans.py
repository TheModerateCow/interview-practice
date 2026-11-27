"""Loan servicing for a consumer lender: instalment schedules, payments, late fees,
payoff quotes and restructuring."""

GRACE_DAYS = 10
LATE_FEE = 2500
PARTS = ("fee", "interest", "principal")  # allocation order within one instalment


def _instalments(start, principal, months, rate_bp):
    """Flat interest rounded half up; the last instalment absorbs the principal remainder."""
    interest = (principal * rate_bp + 5000) // 10000
    base = principal // months
    out = []
    for k in range(1, months + 1):
        p = principal - base * (months - 1) if k == months else base
        out.append({"due": start + 30 * k, "amount": p + interest, "fee": 0, "interest": interest,
                    "principal": p, "charged": False})
    return out


def _left(i):
    return i["fee"] + i["interest"] + i["principal"]


class Lender:
    """Every method takes `day` first: today's date as an integer. Days only ever increase."""

    def __init__(self):
        self.loans = {}  # loan_id -> {"rate": rate_bp, "inst": [instalment, ...] in due order}

    # ---------------------------------------------------------------- level 1

    def originate(self, day: int, loan_id: str, principal: int, months: int, rate_bp: int) -> bool:
        if loan_id in self.loans or principal <= 0 or months <= 0 or rate_bp < 0:
            return False
        self.loans[loan_id] = {"rate": rate_bp, "inst": _instalments(day, principal, months, rate_bp)}
        return True

    def schedule(self, day: int, loan_id: str) -> list[str]:
        loan = self.loans.get(loan_id)
        return [f"{i['due']}:{i['amount']}" for i in loan["inst"]] if loan else []

    def amount_due(self, day: int, loan_id: str) -> int:
        loan = self.loans.get(loan_id)
        if loan is None:
            return -1
        return sum(_left(i) for i in loan["inst"] if i["due"] <= day)

    # ---------------------------------------------------------------- level 2

    def pay(self, day: int, loan_id: str, amount: int) -> int:
        loan = self.loans.get(loan_id)
        if loan is None or amount <= 0:
            return -1
        for i in loan["inst"]:
            for part in PARTS:
                take = min(amount, i[part])
                i[part] -= take
                amount -= take
        return amount

    def owed(self, day: int, loan_id: str) -> int:
        loan = self.loans.get(loan_id)
        return sum(_left(i) for i in loan["inst"]) if loan else -1

    def principal_left(self, day: int, loan_id: str) -> int:
        loan = self.loans.get(loan_id)
        return sum(i["principal"] for i in loan["inst"]) if loan else -1

    # ---------------------------------------------------------------- level 3

    def charge_late_fees(self, day: int) -> int:
        n = 0
        for loan in self.loans.values():
            for i in loan["inst"]:
                if i["due"] + GRACE_DAYS < day and _left(i) > 0 and not i["charged"]:
                    i["charged"] = True
                    i["fee"] += LATE_FEE
                    n += 1
        return n

    def status(self, day: int, loan_id: str) -> str:
        loan = self.loans.get(loan_id)
        if loan is None:
            return ""
        if all(_left(i) == 0 for i in loan["inst"]):
            return "paid_off"
        if any(i["due"] + GRACE_DAYS < day and _left(i) > 0 for i in loan["inst"]):
            return "late"
        return "current"

    # ---------------------------------------------------------------- level 4

    def payoff_quote(self, day: int, loan_id: str) -> int:
        loan = self.loans.get(loan_id)
        if loan is None:
            return -1
        return sum(i["principal"] + (i["fee"] + i["interest"] if i["due"] <= day else 0) for i in loan["inst"])

    def restructure(self, day: int, loan_id: str, months: int) -> bool:
        loan = self.loans.get(loan_id)
        if loan is None or months <= 0:
            return False
        future = [i for i in loan["inst"] if i["due"] > day]
        if not future or any(_left(i) != i["amount"] for i in future):
            return False
        kept = [i for i in loan["inst"] if i["due"] <= day]
        rest = sum(i["principal"] for i in future)
        loan["inst"] = kept + _instalments(day, rest, months, loan["rate"])
        return True
