package dispatch

import (
	"errors"
	"fmt"
	"strconv"
	"testing"
	"time"
)

// The app compiles one phase's tests at a time: keep every import used outside them.
var (
	_ = errors.Is
	_ = fmt.Sprint
	_ = strconv.Itoa
	_ = time.Second
)

func hEq[T comparable](t *testing.T, what string, got, want T) {
	t.Helper()
	if got != want {
		t.Fatalf("%s: got %v want %v", what, got, want)
	}
}

func hErr(t *testing.T, what string, got, want error) {
	t.Helper()
	if !errors.Is(got, want) {
		t.Fatalf("%s: got error %v want %v", what, got, want)
	}
}

func hOrder(t *testing.T, d *Dispatcher, id string) Order {
	t.Helper()
	o, err := d.Order(id)
	if err != nil {
		t.Fatalf("Order(%s): %v", id, err)
	}
	return o
}

func hList(xs []string) string { return fmt.Sprint(xs) }

func hAssignments(as []Assignment) string {
	var out []string
	for _, a := range as {
		out = append(out, a.OrderID+"->"+a.CourierID)
	}
	return fmt.Sprint(out)
}

// ---------------------------------------------------------------- phase 1

func Test_p1_assign_nearest_with_room(t *testing.T) {
	d := New()
	d.AddCourier("a", Point{0, 0}, 1)
	d.AddCourier("b", Point{300, 0}, 1)
	for _, id := range []string{"o1", "o2", "o3"} {
		d.PlaceOrder(id, Point{100, 0}, Point{100, 900}, 0, 5)
	}
	c, err := d.Assign("o1")
	hEq(t, "o1 goes to the nearest courier", c, "a")
	hEq(t, "o1 error", err, nil)
	c, _ = d.Assign("o2")
	hEq(t, "o2 skips the full courier", c, "b")
	_, err = d.Assign("o3")
	hErr(t, "o3 with every courier full", err, ErrNoCourier)
	hEq(t, "o3 still placed", hOrder(t, d, "o3").State, Placed)
	_, err = d.Assign("o1")
	hErr(t, "assigning an assigned order", err, ErrBadTransition)
	hEq(t, "o1 state", hOrder(t, d, "o1").State, Assigned)
	hEq(t, "o1 courier", hOrder(t, d, "o1").CourierID, "a")
}

func Test_p1_assign_ties_and_range(t *testing.T) {
	d := New()
	d.AddCourier("zed", Point{0, 200}, 1)
	d.AddCourier("amy", Point{200, 0}, 1)
	d.AddCourier("edge", Point{4000, 0}, 1)
	d.AddCourier("gone", Point{0, 4001}, 1)
	for _, id := range []string{"o1", "o2", "o3", "o4"} {
		d.PlaceOrder(id, Point{0, 0}, Point{500, 500}, 0, 0)
	}
	c, _ := d.Assign("o1")
	hEq(t, "tie goes to the lower id", c, "amy")
	c, _ = d.Assign("o2")
	hEq(t, "then the other tied courier", c, "zed")
	c, _ = d.Assign("o3")
	hEq(t, "exactly MaxPickupDistance away is in range", c, "edge")
	_, err := d.Assign("o4")
	hErr(t, "only an out-of-range courier left", err, ErrNoCourier)
}

func Test_p1_lifecycle_rules(t *testing.T) {
	d := New()
	d.AddCourier("c1", Point{0, 0}, 1)
	d.PlaceOrder("o1", Point{0, 0}, Point{250, 0}, 0, 0)
	hErr(t, "deliver before pickup", d.Advance("o1", Delivered), ErrBadTransition)
	hErr(t, "assign through Advance", d.Advance("o1", Assigned), ErrBadTransition)
	d.Assign("o1")
	hErr(t, "deliver before pickup", d.Advance("o1", Delivered), ErrBadTransition)
	hEq(t, "pickup", d.Advance("o1", PickedUp), nil)
	hErr(t, "cancel after pickup", d.Advance("o1", Cancelled), ErrBadTransition)
	hEq(t, "deliver", d.Advance("o1", Delivered), nil)
	hErr(t, "deliver twice", d.Advance("o1", Delivered), ErrBadTransition)
	hErr(t, "unknown order", d.Advance("nope", PickedUp), ErrUnknownOrder)
	hErr(t, "AddCourier capacity 0", d.AddCourier("c2", Point{0, 0}, 0), ErrInvalidCourier)
	hErr(t, "AddCourier duplicate", d.AddCourier("c1", Point{0, 0}, 3), ErrDuplicateCourier)
}

