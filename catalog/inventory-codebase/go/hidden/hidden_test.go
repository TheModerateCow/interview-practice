package inventory

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

func hiddenEq[T comparable](t *testing.T, what string, got, want T) {
	t.Helper()
	if got != want {
		t.Fatalf("%s: got %v want %v", what, got, want)
	}
}

func hiddenIsErr(t *testing.T, what string, err, want error) {
	t.Helper()
	if !errors.Is(err, want) {
		t.Fatalf("%s: got error %v want %v", what, err, want)
	}
}

func hiddenMust(t *testing.T, err error) {
	t.Helper()
	if err != nil {
		t.Fatal(err)
	}
}

func hiddenService(t *testing.T, warehouses ...string) *Service {
	t.Helper()
	s := New()
	for _, w := range warehouses {
		hiddenMust(t, s.AddWarehouse(w))
	}
	return s
}

func hiddenAvail(t *testing.T, s *Service, w, sku string, now int64) int {
	t.Helper()
	n, err := s.Available(w, sku, now)
	hiddenMust(t, err)
	return n
}

func hiddenReserve(t *testing.T, s *Service, id, w, sku string, qty int, ttl, now int64) {
	t.Helper()
	if _, err := s.Reserve(id, w, sku, qty, ttl, now); err != nil {
		t.Fatalf("reserve %s: %v", id, err)
	}
}

func hiddenStatus(t *testing.T, s *Service, id string) string {
	t.Helper()
	r, ok := s.Reservation(id)
	if !ok {
		t.Fatalf("reservation %s not found", id)
	}
	return fmt.Sprintf("%s@%d", r.Status, r.UpdatedAt)
}

func hiddenPlan(ps []Suggestion) string { return fmt.Sprintf("%+v", ps) }

// ---------------------------------------------------------------- phase 1

func Test_p1_release_after_hold_ran_out_returns_stock_once(t *testing.T) {
	s := hiddenService(t, "east")
	hiddenMust(t, s.Receive("east", "A-01", "LAMP", 10, 100))
	hiddenReserve(t, s, "o1", "east", "LAMP", 6, 600, 200) // runs out at 800
	hiddenEq(t, "available while held", hiddenAvail(t, s, "east", "LAMP", 799), 4)
	hiddenMust(t, s.Release("o1", 900)) // the order service cancels late
	hiddenEq(t, "o1", hiddenStatus(t, s, "o1"), "expired@800")
	hiddenEq(t, "available after late release", hiddenAvail(t, s, "east", "LAMP", 900), 10)
	_, err := s.Reserve("o2", "east", "LAMP", 11, 600, 910)
	hiddenIsErr(t, "oversell", err, ErrInsufficientStock)
	hiddenReserve(t, s, "o3", "east", "LAMP", 10, 600, 920)
	hiddenMust(t, s.Commit("o3", 930))
	hiddenEq(t, "on hand", s.OnHand("east", "LAMP"), 0)
	hiddenEq(t, "available", hiddenAvail(t, s, "east", "LAMP", 940), 0)
}

func Test_p1_late_release_after_hold_ran_out_at_exact_second(t *testing.T) {
	s := hiddenService(t, "east")
	hiddenMust(t, s.Receive("east", "A-01", "LAMP", 5, 0))
	hiddenReserve(t, s, "o1", "east", "LAMP", 3, 60, 10) // runs out at 70
	hiddenReserve(t, s, "o2", "east", "LAMP", 2, 600, 20)
	hiddenMust(t, s.Release("o1", 70))
	hiddenMust(t, s.Release("o1", 71)) // retried
	hiddenEq(t, "o1", hiddenStatus(t, s, "o1"), "expired@70")
	hiddenEq(t, "available", hiddenAvail(t, s, "east", "LAMP", 72), 3)
	_, err := s.Reserve("o3", "east", "LAMP", 4, 60, 80)
	hiddenIsErr(t, "would oversell", err, ErrInsufficientStock)
}

