import time

import pytest

from inventory import (
    Backdated,
    Duplicate,
    InsufficientStock,
    Invalid,
    InventoryError,
    NotActive,
    NotFound,
    Rule,
    Service,
    TransferState,
    UnknownWarehouse,
)


def _hidden_service(*warehouses):
    s = Service()
    for w in warehouses:
        s.add_warehouse(w)
    return s


def _hidden_status(s, id):
    r = s.reservation(id)
    assert r is not None, f"reservation {id} not found"
    return f"{r.status}@{r.updated_at}"


def _hidden_plan(plan):
    return [(g.sku, g.position, g.qty, g.source) for g in plan]


def _hidden_transfer(s, id):
    t = s.transfer(id)
    return (t.id, t.from_wh, t.to_wh, t.sku, t.qty, t.status, t.shipped_at, t.received_at, t.bin)


# ---------------------------------------------------------------- phase 1


def test_p1_release_after_hold_ran_out_returns_stock_once():
    s = _hidden_service("east")
    s.receive("east", "A-01", "LAMP", 10, 100)
    s.reserve("o1", "east", "LAMP", 6, 600, 200)  # runs out at 800
    assert s.available("east", "LAMP", 799) == 4
    s.release("o1", 900)  # the order service cancels late
    assert _hidden_status(s, "o1") == "expired@800"
    assert s.available("east", "LAMP", 900) == 10
    with pytest.raises(InsufficientStock):
        s.reserve("o2", "east", "LAMP", 11, 600, 910)
    s.reserve("o3", "east", "LAMP", 10, 600, 920)
    s.commit("o3", 930)
    assert s.on_hand("east", "LAMP") == 0
    assert s.available("east", "LAMP", 940) == 0


def test_p1_late_release_after_hold_ran_out_at_exact_second():
    s = _hidden_service("east")
    s.receive("east", "A-01", "LAMP", 5, 0)
    s.reserve("o1", "east", "LAMP", 3, 60, 10)  # runs out at 70
    s.reserve("o2", "east", "LAMP", 2, 600, 20)
    s.release("o1", 70)
    s.release("o1", 71)  # retried
    assert _hidden_status(s, "o1") == "expired@70"
    assert s.available("east", "LAMP", 72) == 3
    with pytest.raises(InsufficientStock):
        s.reserve("o3", "east", "LAMP", 4, 60, 80)


def test_p1_release_and_commit_lifecycle():
    s = _hidden_service("east")
    s.receive("east", "A-01", "KETTLE", 8, 0)
    s.reserve("o1", "east", "KETTLE", 3, 300, 10)
    s.reserve("o2", "east", "KETTLE", 4, 300, 20)
    s.release("o1", 30)
    s.release("o1", 40)  # retry is a no-op
    assert _hidden_status(s, "o1") == "released@30"
    assert s.available("east", "KETTLE", 40) == 4
    s.commit("o2", 50)
    assert _hidden_status(s, "o2") == "committed@50"
    assert s.on_hand("east", "KETTLE") == 4
    assert s.available("east", "KETTLE", 60) == 4
    with pytest.raises(NotActive):
        s.release("o2", 70)
    with pytest.raises(NotActive):
        s.commit("o1", 70)
    with pytest.raises(NotActive):
        s.commit("o2", 70)
    with pytest.raises(NotFound):
        s.release("nope", 70)
    s.reserve("o3", "east", "KETTLE", 4, 100, 80)
    with pytest.raises(NotActive):
        s.commit("o3", 180)  # commit at expiry
    assert _hidden_status(s, "o3") == "expired@180"
    assert s.on_hand("east", "KETTLE") == 4


def test_p1_pick_finds_bins_put_away_after_an_earlier_pick():
    s = _hidden_service("east")
    s.receive("east", "B-02", "TOWEL", 4, 0)
    s.reserve("o1", "east", "TOWEL", 3, 600, 10)
    s.commit("o1", 20)  # B-02 now holds 1
    s.receive("east", "A-09", "TOWEL", 6, 30)
    s.receive("east", "C-01", "TOWEL", 5, 31)
    assert s.on_hand("east", "TOWEL") == 12
    s.reserve("o2", "east", "TOWEL", 9, 600, 40)
    s.commit("o2", 50)
    assert s.bin_qty("east", "A-09", "TOWEL") == 0
    assert s.bin_qty("east", "B-02", "TOWEL") == 0
    assert s.bin_qty("east", "C-01", "TOWEL") == 3
    assert s.on_hand("east", "TOWEL") == 3