func Test_p1_delivery_frees_courier_and_moves_them(t *testing.T) {
	d := New()
	d.AddCourier("c1", Point{0, 0}, 1)
	d.AddCourier("c2", Point{1000, 0}, 1)
	d.PlaceOrder("o1", Point{0, 0}, Point{2000, 0}, 0, 0)
	d.Assign("o1")
	d.Advance("o1", PickedUp)
	d.Advance("o1", Delivered)
	d.PlaceOrder("o2", Point{2000, 100}, Point{0, 0}, 5, 5)
	c, _ := d.Assign("o2")
	hEq(t, "courier is free again, now at the last customer", c, "c1")
	ids, _ := d.CourierOrders("c1")
	hEq(t, "c1 bag", hList(ids), "[o2]")
}

func Test_p1_eta_rounds_each_leg_up(t *testing.T) {
	d := New()
	d.AddCourier("c1", Point{0, 0}, 2)
	d.PlaceOrder("o1", Point{600, 0}, Point{600, 1100}, 0, 0)
	d.Assign("o1")
	m, err := d.ETA("o1", 0)
	hEq(t, "ETA error", err, nil)
	hEq(t, "ETA 600 m + 1100 m", m, 8)
	hEq(t, "TravelMinutes(1)", TravelMinutes(1), 1)
	hEq(t, "TravelMinutes(500)", TravelMinutes(500), 2)
	hEq(t, "TravelMinutes(501)", TravelMinutes(501), 3)
	hEq(t, "TravelMinutes(0)", TravelMinutes(0), 0)
}

func Test_p1_eta_waits_for_kitchen(t *testing.T) {
	d := New()
	d.AddCourier("c1", Point{0, 0}, 2)
	d.PlaceOrder("o2", Point{0, 700}, Point{700, 700}, 5, 15)
	d.Assign("o2")
	m, _ := d.ETA("o2", 5)
	hEq(t, "ETA when food is ready after the courier arrives", m, 18)
}

func Test_p1_eta_after_pickup(t *testing.T) {
	d := New()
	d.AddCourier("c1", Point{0, 0}, 2)
	d.PlaceOrder("o1", Point{600, 0}, Point{600, 1100}, 0, 0)
	d.Assign("o1")
	d.Advance("o1", PickedUp)
	m, _ := d.ETA("o1", 9)
	hEq(t, "ETA from the restaurant to the door", m, 5)
	d.Advance("o1", Delivered)
	_, err := d.ETA("o1", 12)
	hErr(t, "ETA delivered", err, ErrOrderClosed)
	d.PlaceOrder("o3", Point{0, 0}, Point{0, 10}, 12, 0)
	_, err = d.ETA("o3", 12)
	hErr(t, "ETA unassigned", err, ErrNotAssigned)
}

func Test_p1_cancel_frees_courier(t *testing.T) {
	d := New()
	d.AddCourier("solo", Point{0, 0}, 1)
	d.PlaceOrder("o1", Point{100, 100}, Point{900, 900}, 0, 5)
	d.PlaceOrder("o2", Point{100, 100}, Point{800, 800}, 1, 5)
	d.Assign("o1")
	hEq(t, "cancel assigned order", d.Advance("o1", Cancelled), nil)
	c, err := d.Assign("o2")
	hEq(t, "assign after cancel error", err, nil)
	hEq(t, "assign after cancel", c, "solo")
}

func Test_p1_cancelled_order_leaves_bag(t *testing.T) {
	d := New()
	d.AddCourier("c1", Point{0, 0}, 3)
	d.PlaceOrder("o1", Point{0, 0}, Point{900, 0}, 0, 5)
	d.PlaceOrder("o2", Point{0, 0}, Point{0, 900}, 0, 5)
	d.Assign("o1")
	d.Assign("o2")
	d.Advance("o1", Cancelled)
	ids, _ := d.CourierOrders("c1")
	hEq(t, "bag after cancelling o1", hList(ids), "[o2]")
}