func Test_p1_release_and_commit_lifecycle(t *testing.T) {
	s := hiddenService(t, "east")
	hiddenMust(t, s.Receive("east", "A-01", "KETTLE", 8, 0))
	hiddenReserve(t, s, "o1", "east", "KETTLE", 3, 300, 10)
	hiddenReserve(t, s, "o2", "east", "KETTLE", 4, 300, 20)
	hiddenMust(t, s.Release("o1", 30))
	hiddenMust(t, s.Release("o1", 40)) // retry is a no-op
	hiddenEq(t, "o1", hiddenStatus(t, s, "o1"), "released@30")
	hiddenEq(t, "available after release", hiddenAvail(t, s, "east", "KETTLE", 40), 4)
	hiddenMust(t, s.Commit("o2", 50))
	hiddenEq(t, "o2", hiddenStatus(t, s, "o2"), "committed@50")
	hiddenEq(t, "on hand after commit", s.OnHand("east", "KETTLE"), 4)
	hiddenEq(t, "available after commit", hiddenAvail(t, s, "east", "KETTLE", 60), 4)
	hiddenIsErr(t, "release committed", s.Release("o2", 70), ErrNotActive)
	hiddenIsErr(t, "commit released", s.Commit("o1", 70), ErrNotActive)
	hiddenIsErr(t, "commit twice", s.Commit("o2", 70), ErrNotActive)
	hiddenIsErr(t, "unknown", s.Release("nope", 70), ErrNotFound)
	hiddenReserve(t, s, "o3", "east", "KETTLE", 4, 100, 80)
	hiddenIsErr(t, "commit at expiry", s.Commit("o3", 180), ErrNotActive)
	hiddenEq(t, "o3", hiddenStatus(t, s, "o3"), "expired@180")
	hiddenEq(t, "on hand", s.OnHand("east", "KETTLE"), 4)
}

func Test_p1_pick_finds_bins_put_away_after_an_earlier_pick(t *testing.T) {
	s := hiddenService(t, "east")
	hiddenMust(t, s.Receive("east", "B-02", "TOWEL", 4, 0))
	hiddenReserve(t, s, "o1", "east", "TOWEL", 3, 600, 10)
	hiddenMust(t, s.Commit("o1", 20)) // B-02 now holds 1
	hiddenMust(t, s.Receive("east", "A-09", "TOWEL", 6, 30))
	hiddenMust(t, s.Receive("east", "C-01", "TOWEL", 5, 31))
	hiddenEq(t, "on hand", s.OnHand("east", "TOWEL"), 12)
	hiddenReserve(t, s, "o2", "east", "TOWEL", 9, 600, 40)
	hiddenMust(t, s.Commit("o2", 50))
	hiddenEq(t, "A-09", s.BinQty("east", "A-09", "TOWEL"), 0)
	hiddenEq(t, "B-02", s.BinQty("east", "B-02", "TOWEL"), 0)
	hiddenEq(t, "C-01", s.BinQty("east", "C-01", "TOWEL"), 3)
	hiddenEq(t, "on hand after", s.OnHand("east", "TOWEL"), 3)
}

func Test_p1_transfer_arrival_into_new_bin_is_pickable(t *testing.T) {
	s := hiddenService(t, "east", "west")
	hiddenMust(t, s.Receive("west", "W-1", "RUG", 20, 0))
	hiddenMust(t, s.Receive("east", "E-5", "RUG", 2, 0))
	hiddenReserve(t, s, "o1", "east", "RUG", 2, 600, 10)
	hiddenMust(t, s.Commit("o1", 20))
	_, err := s.StartTransfer("t1", "west", "east", "RUG", 7, 30)
	hiddenMust(t, err)
	hiddenMust(t, s.ReceiveTransfer("t1", "E-1", 40))
	hiddenReserve(t, s, "o2", "east", "RUG", 7, 600, 50)
	hiddenMust(t, s.Commit("o2", 60))
	hiddenEq(t, "E-1", s.BinQty("east", "E-1", "RUG"), 0)
	hiddenEq(t, "east on hand", s.OnHand("east", "RUG"), 0)
}

func Test_p1_pick_order_and_short_pick(t *testing.T) {
	s := hiddenService(t, "east")
	hiddenMust(t, s.Receive("east", "C-03", "CUP", 5, 0))
	hiddenMust(t, s.Receive("east", "A-10", "CUP", 2, 0))
	hiddenMust(t, s.Receive("east", "A-02", "CUP", 3, 0))
	hiddenMust(t, s.Receive("east", "A-02", "BOWL", 9, 0))
	hiddenReserve(t, s, "o1", "east", "CUP", 4, 600, 10)
	hiddenMust(t, s.Commit("o1", 20))
	hiddenEq(t, "A-02 cups", s.BinQty("east", "A-02", "CUP"), 0)
	hiddenEq(t, "A-10 cups", s.BinQty("east", "A-10", "CUP"), 1)
	hiddenEq(t, "C-03 cups", s.BinQty("east", "C-03", "CUP"), 5)
	hiddenEq(t, "A-02 bowls", s.BinQty("east", "A-02", "BOWL"), 9)
	hiddenEq(t, "available", hiddenAvail(t, s, "east", "CUP", 30), 6)
}

