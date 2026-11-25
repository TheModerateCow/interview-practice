import time

import pytest

from ledger import (
    DAY,
    FEES_ACCOUNT,
    BANK_ACCOUNT,
    CLEARING_ACCOUNT,
    IN_TRANSIT_ACCOUNT,
    Backdated,
    Duplicate,
    Entry,
    InsufficientFunds,
    Invalid,
    Ledger,
    NotFound,
    PayoutState,
    Posting,
    Pricing,
    Unbalanced,
    UnknownCurrency,
    UnknownMerchant,
    available_account,
    pending_account,
)


def _hidden_merchant(l, mid, bps, fixed=None):
    l.add_merchant(mid, Pricing(bps, fixed or {}))


def _hidden_capture(l, cid, m, cur, amount, method, ts):
    l.capture(cid, m, cur, amount, method, ts)


def _hidden_lines(ls):
    return [tuple(x) for x in ls]


def _hidden_batches(bs):
    return [(b.id, b.merchant, b.currency, b.ts, b.charges, b.gross, b.fees, b.net) for b in bs]


def _hidden_fund(l, m, cur, amount, ts):
    """Put amount straight into a merchant's available balance, as an ops adjustment."""
    l.post(Entry(ts, [Posting(available_account(m), cur, amount), Posting(CLEARING_ACCOUNT, cur, -amount)], "adjustment"))


# ---------------------------------------------------------------- phase 1


def _hidden_statement_ledger():
    l = Ledger()
    _hidden_merchant(l, "m1", 250)
    _hidden_capture(l, "c1", "m1", "USD", 1000, "card", 10)
    _hidden_capture(l, "c2", "m1", "USD", 2500, "card", 20)
    _hidden_capture(l, "c3", "m1", "USD", 400, "card", 30)
    l.refund("c2", 500, 40)
    return l


_HIDDEN_FULL = [(40, "e4", -500, 3400), (30, "e3", 400, 3900), (20, "e2", 2500, 3500), (10, "e1", 1000, 1000)]


def test_p1_statement_leaves_balances_alone():
    l = _hidden_statement_ledger()
    acct = pending_account("m1")
    assert _hidden_lines(l.statement(acct, "USD", 0, 100)) == _HIDDEN_FULL
    assert l.balance(acct, "USD") == 3400
    assert l.balance_at(acct, "USD", 25) == 3500
    assert l.balance_at(acct, "USD", 5) == 0
    assert l.balance_at(acct, "USD", 40) == 3400
    assert l.trial_balance("USD") == 0


def test_p1_repeated_statements_agree():
    l = _hidden_statement_ledger()
    acct = pending_account("m1")
    first = _hidden_lines(l.statement(acct, "USD", 15, 35))
    assert first == [(30, "e3", 400, 3900), (20, "e2", 2500, 3500)]
    assert _hidden_lines(l.statement(acct, "USD", 15, 35)) == first
    assert _hidden_lines(l.statement(acct, "USD", 0, 100)) == _HIDDEN_FULL
    assert l.balance_at(acct, "USD", 30) == 3900
    assert l.balance(acct, "USD") == 3400


def test_p1_failed_payout_webhook_retry_credits_once():
    l = Ledger()
    _hidden_merchant(l, "m1", 250)
    _hidden_fund(l, "m1", "USD", 5000, 1)
    l.request_payout("p1", "m1", "USD", 3000, 2)
    assert l.balance(available_account("m1"), "USD") == 2000
    assert l.balance(IN_TRANSIT_ACCOUNT, "USD") == 3000
    l.payout_failed("p1", 3)
    l.payout_failed("p1", 4)  # the bank retries the webhook
    assert l.balance(available_account("m1"), "USD") == 5000
    assert l.balance(IN_TRANSIT_ACCOUNT, "USD") == 0
    p = l.payout("p1")
    assert p is not None
    assert p.status == "failed"
    assert p.updated_at == 3
    with pytest.raises(InsufficientFunds):
        l.request_payout("p2", "m1", "USD", 5001, 5)
    assert l.trial_balance("USD") == 0


