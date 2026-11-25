import time

import pytest

from dispatch import (
    Assignment,
    BadTransition,
    Dispatcher,
    DuplicateCourier,
    DuplicateOrder,
    InvalidCourier,
    NoCourier,
    NotAssigned,
    OrderClosed,
    Point,
    State,
    UnknownOrder,
    travel_minutes,
)


def _hidden_assignments(as_):
    return [f"{a.order_id}->{a.courier_id}" for a in as_]


# ---------------------------------------------------------------- phase 1


def test_p1_assign_nearest_with_room():
    d = Dispatcher()
    d.add_courier("a", Point(0, 0), 1)
    d.add_courier("b", Point(300, 0), 1)
    for oid in ("o1", "o2", "o3"):
        d.place_order(oid, Point(100, 0), Point(100, 900), 0, 5)
    assert d.assign("o1") == "a"
    assert d.assign("o2") == "b"
    with pytest.raises(NoCourier):
        d.assign("o3")
    assert d.order("o3").state is State.PLACED
    with pytest.raises(BadTransition):
        d.assign("o1")
    assert d.order("o1").state is State.ASSIGNED
    assert d.order("o1").courier_id == "a"


def test_p1_assign_ties_and_range():
    d = Dispatcher()
    d.add_courier("zed", Point(0, 200), 1)
    d.add_courier("amy", Point(200, 0), 1)
    d.add_courier("edge", Point(4000, 0), 1)
    d.add_courier("gone", Point(0, 4001), 1)
    for oid in ("o1", "o2", "o3", "o4"):
        d.place_order(oid, Point(0, 0), Point(500, 500), 0, 0)
    assert d.assign("o1") == "amy"  # tie goes to the lower id
    assert d.assign("o2") == "zed"
    assert d.assign("o3") == "edge"  # exactly MAX_PICKUP_DISTANCE away is in range
    with pytest.raises(NoCourier):
        d.assign("o4")


def test_p1_lifecycle_rules():
    d = Dispatcher()
    d.add_courier("c1", Point(0, 0), 1)
    d.place_order("o1", Point(0, 0), Point(250, 0), 0, 0)
    with pytest.raises(BadTransition):
        d.advance("o1", State.DELIVERED)
    with pytest.raises(BadTransition):
        d.advance("o1", State.ASSIGNED)
    d.assign("o1")
    with pytest.raises(BadTransition):
        d.advance("o1", State.DELIVERED)
    d.advance("o1", State.PICKED_UP)
    with pytest.raises(BadTransition):
        d.advance("o1", State.CANCELLED)
    d.advance("o1", State.DELIVERED)
    with pytest.raises(BadTransition):
        d.advance("o1", State.DELIVERED)
    with pytest.raises(UnknownOrder):
        d.advance("nope", State.PICKED_UP)
    with pytest.raises(InvalidCourier):
        d.add_courier("c2", Point(0, 0), 0)
    with pytest.raises(DuplicateCourier):
        d.add_courier("c1", Point(0, 0), 3)


def test_p1_delivery_frees_courier_and_moves_them():
    d = Dispatcher()
    d.add_courier("c1", Point(0, 0), 1)
    d.add_courier("c2", Point(1000, 0), 1)
    d.place_order("o1", Point(0, 0), Point(2000, 0), 0, 0)
    d.assign("o1")
    d.advance("o1", State.PICKED_UP)
    d.advance("o1", State.DELIVERED)
    d.place_order("o2", Point(2000, 100), Point(0, 0), 5, 5)
    assert d.assign("o2") == "c1"  # free again, now at the last customer
    assert d.courier_orders("c1") == ["o2"]


def test_p1_eta_rounds_each_leg_up():
    d = Dispatcher()
    d.add_courier("c1", Point(0, 0), 2)
    d.place_order("o1", Point(600, 0), Point(600, 1100), 0, 0)
    d.assign("o1")
    assert d.eta("o1", 0) == 8  # 600 m + 1100 m
    assert travel_minutes(1) == 1
    assert travel_minutes(500) == 2
    assert travel_minutes(501) == 3
    assert travel_minutes(0) == 0