func Test_p1_transfer_cannot_take_reserved_stock(t *testing.T) {
	s := hiddenService(t, "east", "west")
	hiddenMust(t, s.Receive("east", "A-01", "CHAIR", 10, 0))
	hiddenReserve(t, s, "o1", "east", "CHAIR", 8, 3600, 10)
	_, err := s.StartTransfer("t1", "east", "west", "CHAIR", 5, 20)
	hiddenIsErr(t, "transfer of held stock", err, ErrInsufficientStock)
	_, ok := s.Transfer("t1")
	hiddenEq(t, "t1 recorded", ok, false)
	hiddenEq(t, "west inbound", s.Inbound("west", "CHAIR"), 0)
	hiddenEq(t, "east on hand", s.OnHand("east", "CHAIR"), 10)
	tr, err := s.StartTransfer("t2", "east", "west", "CHAIR", 2, 30)
	hiddenMust(t, err)
	hiddenEq(t, "t2", fmt.Sprintf("%+v", tr), "{ID:t2 From:east To:west SKU:CHAIR Qty:2 Status:in_transit ShippedAt:30 ReceivedAt:0 Bin:}")
	hiddenEq(t, "east available", hiddenAvail(t, s, "east", "CHAIR", 40), 0)
	hiddenMust(t, s.Commit("o1", 50))
	hiddenEq(t, "east on hand after ship", s.OnHand("east", "CHAIR"), 0)
}

func Test_p1_transfer_lifecycle(t *testing.T) {
	s := hiddenService(t, "east", "west")
	hiddenMust(t, s.Receive("east", "A-01", "DESK", 6, 0))
	_, err := s.StartTransfer("t1", "east", "east", "DESK", 1, 10)
	hiddenIsErr(t, "same warehouse", err, ErrInvalid)
	_, err = s.StartTransfer("t1", "east", "south", "DESK", 1, 10)
	hiddenIsErr(t, "unknown warehouse", err, ErrUnknownWarehouse)
	_, err = s.StartTransfer("t1", "east", "west", "DESK", 7, 10)
	hiddenIsErr(t, "more than on hand", err, ErrInsufficientStock)
	_, err = s.StartTransfer("t1", "east", "west", "DESK", 4, 10)
	hiddenMust(t, err)
	_, err = s.StartTransfer("t1", "east", "west", "DESK", 1, 11)
	hiddenIsErr(t, "duplicate", err, ErrDuplicate)
	hiddenEq(t, "inbound", s.Inbound("west", "DESK"), 4)
	hiddenEq(t, "west on hand in transit", s.OnHand("west", "DESK"), 0)
	hiddenMust(t, s.ReceiveTransfer("t1", "Z-9", 20))
	hiddenIsErr(t, "receive twice", s.ReceiveTransfer("t1", "Z-9", 21), ErrTransferState)
	hiddenEq(t, "inbound after", s.Inbound("west", "DESK"), 0)
	hiddenEq(t, "west bin", s.BinQty("west", "Z-9", "DESK"), 4)
	hiddenEq(t, "east on hand", s.OnHand("east", "DESK"), 2)
	tr, _ := s.Transfer("t1")
	hiddenEq(t, "t1", fmt.Sprintf("%+v", tr), "{ID:t1 From:east To:west SKU:DESK Qty:4 Status:received ShippedAt:10 ReceivedAt:20 Bin:Z-9}")
}