func Test_p1_duplicate_order_keeps_assignment(t *testing.T) {
	d := New()
	d.AddCourier("c1", Point{0, 0}, 1)
	d.AddCourier("c2", Point{3000, 0}, 1)
	d.PlaceOrder("o1", Point{0, 0}, Point{900, 0}, 0, 5)
	d.Assign("o1")
	hErr(t, "retried checkout", d.PlaceOrder("o1", Point{3000, 0}, Point{900, 0}, 2, 5), ErrDuplicateOrder)
	o := hOrder(t, d, "o1")
	hEq(t, "state after retry", o.State, Assigned)
	hEq(t, "courier after retry", o.CourierID, "c1")
	hEq(t, "restaurant after retry", o.Restaurant, Point{0, 0})
	_, err := d.Assign("o1")
	hErr(t, "re-assign after retry", err, ErrBadTransition)
}

func Test_p1_duplicate_pending_order_unchanged(t *testing.T) {
	d := New()
	d.PlaceOrder("o9", Point{10, 10}, Point{20, 20}, 3, 10)
	hErr(t, "duplicate id", d.PlaceOrder("o9", Point{50, 50}, Point{60, 60}, 4, 2), ErrDuplicateOrder)
	o := hOrder(t, d, "o9")
	hEq(t, "placed at", o.PlacedAt, 3)
	hEq(t, "prep", o.PrepMinutes, 10)
}

// ---------------------------------------------------------------- phase 2

func Test_p2_hands_out_due_orders(t *testing.T) {
	d := New()
	d.AddCourier("north", Point{0, 3000}, 2)
	d.AddCourier("south", Point{0, 0}, 2)
	d.PlaceOrder("n1", Point{0, 2900}, Point{500, 2900}, 0, 5)
	d.PlaceOrder("s1", Point{100, 0}, Point{500, 0}, 0, 8)
	got := d.DispatchPending(0)
	hEq(t, "assignments", hAssignments(got), "[n1->north s1->south]")
	hEq(t, "n1 state", hOrder(t, d, "n1").State, Assigned)
	hEq(t, "s1 courier", hOrder(t, d, "s1").CourierID, "south")
	hEq(t, "nothing left", len(d.DispatchPending(1)), 0)
}

func Test_p2_ready_soonest_first(t *testing.T) {
	d := New()
	d.AddCourier("solo", Point{0, 0}, 1)
	d.PlaceOrder("early", Point{0, 0}, Point{500, 0}, 0, 20)
	d.PlaceOrder("late", Point{0, 0}, Point{0, 500}, 5, 5)
	got := d.DispatchPending(10)
	hEq(t, "food ready first goes first", hAssignments(got), "[late->solo]")
	hEq(t, "the other waits", hOrder(t, d, "early").State, Placed)
}

func Test_p2_ready_ties_by_order_id(t *testing.T) {
	d := New()
	d.AddCourier("solo", Point{0, 0}, 1)
	d.PlaceOrder("o-b", Point{0, 0}, Point{500, 0}, 0, 10)
	d.PlaceOrder("o-a", Point{0, 0}, Point{0, 500}, 5, 5)
	got := d.DispatchPending(3)
	hEq(t, "same ready minute, lower id first", hAssignments(got), "[o-a->solo]")
}

func Test_p2_dispatch_window(t *testing.T) {
	d := New()
	d.AddCourier("c1", Point{0, 0}, 5)
	d.PlaceOrder("in10", Point{0, 0}, Point{100, 0}, 0, 10)
	d.PlaceOrder("in11", Point{0, 0}, Point{200, 0}, 0, 11)
	d.PlaceOrder("ready", Point{0, 0}, Point{300, 0}, 0, 0)
	hEq(t, "minute 0", hAssignments(d.DispatchPending(0)), "[ready->c1 in10->c1]")
	hEq(t, "in11 waits", hOrder(t, d, "in11").State, Placed)
	hEq(t, "minute 1", hAssignments(d.DispatchPending(1)), "[in11->c1]")
}