def test_p1_eta_waits_for_kitchen():
    d = Dispatcher()
    d.add_courier("c1", Point(0, 0), 2)
    d.place_order("o2", Point(0, 700), Point(700, 700), 5, 15)
    d.assign("o2")
    assert d.eta("o2", 5) == 18  # food is ready after the courier arrives


def test_p1_eta_after_pickup():
    d = Dispatcher()
    d.add_courier("c1", Point(0, 0), 2)
    d.place_order("o1", Point(600, 0), Point(600, 1100), 0, 0)
    d.assign("o1")
    d.advance("o1", State.PICKED_UP)
    assert d.eta("o1", 9) == 5  # restaurant to the door
    d.advance("o1", State.DELIVERED)
    with pytest.raises(OrderClosed):
        d.eta("o1", 12)
    d.place_order("o3", Point(0, 0), Point(0, 10), 12, 0)
    with pytest.raises(NotAssigned):
        d.eta("o3", 12)


def test_p1_cancel_frees_courier():
    d = Dispatcher()
    d.add_courier("solo", Point(0, 0), 1)
    d.place_order("o1", Point(100, 100), Point(900, 900), 0, 5)
    d.place_order("o2", Point(100, 100), Point(800, 800), 1, 5)
    d.assign("o1")
    d.advance("o1", State.CANCELLED)
    assert d.assign("o2") == "solo"


def test_p1_cancelled_order_leaves_bag():
    d = Dispatcher()
    d.add_courier("c1", Point(0, 0), 3)
    d.place_order("o1", Point(0, 0), Point(900, 0), 0, 5)
    d.place_order("o2", Point(0, 0), Point(0, 900), 0, 5)
    d.assign("o1")
    d.assign("o2")
    d.advance("o1", State.CANCELLED)
    assert d.courier_orders("c1") == ["o2"]


def test_p1_duplicate_order_keeps_assignment():
    d = Dispatcher()
    d.add_courier("c1", Point(0, 0), 1)
    d.add_courier("c2", Point(3000, 0), 1)
    d.place_order("o1", Point(0, 0), Point(900, 0), 0, 5)
    d.assign("o1")
    with pytest.raises(DuplicateOrder):  # retried checkout
        d.place_order("o1", Point(3000, 0), Point(900, 0), 2, 5)
    o = d.order("o1")
    assert o.state is State.ASSIGNED
    assert o.courier_id == "c1"
    assert o.restaurant == Point(0, 0)
    with pytest.raises(BadTransition):
        d.assign("o1")


def test_p1_duplicate_pending_order_unchanged():
    d = Dispatcher()
    d.place_order("o9", Point(10, 10), Point(20, 20), 3, 10)
    with pytest.raises(DuplicateOrder):
        d.place_order("o9", Point(50, 50), Point(60, 60), 4, 2)
    o = d.order("o9")
    assert o.placed_at == 3
    assert o.prep_minutes == 10


# ---------------------------------------------------------------- phase 2


def test_p2_hands_out_due_orders():
    d = Dispatcher()
    d.add_courier("north", Point(0, 3000), 2)
    d.add_courier("south", Point(0, 0), 2)
    d.place_order("n1", Point(0, 2900), Point(500, 2900), 0, 5)
    d.place_order("s1", Point(100, 0), Point(500, 0), 0, 8)
    got = d.dispatch_pending(0)
    assert _hidden_assignments(got) == ["n1->north", "s1->south"]
    assert d.order("n1").state is State.ASSIGNED
    assert d.order("s1").courier_id == "south"
    assert len(d.dispatch_pending(1)) == 0


def test_p2_ready_soonest_first():
    d = Dispatcher()
    d.add_courier("solo", Point(0, 0), 1)
    d.place_order("early", Point(0, 0), Point(500, 0), 0, 20)
    d.place_order("late", Point(0, 0), Point(0, 500), 5, 5)
    got = d.dispatch_pending(10)
    assert _hidden_assignments(got) == ["late->solo"]  # food ready first goes first
    assert d.order("early").state is State.PLACED


def test_p2_ready_ties_by_order_id():
    d = Dispatcher()
    d.add_courier("solo", Point(0, 0), 1)
    d.place_order("o-b", Point(0, 0), Point(500, 0), 0, 10)
    d.place_order("o-a", Point(0, 0), Point(0, 500), 5, 5)
    got = d.dispatch_pending(3)
    assert _hidden_assignments(got) == ["o-a->solo"]  # same ready minute, lower id first