func Test_p1_validation_and_clock(t *testing.T) {
	s := hiddenService(t, "east")
	hiddenIsErr(t, "duplicate warehouse", s.AddWarehouse("east"), ErrDuplicate)
	hiddenIsErr(t, "zero receive", s.Receive("east", "A-01", "PEN", 0, 1), ErrInvalid)
	hiddenIsErr(t, "unknown warehouse", s.Receive("west", "A-01", "PEN", 1, 1), ErrUnknownWarehouse)
	hiddenMust(t, s.Receive("east", "A-01", "PEN", 3, 100))
	hiddenIsErr(t, "backdated receive", s.Receive("east", "A-01", "PEN", 1, 99), ErrBackdated)
	_, err := s.Reserve("o1", "east", "PEN", 1, 0, 100)
	hiddenIsErr(t, "zero ttl", err, ErrInvalid)
	_, err = s.Reserve("o1", "east", "PEN", 4, 60, 100)
	hiddenIsErr(t, "too many", err, ErrInsufficientStock)
	r, err := s.Reserve("o1", "east", "PEN", 3, 60, 100)
	hiddenMust(t, err)
	hiddenEq(t, "o1", fmt.Sprintf("%s %s %d %d..%d %s", r.Warehouse, r.SKU, r.Qty, r.CreatedAt, r.ExpiresAt, r.Status), "east PEN 3 100..160 active")
	_, err = s.Reserve("o1", "east", "PEN", 1, 60, 101)
	hiddenIsErr(t, "duplicate reservation", err, ErrDuplicate)
	hiddenIsErr(t, "backdated release", s.Release("o1", 50), ErrBackdated)
	hiddenEq(t, "available just before expiry", hiddenAvail(t, s, "east", "PEN", 159), 0)
	hiddenEq(t, "available at expiry", hiddenAvail(t, s, "east", "PEN", 160), 3)
	_, err = s.Available("east", "PEN", 10)
	hiddenIsErr(t, "backdated query", err, ErrBackdated)
}

// ---------------------------------------------------------------- phase 2

func Test_p2_reorders_up_to_max_at_or_below_min(t *testing.T) {
	s := hiddenService(t, "east")
	hiddenMust(t, s.Receive("east", "A-01", "SOAP", 10, 0))
	hiddenMust(t, s.Receive("east", "A-02", "SALT", 11, 0))
	hiddenMust(t, s.Receive("east", "A-03", "OIL", 3, 0))
	hiddenMust(t, s.SetRule("east", "SOAP", Rule{Min: 10, Max: 50}))
	hiddenMust(t, s.SetRule("east", "SALT", Rule{Min: 10, Max: 50}))
	hiddenMust(t, s.SetRule("east", "OIL", Rule{Min: 5, Max: 12, Pack: 1}))
	hiddenMust(t, s.SetRule("east", "FLOUR", Rule{Min: 0, Max: 20}))
	plan, err := s.Replenishment("east", 10)
	hiddenMust(t, err)
	hiddenEq(t, "plan", hiddenPlan(plan), "[{SKU:FLOUR Position:0 Qty:20 From:} {SKU:OIL Position:3 Qty:9 From:} {SKU:SOAP Position:10 Qty:40 From:}]")
	hiddenEq(t, "on hand untouched", s.OnHand("east", "SOAP"), 10)
	plan, err = s.Replenishment("east", 20)
	hiddenMust(t, err)
	hiddenEq(t, "plan again", len(plan), 3)
}

func Test_p2_case_packs_round_up(t *testing.T) {
	s := hiddenService(t, "east")
	hiddenMust(t, s.Receive("east", "A-01", "TEA", 7, 0))
	hiddenMust(t, s.Receive("east", "A-01", "JAM", 2, 0))
	hiddenMust(t, s.SetRule("east", "TEA", Rule{Min: 8, Max: 30, Pack: 12}))
	hiddenMust(t, s.SetRule("east", "JAM", Rule{Min: 4, Max: 26, Pack: 6}))
	plan, err := s.Replenishment("east", 10)
	hiddenMust(t, err)
	hiddenEq(t, "plan", hiddenPlan(plan), "[{SKU:JAM Position:2 Qty:24 From:} {SKU:TEA Position:7 Qty:24 From:}]")
}