def test_p1_paid_payout_cannot_then_fail():
    l = Ledger()
    _hidden_merchant(l, "m1", 250)
    _hidden_fund(l, "m1", "EUR", 8000, 1)
    l.request_payout("p1", "m1", "EUR", 3000, 2)
    l.payout_paid("p1", 3)
    l.payout_paid("p1", 4)
    with pytest.raises(PayoutState):
        l.payout_failed("p1", 5)
    assert l.balance(BANK_ACCOUNT, "EUR") == 3000
    assert l.balance(IN_TRANSIT_ACCOUNT, "EUR") == 0
    assert l.balance(available_account("m1"), "EUR") == 5000
    assert l.payout("p1").status == "paid"


def test_p1_payout_requests():
    l = Ledger()
    _hidden_merchant(l, "m1", 250)
    _hidden_fund(l, "m1", "USD", 1000, 1)
    l.request_payout("p1", "m1", "USD", 1000, 2)
    with pytest.raises(Duplicate):
        l.request_payout("p1", "m1", "USD", 1, 3)
    with pytest.raises(Invalid):
        l.request_payout("p2", "m1", "USD", 0, 3)
    with pytest.raises(InsufficientFunds):
        l.request_payout("p3", "m1", "USD", 1, 3)
    with pytest.raises(NotFound):
        l.payout_paid("nope", 4)
    assert l.balance(available_account("m1"), "USD") == 0


def test_p1_entries_balance_in_every_currency():
    l = Ledger()
    with pytest.raises(Unbalanced):
        l.post(Entry(1, [Posting("ops:suspense", "USD", 100), Posting("ops:suspense", "EUR", -100)], "bad adjustment"))
    assert l.trial_balance("USD") == 0
    assert l.trial_balance("EUR") == 0
    assert l.balance("ops:suspense", "USD") == 0
    l.post(Entry(2, [Posting("customer:9", "USD", -1000), Posting("platform:fx", "USD", 1000),
                     Posting("platform:fx", "EUR", -920), Posting("customer:9", "EUR", 920)], "fx conversion"))
    assert l.balance("platform:fx", "USD") == 1000
    assert l.balance("customer:9", "EUR") == 920
    with pytest.raises(Unbalanced):
        l.post(Entry(3, [Posting("a", "JPY", 500), Posting("b", "JPY", -400),
                         Posting("c", "KWD", 1000), Posting("d", "KWD", -1100)]))
    assert l.trial_balance("JPY") == 0


def test_p1_entry_validation():
    l = Ledger()
    with pytest.raises(Invalid):
        l.post(Entry(1, [Posting("a", "USD", 0), Posting("b", "USD", 0)]))
    with pytest.raises(Invalid):
        l.post(Entry(1, [Posting("a", "USD", 5)]))
    with pytest.raises(UnknownCurrency):
        l.post(Entry(1, [Posting("a", "XYZ", 5), Posting("b", "XYZ", -5)]))
    e = l.post(Entry(10, [Posting("a", "USD", 5), Posting("b", "USD", -5)]))
    assert e.id == "e1"
    with pytest.raises(Backdated):
        l.post(Entry(9, [Posting("a", "USD", 5), Posting("b", "USD", -5)]))


def test_p1_refund_limits():
    l = Ledger()
    _hidden_merchant(l, "m1", 250)
    _hidden_capture(l, "c1", "m1", "GBP", 1000, "card", 1)
    l.refund("c1", 600, 2)
    with pytest.raises(Invalid):
        l.refund("c1", 401, 3)
    l.refund("c1", 400, 4)
    with pytest.raises(Invalid):
        l.refund("c1", 1, 5)
    with pytest.raises(NotFound):
        l.refund("c9", 1, 5)
    with pytest.raises(Duplicate):
        l.capture("c1", "m1", "GBP", 1000, "card", 6)
    with pytest.raises(UnknownMerchant):
        l.capture("c2", "m9", "GBP", 1000, "card", 6)
    assert l.balance(pending_account("m1"), "GBP") == 0
    assert l.charge("c1").refunded == 1000


# ---------------------------------------------------------------- phase 2


