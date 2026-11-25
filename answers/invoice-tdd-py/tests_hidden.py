import pytest

from invoice import Invoice


def _hidden_line(unit_price, quantity, category="zero"):
    return Invoice(0, "net30").add_line(unit_price, quantity, category)


def _hidden_invoice(*lines, issue_day=0, terms="net30"):
    inv = Invoice(issue_day, terms)
    for line in lines:
        inv.add_line(*line)
    return inv


def _hidden_state(inv):
    return (inv.subtotal(), inv.tax(), inv.total(), inv.balance(), inv.due_day())


def test_p1_line_below_discount_tiers():
    assert _hidden_line(1999, 3, "standard") == 5997
    assert _hidden_line(200, 49) == 9800
    assert _hidden_line(1, 49) == 49


def test_p1_discount_tiers_start_at_50_and_100():
    assert _hidden_line(200, 50) == 9500
    assert _hidden_line(200, 99) == 18810
    assert _hidden_line(200, 100) == 18000
    assert _hidden_line(7, 100) == 630


def test_p1_discount_rounded_half_up():
    assert _hidden_line(1, 50) == 47  # 2.5 cents of discount rounds to 3
    assert _hidden_line(3, 51) == 145  # 7.65 rounds to 8


def test_p1_free_line_allowed():
    inv = _hidden_invoice((0, 5, "standard"))
    assert _hidden_state(inv) == (0, 0, 0, 0, 30)


def test_p1_empty_invoice():
    inv = Invoice(3, "net15")
    assert _hidden_state(inv) == (0, 0, 0, 0, 18)
    assert inv.amount_due(100) == 0


def test_p1_tax_by_category():
    inv = _hidden_invoice((4250, 2, "standard"), (1599, 10, "reduced"), (2000, 3, "zero"))
    assert inv.subtotal() == 30490
    assert inv.tax() == 2500  # 1700 + 799.5 rounded up + 0
    assert inv.total() == 32990
    assert inv.balance() == 32990


def test_p1_tax_rounded_once_per_category_not_per_line():
    assert _hidden_invoice((3, 1, "standard"), (3, 1, "standard")).tax() == 1
    assert _hidden_invoice((6, 1, "reduced"), (6, 1, "reduced"), (6, 1, "reduced")).tax() == 1


def test_p1_tax_rounded_half_up():
    assert _hidden_invoice((10, 1, "reduced")).tax() == 1
    assert _hidden_invoice((30, 1, "reduced"), (1, 1, "reduced")).tax() == 2


def test_p1_due_day_from_terms():
    assert Invoice(0, "net15").due_day() == 15
    assert Invoice(10, "net30").due_day() == 40
    assert Invoice(7, "net60").due_day() == 67


def test_p1_rejects_unknown_terms():
    for terms in ("net45", "NET30", "net 30", ""):
        with pytest.raises(ValueError):
            Invoice(0, terms)


def test_p1_bad_line_rejected_and_changes_nothing():
    inv = _hidden_invoice((1000, 1, "standard"))
    before = _hidden_state(inv)
    for line in ((100, 1, "Standard"), (100, 1, "luxury"), (100, 0, "zero"), (100, -2, "zero"), (-1, 1, "zero")):
        with pytest.raises(ValueError):
            inv.add_line(*line)
    assert _hidden_state(inv) == before


def test_p1_payments_and_credit_notes_reduce_balance():
    inv = _hidden_invoice((100000, 1, "standard"))
    inv.pay(40000)
    assert inv.balance() == 80000
    inv.credit_note(20000)
    assert inv.balance() == 60000
    assert inv.total() == 120000


def test_p1_settle_up_to_the_balance_only():
    inv = _hidden_invoice((500, 1, "zero"))
    for settle in (inv.pay, inv.credit_note):
        for amount in (0, -100, 501):
            with pytest.raises(ValueError):
                settle(amount)
    assert inv.balance() == 500
    inv.credit_note(200)
    with pytest.raises(ValueError):
        inv.pay(301)
    inv.pay(300)
    assert inv.balance() == 0
    with pytest.raises(ValueError):
        inv.credit_note(1)
    assert inv.balance() == 0


def test_p1_lines_added_after_payment_raise_balance():
    inv = _hidden_invoice((500, 1, "zero"))
    inv.pay(500)
    inv.add_line(1000, 1, "standard")
    assert inv.balance() == 1200


def test_p1_no_late_fee_until_after_due_day():
    inv = _hidden_invoice((100000, 1, "standard"), issue_day=5, terms="net15")
    assert inv.amount_due(5) == 120000
    assert inv.amount_due(20) == 120000
    assert inv.amount_due(21) == 121800
    assert inv.amount_due(400) == 121800


def test_p1_late_fee_on_remaining_balance():
    inv = _hidden_invoice((100000, 1, "standard"), issue_day=5, terms="net15")
    inv.pay(40000)
    assert inv.amount_due(21) == 81200
    inv.credit_note(20000)
    assert inv.amount_due(100) == 60900
    assert inv.balance() == 60000


def test_p1_late_fee_rounded_half_up():
    assert _hidden_invoice((100, 1, "zero")).amount_due(31) == 102  # 1.5 cents rounds to 2
    assert _hidden_invoice((33, 1, "zero")).amount_due(31) == 33  # 0.495 rounds to 0
    assert _hidden_invoice((34, 1, "zero")).amount_due(31) == 35


def test_p1_settled_invoice_has_no_late_fee():
    inv = _hidden_invoice((2500, 2, "reduced"))
    inv.credit_note(5250)
    assert inv.amount_due(90) == 0


def test_p1_amount_due_before_issue_day_rejected():
    inv = _hidden_invoice((1000, 1, "zero"), issue_day=10)
    with pytest.raises(ValueError):
        inv.amount_due(9)
    assert inv.amount_due(10) == 1000