def test_p1_transfer_arrival_into_new_bin_is_pickable():
    s = _hidden_service("east", "west")
    s.receive("west", "W-1", "RUG", 20, 0)
    s.receive("east", "E-5", "RUG", 2, 0)
    s.reserve("o1", "east", "RUG", 2, 600, 10)
    s.commit("o1", 20)
    s.start_transfer("t1", "west", "east", "RUG", 7, 30)
    s.receive_transfer("t1", "E-1", 40)
    s.reserve("o2", "east", "RUG", 7, 600, 50)
    s.commit("o2", 60)
    assert s.bin_qty("east", "E-1", "RUG") == 0
    assert s.on_hand("east", "RUG") == 0


def test_p1_pick_order_and_short_pick():
    s = _hidden_service("east")
    s.receive("east", "C-03", "CUP", 5, 0)
    s.receive("east", "A-10", "CUP", 2, 0)
    s.receive("east", "A-02", "CUP", 3, 0)
    s.receive("east", "A-02", "BOWL", 9, 0)
    s.reserve("o1", "east", "CUP", 4, 600, 10)
    s.commit("o1", 20)
    assert s.bin_qty("east", "A-02", "CUP") == 0
    assert s.bin_qty("east", "A-10", "CUP") == 1
    assert s.bin_qty("east", "C-03", "CUP") == 5
    assert s.bin_qty("east", "A-02", "BOWL") == 9
    assert s.available("east", "CUP", 30) == 6


def test_p1_transfer_cannot_take_reserved_stock():
    s = _hidden_service("east", "west")
    s.receive("east", "A-01", "CHAIR", 10, 0)
    s.reserve("o1", "east", "CHAIR", 8, 3600, 10)
    with pytest.raises(InsufficientStock):
        s.start_transfer("t1", "east", "west", "CHAIR", 5, 20)
    assert s.transfer("t1") is None
    assert s.inbound("west", "CHAIR") == 0
    assert s.on_hand("east", "CHAIR") == 10
    t = s.start_transfer("t2", "east", "west", "CHAIR", 2, 30)
    assert (t.id, t.from_wh, t.to_wh, t.sku, t.qty, t.status, t.shipped_at, t.received_at, t.bin) == (
        "t2", "east", "west", "CHAIR", 2, "in_transit", 30, 0, "")
    assert s.available("east", "CHAIR", 40) == 0
    s.commit("o1", 50)
    assert s.on_hand("east", "CHAIR") == 0


def test_p1_transfer_lifecycle():
    s = _hidden_service("east", "west")
    s.receive("east", "A-01", "DESK", 6, 0)
    with pytest.raises(Invalid):
        s.start_transfer("t1", "east", "east", "DESK", 1, 10)
    with pytest.raises(UnknownWarehouse):
        s.start_transfer("t1", "east", "south", "DESK", 1, 10)
    with pytest.raises(InsufficientStock):
        s.start_transfer("t1", "east", "west", "DESK", 7, 10)
    s.start_transfer("t1", "east", "west", "DESK", 4, 10)
    with pytest.raises(Duplicate):
        s.start_transfer("t1", "east", "west", "DESK", 1, 11)
    assert s.inbound("west", "DESK") == 4
    assert s.on_hand("west", "DESK") == 0
    s.receive_transfer("t1", "Z-9", 20)
    with pytest.raises(TransferState):
        s.receive_transfer("t1", "Z-9", 21)
    assert s.inbound("west", "DESK") == 0
    assert s.bin_qty("west", "Z-9", "DESK") == 4
    assert s.on_hand("east", "DESK") == 2
    assert _hidden_transfer(s, "t1") == ("t1", "east", "west", "DESK", 4, "received", 10, 20, "Z-9")