def test_p2_settles_available_charges_minus_fees():
    l = Ledger()
    _hidden_merchant(l, "m1", 290, {"USD": 30})
    _hidden_capture(l, "c1", "m1", "USD", 10000, "card", 0)
    _hidden_capture(l, "c2", "m1", "USD", 2500, "card", 100)
    bs = l.settle("m1", 2 * DAY + 50)
    assert _hidden_batches(bs) == [("b1", "m1", "USD", 172850, ["c1"], 10000, 320, 9680)]
    assert l.balance(pending_account("m1"), "USD") == 2500
    assert l.balance(available_account("m1"), "USD") == 9680
    assert l.balance(FEES_ACCOUNT, "USD") == 320
    assert l.trial_balance("USD") == 0
    assert l.charge("c1").batch == "b1"
    assert l.charge("c2").batch == ""


def test_p2_cutoff_is_inclusive_and_charges_settle_once():
    l = Ledger()
    _hidden_merchant(l, "m1", 100)
    _hidden_capture(l, "c1", "m1", "USD", 5000, "bank", 0)
    _hidden_capture(l, "c2", "m1", "USD", 3000, "card", DAY)
    assert len(l.settle("m1", 3 * DAY - 1)) == 0
    bs = l.settle("m1", 3 * DAY)
    assert _hidden_batches(bs) == [("b1", "m1", "USD", 259200, ["c2"], 3000, 30, 2970)]
    assert len(l.settle("m1", 3 * DAY + 10)) == 0
    bs = l.settle("m1", 5 * DAY)
    assert _hidden_batches(bs) == [("b2", "m1", "USD", 432000, ["c1"], 5000, 50, 4950)]
    assert l.balance(pending_account("m1"), "USD") == 0
    assert l.balance(available_account("m1"), "USD") == 7920
    assert l.balance(FEES_ACCOUNT, "USD") == 80


def test_p2_one_batch_per_currency_with_half_up_fees():
    l = Ledger()
    _hidden_merchant(l, "m1", 100, {"USD": 30, "JPY": 40, "EUR": 25})
    _hidden_capture(l, "u1", "m1", "USD", 150, "card", 0)
    _hidden_capture(l, "j1", "m1", "JPY", 12345, "card", 10)
    _hidden_capture(l, "e1", "m1", "EUR", 249, "card", 20)
    _hidden_capture(l, "u2", "m1", "USD", 2049, "card", 30)
    _hidden_capture(l, "j2", "m1", "JPY", 50, "card", 40)
    bs = l.settle("m1", 3 * DAY)
    assert _hidden_batches(bs) == [
        ("b1", "m1", "EUR", 259200, ["e1"], 249, 27, 222),
        ("b2", "m1", "JPY", 259200, ["j1", "j2"], 12395, 204, 12191),
        ("b3", "m1", "USD", 259200, ["u1", "u2"], 2199, 82, 2117),
    ]
    for cur in ("EUR", "JPY", "USD"):
        assert l.balance(pending_account("m1"), cur) == 0
        assert l.trial_balance(cur) == 0
    assert l.balance(available_account("m1"), "JPY") == 12191
    assert l.balance(FEES_ACCOUNT, "USD") == 82


def test_p2_refunds_before_settlement_reduce_gross():
    l = Ledger()
    _hidden_merchant(l, "m1", 300, {"USD": 30})
    _hidden_capture(l, "c1", "m1", "USD", 10000, "card", 0)
    _hidden_capture(l, "c2", "m1", "USD", 800, "card", 10)
    l.refund("c1", 2500, 20)
    l.refund("c2", 800, 30)
    bs = l.settle("m1", 2 * DAY + 10)
    assert _hidden_batches(bs) == [("b1", "m1", "USD", 172810, ["c1", "c2"], 7500, 384, 7116)]
    assert l.balance(available_account("m1"), "USD") == 7116
    assert l.balance(pending_account("m1"), "USD") == 0

    l = Ledger()
    _hidden_merchant(l, "m2", 300, {"USD": 30})
    _hidden_capture(l, "x1", "m2", "USD", 500, "card", 0)
    l.refund("x1", 500, 5)
    bs = l.settle("m2", 2 * DAY)
    assert _hidden_batches(bs) == [("b1", "m2", "USD", 172800, ["x1"], 0, 45, -45)]
    assert l.balance(available_account("m2"), "USD") == -45
    assert l.balance(FEES_ACCOUNT, "USD") == 45
    assert l.trial_balance("USD") == 0


