"""One B2B invoice: discounted line items, tax by category, credit notes, payments and late fees.

All money is an int number of cents. Days are day numbers (0, 1, 2, ...).
"""

class InvalidTermsError(ValueError):
    pass


class InvalidCategoryError(ValueError):
    pass


class InvalidQuantityError(ValueError):
    pass


class InvalidPriceError(ValueError):
    pass


class InvalidAmountError(ValueError):
    pass


class InvalidDayError(ValueError):
    pass


TERMS = {"net15": 15, "net30": 30, "net60": 60}
TAX_BP = {"standard": 2000, "reduced": 500, "zero": 0}  # basis points: 2000 = 20%
LATE_FEE_BP = 150  # 1.5%


def _half_up(numerator, denominator):
    """numerator / denominator rounded to the nearest int, an exact half rounding up (both >= 0)."""
    return (numerator + denominator // 2) // denominator


def _discount_bp(quantity):
    if quantity >= 100:
        return 1000
    if quantity >= 50:
        return 500
    return 0


class Invoice:
    def __init__(self, issue_day, terms):
        if terms not in TERMS:
            raise InvalidTermsError(f"unknown payment terms {terms!r}")
        self._issue_day = issue_day
        self._terms = TERMS[terms]
        self._lines = []  # (category, net)
        self._settled = 0  # payments + credit notes

    def add_line(self, unit_price, quantity, category):
        if category not in TAX_BP:
            raise InvalidCategoryError(f"unknown tax category {category!r}")
        if quantity < 1:
            raise InvalidQuantityError("quantity must be at least 1")
        if unit_price < 0:
            raise InvalidPriceError("unit price must not be negative")
        gross = unit_price * quantity
        net = gross - _half_up(gross * _discount_bp(quantity), 10000)
        self._lines.append((category, net))
        return net

    def subtotal(self):
        return sum(net for _, net in self._lines)

    def tax(self):
        by_category = {}
        for category, net in self._lines:
            by_category[category] = by_category.get(category, 0) + net
        return sum(_half_up(net * TAX_BP[c], 10000) for c, net in by_category.items())

    def total(self):
        return self.subtotal() + self.tax()

    def due_day(self):
        return self._issue_day + self._terms

    def balance(self):
        return self.total() - self._settled

    def _settle(self, amount):
        if amount < 1 or amount > self.balance():
            raise InvalidAmountError("amount must be 1 to the balance")
        self._settled += amount

    def pay(self, amount):
        self._settle(amount)

    def credit_note(self, amount):
        self._settle(amount)

    def amount_due(self, day):
        if day < self._issue_day:
            raise InvalidDayError("day is before the issue day")
        owed = self.balance()
        if day > self.due_day() and owed > 0:
            return owed + _half_up(owed * LATE_FEE_BP, 10000)
        return owed