func Test_p2_active_holds_reduce_position(t *testing.T) {
	s := hiddenService(t, "east")
	hiddenMust(t, s.Receive("east", "A-01", "SOCK", 30, 0))
	hiddenMust(t, s.SetRule("east", "SOCK", Rule{Min: 20, Max: 40, Pack: 5}))
	hiddenReserve(t, s, "o1", "east", "SOCK", 6, 100, 10) // runs out at 110
	hiddenReserve(t, s, "o2", "east", "SOCK", 5, 500, 20)
	hiddenReserve(t, s, "o3", "east", "SOCK", 2, 500, 30)
	hiddenMust(t, s.Release("o3", 40))
	plan, err := s.Replenishment("east", 109)
	hiddenMust(t, err)
	hiddenEq(t, "while o1 held", hiddenPlan(plan), "[{SKU:SOCK Position:19 Qty:25 From:}]")
	plan, err = s.Replenishment("east", 110)
	hiddenMust(t, err)
	hiddenEq(t, "o1 ran out", hiddenPlan(plan), "[]")
	hiddenMust(t, s.Commit("o2", 120))
	plan, _ = s.Replenishment("east", 130)
	hiddenEq(t, "after shipping o2", hiddenPlan(plan), "[]")
	hiddenReserve(t, s, "o4", "east", "SOCK", 6, 500, 140)
	plan, _ = s.Replenishment("east", 150)
	hiddenEq(t, "o4 held", hiddenPlan(plan), "[{SKU:SOCK Position:19 Qty:25 From:}]")
}

func Test_p2_inbound_transfers_count_once(t *testing.T) {
	s := hiddenService(t, "east", "west")
	hiddenMust(t, s.Receive("east", "A-01", "BOOT", 4, 0))
	hiddenMust(t, s.Receive("west", "W-01", "BOOT", 45, 0))
	hiddenMust(t, s.SetRule("east", "BOOT", Rule{Min: 10, Max: 30}))
	hiddenMust(t, s.SetRule("west", "BOOT", Rule{Min: 15, Max: 60}))
	plan, err := s.Replenishment("east", 10)
	hiddenMust(t, err)
	hiddenEq(t, "before transfer", hiddenPlan(plan), "[{SKU:BOOT Position:4 Qty:26 From:west}]")
	_, err = s.StartTransfer("t1", "west", "east", "BOOT", 5, 20)
	hiddenMust(t, err)
	plan, _ = s.Replenishment("east", 30)
	hiddenEq(t, "in transit", hiddenPlan(plan), "[{SKU:BOOT Position:9 Qty:21 From:west}]")
	plan, _ = s.Replenishment("west", 30)
	hiddenEq(t, "west", hiddenPlan(plan), "[]")
	hiddenMust(t, s.ReceiveTransfer("t1", "A-02", 40))
	plan, _ = s.Replenishment("east", 50)
	hiddenEq(t, "received", hiddenPlan(plan), "[{SKU:BOOT Position:9 Qty:21 From:west}]")
	_, err = s.StartTransfer("t2", "west", "east", "BOOT", 2, 60)
	hiddenMust(t, err)
	plan, _ = s.Replenishment("east", 70)
	hiddenEq(t, "second transfer", hiddenPlan(plan), "[]")
}

func Test_p2_source_is_largest_surplus_over_its_min(t *testing.T) {
	s := hiddenService(t, "north", "east", "west", "south")
	hiddenMust(t, s.SetRule("north", "BIKE", Rule{Min: 5, Max: 25}))
	hiddenMust(t, s.Receive("east", "A", "BIKE", 40, 0))
	hiddenMust(t, s.SetRule("east", "BIKE", Rule{Min: 30, Max: 60})) // surplus 10
	hiddenMust(t, s.Receive("west", "A", "BIKE", 30, 0))             // no rule: surplus 30
	hiddenMust(t, s.Receive("south", "A", "BIKE", 34, 0))
	hiddenReserve(t, s, "o1", "south", "BIKE", 4, 1000, 1) // surplus 30
	plan, err := s.Replenishment("north", 10)
	hiddenMust(t, err)
	hiddenEq(t, "tie goes to lowest id", hiddenPlan(plan), "[{SKU:BIKE Position:0 Qty:25 From:south}]")
	hiddenMust(t, s.Release("o1", 20))
	plan, _ = s.Replenishment("north", 30)
	hiddenEq(t, "south grows", hiddenPlan(plan), "[{SKU:BIKE Position:0 Qty:25 From:south}]")
	hiddenReserve(t, s, "o2", "south", "BIKE", 11, 1000, 40)
	hiddenReserve(t, s, "o3", "west", "BIKE", 6, 1000, 40)
	plan, _ = s.Replenishment("north", 50)
	hiddenEq(t, "nobody can spare 25", hiddenPlan(plan), "[{SKU:BIKE Position:0 Qty:25 From:}]")
	hiddenMust(t, s.Receive("north", "N", "BIKE", 3, 60))
	plan, _ = s.Replenishment("north", 70)
	hiddenEq(t, "smaller need", hiddenPlan(plan), "[{SKU:BIKE Position:3 Qty:22 From:west}]")
	hiddenReserve(t, s, "o4", "west", "BIKE", 2, 1000, 80)
	hiddenReserve(t, s, "o5", "south", "BIKE", 2, 1000, 80)
	plan, _ = s.Replenishment("north", 90)
	hiddenEq(t, "exactly enough", hiddenPlan(plan), "[{SKU:BIKE Position:3 Qty:22 From:west}]")
}