def test_p1_validation_and_clock():
    s = _hidden_service("east")
    with pytest.raises(Duplicate):
        s.add_warehouse("east")
    with pytest.raises(Invalid):
        s.receive("east", "A-01", "PEN", 0, 1)
    with pytest.raises(UnknownWarehouse):
        s.receive("west", "A-01", "PEN", 1, 1)
    s.receive("east", "A-01", "PEN", 3, 100)
    with pytest.raises(Backdated):
        s.receive("east", "A-01", "PEN", 1, 99)
    with pytest.raises(Invalid):
        s.reserve("o1", "east", "PEN", 1, 0, 100)
    with pytest.raises(InsufficientStock):
        s.reserve("o1", "east", "PEN", 4, 60, 100)
    r = s.reserve("o1", "east", "PEN", 3, 60, 100)
    assert (r.warehouse, r.sku, r.qty, r.created_at, r.expires_at, r.status) == ("east", "PEN", 3, 100, 160, "active")
    with pytest.raises(Duplicate):
        s.reserve("o1", "east", "PEN", 1, 60, 101)
    with pytest.raises(Backdated):
        s.release("o1", 50)
    assert s.available("east", "PEN", 159) == 0
    assert s.available("east", "PEN", 160) == 3
    with pytest.raises(Backdated):
        s.available("east", "PEN", 10)


# ---------------------------------------------------------------- phase 2


def test_p2_reorders_up_to_max_at_or_below_min():
    s = _hidden_service("east")
    s.receive("east", "A-01", "SOAP", 10, 0)
    s.receive("east", "A-02", "SALT", 11, 0)
    s.receive("east", "A-03", "OIL", 3, 0)
    s.set_rule("east", "SOAP", Rule(10, 50))
    s.set_rule("east", "SALT", Rule(10, 50))
    s.set_rule("east", "OIL", Rule(5, 12, 1))
    s.set_rule("east", "FLOUR", Rule(0, 20))
    plan = s.replenishment("east", 10)
    assert _hidden_plan(plan) == [("FLOUR", 0, 20, ""), ("OIL", 3, 9, ""), ("SOAP", 10, 40, "")]
    assert s.on_hand("east", "SOAP") == 10
    assert len(s.replenishment("east", 20)) == 3


def test_p2_case_packs_round_up():
    s = _hidden_service("east")
    s.receive("east", "A-01", "TEA", 7, 0)
    s.receive("east", "A-01", "JAM", 2, 0)
    s.set_rule("east", "TEA", Rule(8, 30, 12))
    s.set_rule("east", "JAM", Rule(4, 26, 6))
    assert _hidden_plan(s.replenishment("east", 10)) == [("JAM", 2, 24, ""), ("TEA", 7, 24, "")]


def test_p2_active_holds_reduce_position():
    s = _hidden_service("east")
    s.receive("east", "A-01", "SOCK", 30, 0)
    s.set_rule("east", "SOCK", Rule(20, 40, 5))
    s.reserve("o1", "east", "SOCK", 6, 100, 10)  # runs out at 110
    s.reserve("o2", "east", "SOCK", 5, 500, 20)
    s.reserve("o3", "east", "SOCK", 2, 500, 30)
    s.release("o3", 40)
    assert _hidden_plan(s.replenishment("east", 109)) == [("SOCK", 19, 25, "")]  # while o1 held
    assert _hidden_plan(s.replenishment("east", 110)) == []  # o1 ran out
    s.commit("o2", 120)
    assert _hidden_plan(s.replenishment("east", 130)) == []  # after shipping o2
    s.reserve("o4", "east", "SOCK", 6, 500, 140)
    assert _hidden_plan(s.replenishment("east", 150)) == [("SOCK", 19, 25, "")]  # o4 held


def test_p2_inbound_transfers_count_once():
    s = _hidden_service("east", "west")
    s.receive("east", "A-01", "BOOT", 4, 0)
    s.receive("west", "W-01", "BOOT", 45, 0)
    s.set_rule("east", "BOOT", Rule(10, 30))
    s.set_rule("west", "BOOT", Rule(15, 60))
    assert _hidden_plan(s.replenishment("east", 10)) == [("BOOT", 4, 26, "west")]
    s.start_transfer("t1", "west", "east", "BOOT", 5, 20)
    assert _hidden_plan(s.replenishment("east", 30)) == [("BOOT", 9, 21, "west")]  # in transit
    assert _hidden_plan(s.replenishment("west", 30)) == []
    s.receive_transfer("t1", "A-02", 40)
    assert _hidden_plan(s.replenishment("east", 50)) == [("BOOT", 9, 21, "west")]  # received
    s.start_transfer("t2", "west", "east", "BOOT", 2, 60)
    assert _hidden_plan(s.replenishment("east", 70)) == []  # second transfer