func Test_p2_capacity_spills_to_next_courier(t *testing.T) {
	d := New()
	d.AddCourier("near", Point{50, 0}, 1)
	d.AddCourier("far", Point{900, 0}, 2)
	d.AddCourier("farther", Point{1500, 0}, 4)
	for i := 1; i <= 4; i++ {
		d.PlaceOrder("o"+strconv.Itoa(i), Point{0, 0}, Point{0, 800}, i, 0)
	}
	got := d.DispatchPending(5)
	hEq(t, "assignments", hAssignments(got), "[o1->near o2->far o3->far o4->farther]")
	ids, _ := d.CourierOrders("far")
	hEq(t, "far bag", hList(ids), "[o2 o3]")
}

func Test_p2_unreachable_and_finished_orders(t *testing.T) {
	d := New()
	d.AddCourier("away", Point{5000, 0}, 3)
	d.PlaceOrder("o1", Point{0, 0}, Point{100, 0}, 0, 0)
	d.PlaceOrder("o2", Point{4900, 0}, Point{4800, 0}, 0, 0)
	d.PlaceOrder("o3", Point{4900, 0}, Point{4700, 0}, 0, 0)
	d.PlaceOrder("o4", Point{4900, 0}, Point{4600, 0}, 0, 0)
	d.Assign("o2")
	d.Advance("o3", Cancelled)
	hEq(t, "only o4 is reachable and waiting", hAssignments(d.DispatchPending(1)), "[o4->away]")
	hEq(t, "o1 waits", hOrder(t, d, "o1").State, Placed)
	hEq(t, "o3 stays cancelled", hOrder(t, d, "o3").State, Cancelled)
	d.AddCourier("home", Point{0, 300}, 1)
	hEq(t, "new courier picks up o1", hAssignments(d.DispatchPending(2)), "[o1->home]")
	got := d.DispatchPending(3)
	if got == nil || len(got) != 0 {
		t.Fatalf("nothing to do: got %#v want an empty slice", got)
	}
}

// ---------------------------------------------------------------- phase 3

// hRush builds a dinner-rush zone: nc couriers (capacity 10 each) and 10*nc
// orders spread over a 2 km square, placed over the first hours of the shift.
func hRush(nc int) *Dispatcher {
	d := New()
	seed := uint32(12345)
	rnd := func(n int) int { seed = seed*1664525 + 1013904223; return int(seed>>8) % n }
	for i := 0; i < nc; i++ {
		d.AddCourier("c"+strconv.Itoa(i), Point{rnd(2000), rnd(2000)}, 10)
	}
	for i := 0; i < nc*10; i++ {
		d.PlaceOrder("o"+strconv.Itoa(i), Point{rnd(2000), rnd(2000)}, Point{rnd(2000), rnd(2000)}, i/20, 5+rnd(11))
	}
	return d
}

func Test_p3_dinner_rush_dispatch(t *testing.T) {
	d := hRush(200)
	start := time.Now()
	got := d.DispatchPending(200)
	elapsed := time.Since(start)
	hEq(t, "assignments", len(got), 2000)
	hEq(t, "first", got[0], Assignment{"o3", "c151"})
	hEq(t, "middle", got[999], Assignment{"o1060", "c19"})
	hEq(t, "last", got[1999], Assignment{"o1996", "c28"})
	if elapsed > 500*time.Millisecond {
		t.Fatalf("DispatchPending of 2000 orders took %v, budget 500ms", elapsed)
	}
}

func Test_p3_dinner_rush_manual_assign(t *testing.T) {
	d := hRush(150)
	start := time.Now()
	var last string
	for i := 0; i < 1500; i++ {
		c, err := d.Assign("o" + strconv.Itoa(i))
		if err != nil {
			t.Fatalf("Assign(o%d): %v", i, err)
		}
		last = c
	}
	elapsed := time.Since(start)
	hEq(t, "last courier", last, "c135")
	ids, _ := d.CourierOrders("c0")
	hEq(t, "c0 bag", hList(ids), "[o1034 o1137 o1154 o1172 o1182 o28 o614 o848 o983 o984]")
	if elapsed > 500*time.Millisecond {
		t.Fatalf("1500 Assign calls took %v, budget 500ms", elapsed)
	}
}