def test_p2_dispatch_window():
    d = Dispatcher()
    d.add_courier("c1", Point(0, 0), 5)
    d.place_order("in10", Point(0, 0), Point(100, 0), 0, 10)
    d.place_order("in11", Point(0, 0), Point(200, 0), 0, 11)
    d.place_order("ready", Point(0, 0), Point(300, 0), 0, 0)
    assert _hidden_assignments(d.dispatch_pending(0)) == ["ready->c1", "in10->c1"]
    assert d.order("in11").state is State.PLACED
    assert _hidden_assignments(d.dispatch_pending(1)) == ["in11->c1"]


def test_p2_capacity_spills_to_next_courier():
    d = Dispatcher()
    d.add_courier("near", Point(50, 0), 1)
    d.add_courier("far", Point(900, 0), 2)
    d.add_courier("farther", Point(1500, 0), 4)
    for i in range(1, 5):
        d.place_order(f"o{i}", Point(0, 0), Point(0, 800), i, 0)
    got = d.dispatch_pending(5)
    assert _hidden_assignments(got) == ["o1->near", "o2->far", "o3->far", "o4->farther"]
    assert d.courier_orders("far") == ["o2", "o3"]


def test_p2_unreachable_and_finished_orders():
    d = Dispatcher()
    d.add_courier("away", Point(5000, 0), 3)
    d.place_order("o1", Point(0, 0), Point(100, 0), 0, 0)
    d.place_order("o2", Point(4900, 0), Point(4800, 0), 0, 0)
    d.place_order("o3", Point(4900, 0), Point(4700, 0), 0, 0)
    d.place_order("o4", Point(4900, 0), Point(4600, 0), 0, 0)
    d.assign("o2")
    d.advance("o3", State.CANCELLED)
    assert _hidden_assignments(d.dispatch_pending(1)) == ["o4->away"]  # only o4 is reachable and waiting
    assert d.order("o1").state is State.PLACED
    assert d.order("o3").state is State.CANCELLED
    d.add_courier("home", Point(0, 300), 1)
    assert _hidden_assignments(d.dispatch_pending(2)) == ["o1->home"]
    got = d.dispatch_pending(3)
    assert got == [] and got is not None


# ---------------------------------------------------------------- phase 3


def _hidden_rush(nc):
    """A dinner-rush zone: nc couriers (capacity 10 each) and 10*nc orders spread over a 2 km square,
    placed over the first hours of the shift."""
    d = Dispatcher()
    seed = 12345

    def rnd(n):
        nonlocal seed
        seed = (seed * 1664525 + 1013904223) % 2**32
        return (seed >> 8) % n

    for i in range(nc):
        d.add_courier(f"c{i}", Point(rnd(2000), rnd(2000)), 10)
    for i in range(nc * 10):
        d.place_order(f"o{i}", Point(rnd(2000), rnd(2000)), Point(rnd(2000), rnd(2000)), i // 20, 5 + rnd(11))
    return d


def test_p3_dinner_rush_dispatch():
    d = _hidden_rush(150)
    start = time.perf_counter()
    got = d.dispatch_pending(200)
    elapsed = time.perf_counter() - start
    assert len(got) == 1500
    assert got[0] == Assignment('o3', 'c89')
    assert got[750] == Assignment('o672', 'c23')
    assert got[-1] == Assignment('o1497', 'c135')
    assert elapsed < 0.5, f"dispatch_pending of 1500 orders took {elapsed:.2f}s, budget 0.5s"


def test_p3_dinner_rush_manual_assign():
    d = _hidden_rush(150)
    start = time.perf_counter()
    last = ""
    for i in range(1500):
        last = d.assign(f"o{i}")
    elapsed = time.perf_counter() - start
    assert last == 'c135'
    assert d.courier_orders("c0") == ['o1034', 'o1137', 'o1154', 'o1172', 'o1182', 'o28', 'o614', 'o848', 'o983', 'o984']
    assert elapsed < 0.5, f"1500 assign calls took {elapsed:.2f}s, budget 0.5s"