def test_p2_source_is_largest_surplus_over_its_min():
    s = _hidden_service("north", "east", "west", "south")
    s.set_rule("north", "BIKE", Rule(5, 25))
    s.receive("east", "A", "BIKE", 40, 0)
    s.set_rule("east", "BIKE", Rule(30, 60))  # surplus 10
    s.receive("west", "A", "BIKE", 30, 0)  # no rule: surplus 30
    s.receive("south", "A", "BIKE", 34, 0)
    s.reserve("o1", "south", "BIKE", 4, 1000, 1)  # surplus 30
    assert _hidden_plan(s.replenishment("north", 10)) == [("BIKE", 0, 25, "south")]  # tie: lowest id
    s.release("o1", 20)
    assert _hidden_plan(s.replenishment("north", 30)) == [("BIKE", 0, 25, "south")]  # south grows
    s.reserve("o2", "south", "BIKE", 11, 1000, 40)
    s.reserve("o3", "west", "BIKE", 6, 1000, 40)
    assert _hidden_plan(s.replenishment("north", 50)) == [("BIKE", 0, 25, "")]  # nobody can spare 25
    s.receive("north", "N", "BIKE", 3, 60)
    assert _hidden_plan(s.replenishment("north", 70)) == [("BIKE", 3, 22, "west")]  # smaller need
    s.reserve("o4", "west", "BIKE", 2, 1000, 80)
    s.reserve("o5", "south", "BIKE", 2, 1000, 80)
    assert _hidden_plan(s.replenishment("north", 90)) == [("BIKE", 3, 22, "west")]  # exactly enough


def test_p2_errors_and_empty_plans():
    s = _hidden_service("east", "west")
    with pytest.raises(UnknownWarehouse):
        s.replenishment("south", 10)
    assert s.replenishment("east", 10) == []
    s.set_rule("west", "CAP", Rule(1, 9))
    assert s.replenishment("east", 20) == []  # other warehouse's rule
    with pytest.raises(Backdated):
        s.replenishment("west", 5)
    with pytest.raises(Invalid):
        s.set_rule("east", "CAP", Rule(5, 5))
    assert _hidden_plan(s.replenishment("west", 30)) == [("CAP", 0, 9, "")]


# ---------------------------------------------------------------- phase 3

_hidden_SKUS, _hidden_N = 20, 30000


def test_p3_flash_sale_at_scale():
    s = _hidden_service("main", "overflow")
    skus, n = _hidden_SKUS, _hidden_N
    sku = lambda i: f"SKU-{i % skus}"
    for i in range(skus):
        s.receive("main", f"A-{i}", sku(i), 400, 0)
        s.receive("overflow", f"Z-{i}", sku(i), 3000, 0)
        s.set_rule("main", sku(i), Rule(1200, 2400, 100))
    sold_out = committed = not_active = from_overflow = restocked = 0
    start = time.perf_counter()
    for i in range(n):
        now = 1 + i
        qty = 1 + i % 5
        # The product page checks stock, then checkout holds it: card payments for
        # 15 minutes, bank transfers and pre-orders for up to 12 hours.
        if s.available("main", sku(i), now) < qty:
            sold_out += 1
        else:
            s.reserve(f"o{i}", "main", sku(i), qty, 900 + (i * 7919) % 42300, now)
        if i % 3 == 0 and i >= 5:
            try:
                s.commit(f"o{i - 5}", now)
                committed += 1
            except InventoryError:
                not_active += 1
        if i % 5 == 0 and i >= 2:
            try:
                s.release(f"o{i - 2}", now)
            except NotFound:
                pass
        if i % 4000 == 3999:
            for sg in s.replenishment("main", now):
                if sg.source:
                    from_overflow += 1
                s.receive("main", "A-" + sg.sku[4:], sg.sku, sg.qty, now)
                restocked += sg.qty
    elapsed = time.perf_counter() - start
    total = sum(s.available("main", sku(i), n + 1) for i in range(skus))
    assert (
        f"soldOut={sold_out} committed={committed} notActive={not_active} fromOverflow={from_overflow} "
        f"restocked={restocked} available={total} onhand={s.on_hand('main', sku(7))}"
    ) == "soldOut=724 committed=7757 notActive=2241 fromOverflow=44 restocked=82500 available=41113 onhand=4263"
    assert elapsed < 1.5, f"{n} checkouts took {elapsed:.2f}s (budget 1.5s)"
