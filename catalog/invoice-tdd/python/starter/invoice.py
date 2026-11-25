"""One B2B invoice: discounted line items, tax by category, credit notes, payments and late fees.

All money is an int number of cents. Days are day numbers (0, 1, 2, ...). Every error is a ValueError subclass: one class per kind.
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


class Invoice:
    def __init__(self, issue_day, terms):
        """A new, empty invoice issued on issue_day with terms "net15", "net30" or "net60"."""
        raise NotImplementedError

    def add_line(self, unit_price, quantity, category):
        """Adds a line item and returns its net amount (after discount, before tax), in cents."""
        raise NotImplementedError

    def subtotal(self):
        """Sum of the line nets, in cents."""
        raise NotImplementedError

    def tax(self):
        """Tax on the invoice, in cents."""
        raise NotImplementedError

    def total(self):
        """subtotal() + tax(), in cents."""
        raise NotImplementedError

    def due_day(self):
        """The last day the invoice can be paid without a late fee."""
        raise NotImplementedError

    def pay(self, amount):
        """Records a payment of amount cents."""
        raise NotImplementedError

    def credit_note(self, amount):
        """Records a credit note of amount cents."""
        raise NotImplementedError

    def balance(self):
        """total() less every payment and credit note, in cents."""
        raise NotImplementedError

    def amount_due(self, day):
        """What the customer owes on day: balance() plus any late fee, in cents."""
        raise NotImplementedError