func Test_p2_errors_and_empty_plans(t *testing.T) {
	s := hiddenService(t, "east", "west")
	_, err := s.Replenishment("south", 10)
	hiddenIsErr(t, "unknown warehouse", err, ErrUnknownWarehouse)
	plan, err := s.Replenishment("east", 10)
	hiddenMust(t, err)
	hiddenEq(t, "no rules", len(plan), 0)
	hiddenMust(t, s.SetRule("west", "CAP", Rule{Min: 1, Max: 9}))
	plan, _ = s.Replenishment("east", 20)
	hiddenEq(t, "other warehouse's rule", len(plan), 0)
	_, err = s.Replenishment("west", 5)
	hiddenIsErr(t, "backdated", err, ErrBackdated)
	hiddenIsErr(t, "bad rule", s.SetRule("east", "CAP", Rule{Min: 5, Max: 5}), ErrInvalid)
	plan, _ = s.Replenishment("west", 30)
	hiddenEq(t, "west", hiddenPlan(plan), "[{SKU:CAP Position:0 Qty:9 From:}]")
}

// ---------------------------------------------------------------- phase 3

func Test_p3_flash_sale_at_scale(t *testing.T) {
	s := hiddenService(t, "main", "overflow")
	const skus, n = 20, 80000
	sku := func(i int) string { return "SKU-" + strconv.Itoa(i%skus) }
	for i := 0; i < skus; i++ {
		hiddenMust(t, s.Receive("main", "A-"+strconv.Itoa(i), sku(i), 400, 0))
		hiddenMust(t, s.Receive("overflow", "Z-"+strconv.Itoa(i), sku(i), 3000, 0))
		hiddenMust(t, s.SetRule("main", sku(i), Rule{Min: 1200, Max: 2400, Pack: 100}))
	}
	soldOut, committed, notActive, fromOverflow, restocked := 0, 0, 0, 0, 0
	start := time.Now()
	for i := 0; i < n; i++ {
		now := int64(1 + i)
		qty := 1 + i%5
		// The product page checks stock, then checkout holds it: card payments for
		// 15 minutes, bank transfers and pre-orders for up to 12 hours.
		if avail, err := s.Available("main", sku(i), now); err != nil {
			t.Fatal(err)
		} else if avail < qty {
			soldOut++
		} else if _, err := s.Reserve("o"+strconv.Itoa(i), "main", sku(i), qty, int64(900+(i*7919)%42300), now); err != nil {
			t.Fatal(err)
		}
		if i%3 == 0 && i >= 5 {
			if err := s.Commit("o"+strconv.Itoa(i-5), now); err == nil {
				committed++
			} else {
				notActive++
			}
		}
		if i%5 == 0 && i >= 2 {
			if err := s.Release("o"+strconv.Itoa(i-2), now); err != nil && !errors.Is(err, ErrNotFound) {
				t.Fatal(err)
			}
		}
		if i%4000 == 3999 {
			plan, err := s.Replenishment("main", now)
			hiddenMust(t, err)
			for _, sg := range plan {
				if sg.From != "" {
					fromOverflow++
				}
				hiddenMust(t, s.Receive("main", "A-"+sg.SKU[4:], sg.SKU, sg.Qty, now))
				restocked += sg.Qty
			}
		}
	}
	elapsed := time.Since(start)
	total := 0
	for i := 0; i < skus; i++ {
		total += hiddenAvail(t, s, "main", sku(i), n+1)
	}
	hiddenEq(t, "outcome", fmt.Sprintf("soldOut=%d committed=%d notActive=%d fromOverflow=%d restocked=%d available=%d onhand=%d",
		soldOut, committed, notActive, fromOverflow, restocked, total, s.OnHand("main", sku(7))), "soldOut=724 committed=21090 notActive=5575 fromOverflow=72 restocked=120900 available=38943 onhand=4461")
	if elapsed > time.Second {
		t.Fatalf("too slow: %d checkouts took %v (budget 1s)", n, elapsed)
	}
}