def test_p2_refund_after_settlement_comes_from_available():
    l = Ledger()
    _hidden_merchant(l, "m1", 200, {"USD": 20})
    _hidden_capture(l, "c1", "m1", "USD", 4000, "card", 0)
    _hidden_capture(l, "c2", "m1", "USD", 1000, "bank", 0)
    bs = l.settle("m1", 2 * DAY)
    assert _hidden_batches(bs) == [("b1", "m1", "USD", 172800, ["c1"], 4000, 100, 3900)]
    l.refund("c1", 1500, 2 * DAY + 1)
    assert l.balance(available_account("m1"), "USD") == 2400
    assert l.balance(pending_account("m1"), "USD") == 1000
    l.refund("c2", 1000, 2 * DAY + 2)
    assert l.balance(pending_account("m1"), "USD") == 0
    assert l.charge("c1").batch == "b1"
    bs = l.settle("m1", 5 * DAY)
    assert _hidden_batches(bs) == [("b2", "m1", "USD", 432000, ["c2"], 0, 40, -40)]
    assert l.balance(available_account("m1"), "USD") == 2360
    assert l.balance(FEES_ACCOUNT, "USD") == 140
    assert l.trial_balance("USD") == 0


def test_p2_charge_order_and_merchant_isolation():
    l = Ledger()
    _hidden_merchant(l, "m1", 100)
    _hidden_merchant(l, "m2", 100)
    _hidden_capture(l, "a", "m1", "USD", 1000, "bank", 0)
    _hidden_capture(l, "c", "m1", "USD", 1200, "card", 2 * DAY)
    _hidden_capture(l, "b", "m1", "USD", 1300, "card", 3 * DAY)
    _hidden_capture(l, "z", "m2", "USD", 7000, "card", 3 * DAY + 1)
    _hidden_capture(l, "d", "m1", "USD", 1400, "card", 3 * DAY + 5)
    bs = l.settle("m1", 5 * DAY)
    assert _hidden_batches(bs) == [("b1", "m1", "USD", 432000, ["c", "a", "b"], 3500, 35, 3465)]
    bs = l.settle("m1", 5 * DAY + 5)
    assert _hidden_batches(bs) == [("b2", "m1", "USD", 432005, ["d"], 1400, 14, 1386)]
    assert l.balance(available_account("m1"), "USD") == 4851
    assert l.balance(pending_account("m2"), "USD") == 7000
    assert l.balance(available_account("m2"), "USD") == 0
    with pytest.raises(UnknownMerchant):
        l.settle("nobody", 6 * DAY)
    with pytest.raises(Backdated):
        l.settle("m2", 4 * DAY)
    bs = l.settle("m2", 6 * DAY)
    assert _hidden_batches(bs) == [("b3", "m2", "USD", 518400, ["z"], 7000, 70, 6930)]


# ---------------------------------------------------------------- phase 3


def test_p3_settlement_polling_at_scale():
    l = Ledger()
    _hidden_merchant(l, "big", 250, {"USD": 25})
    n, polls = 15000, 8
    settled = nb = 0
    start = time.perf_counter()
    for i in range(n):
        ts = i * 60
        method = "bank" if i % 4 == 0 else "card"
        l.capture(f"ch{i}", "big", "USD", 500 + i % 1000, method, ts)
        for j in range(polls):
            bs = l.settle("big", ts + j * 60 // polls)
            nb += len(bs)
            settled += sum(len(b.charges) for b in bs)
    elapsed = time.perf_counter() - start
    assert settled == 11040
    assert nb == 11040
    assert l.balance(available_account("big"), "USD") == 10425990
    assert l.balance(pending_account("big"), "USD") == 4016000
    assert l.balance(FEES_ACCOUNT, "USD") == 550510
    assert elapsed < 2.0, f"{n} captures with {polls} settlement polls each took {elapsed:.2f}s (budget 2s)"
