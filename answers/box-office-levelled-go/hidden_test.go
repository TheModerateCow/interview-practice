package tickets

import (
	"strconv"
	"testing"
)

func hiddenItoa(n int) string { return strconv.Itoa(n) }

func hiddenSame(t *testing.T, what string, got, want []string) {
	t.Helper()
	if len(got) != len(want) {
		t.Fatalf("%s: got %v want %v", what, got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("%s: got %v want %v", what, got, want)
		}
	}
}

func hiddenEq[T comparable](t *testing.T, what string, got, want T) {
	t.Helper()
	if got != want {
		t.Fatalf("%s: got %v want %v", what, got, want)
	}
}

// ---------------------------------------------------------------- level 1

func Test_l1_create_rules(t *testing.T) {
	o := NewOffice()
	hiddenEq(t, "create gig", o.CreateEvent(1, "gig", 10), true)
	hiddenEq(t, "duplicate id", o.CreateEvent(2, "gig", 50), false)
	hiddenEq(t, "capacity 0", o.CreateEvent(3, "zero", 0), false)
	hiddenEq(t, "negative capacity", o.CreateEvent(4, "neg", -5), false)
	hiddenEq(t, "available new event", o.Available(5, "gig"), 10)
	hiddenEq(t, "available unknown", o.Available(6, "zero"), -1)
}

func Test_l1_buy_reduces_available(t *testing.T) {
	o := NewOffice()
	o.CreateEvent(1, "gig", 10)
	hiddenEq(t, "buy 4", o.Buy(2, "gig", "ana", 4), true)
	hiddenEq(t, "available after 4", o.Available(3, "gig"), 6)
	hiddenEq(t, "buy the rest", o.Buy(4, "gig", "bo", 6), true)
	hiddenEq(t, "sold out", o.Available(5, "gig"), 0)
	hiddenEq(t, "buy when sold out", o.Buy(6, "gig", "cy", 1), false)
}

func Test_l1_buy_rejects(t *testing.T) {
	o := NewOffice()
	o.CreateEvent(1, "gig", 5)
	hiddenEq(t, "unknown event", o.Buy(2, "other", "ana", 1), false)
	hiddenEq(t, "qty 0", o.Buy(3, "gig", "ana", 0), false)
	hiddenEq(t, "negative qty", o.Buy(4, "gig", "ana", -2), false)
	hiddenEq(t, "more than available", o.Buy(5, "gig", "ana", 6), false)
	hiddenEq(t, "nothing changed", o.Available(6, "gig"), 5)
	hiddenEq(t, "exactly available", o.Buy(7, "gig", "ana", 5), true)
}

func Test_l1_refund(t *testing.T) {
	o := NewOffice()
	o.CreateEvent(1, "gig", 10)
	o.Buy(2, "gig", "ana", 5)
	hiddenEq(t, "refund 2", o.Refund(3, "gig", "ana", 2), true)
	hiddenEq(t, "available after refund", o.Available(4, "gig"), 7)
	hiddenEq(t, "refund more than owned", o.Refund(5, "gig", "ana", 4), false)
	hiddenEq(t, "refund by a non-owner", o.Refund(6, "gig", "bo", 1), false)
	hiddenEq(t, "refund qty 0", o.Refund(7, "gig", "ana", 0), false)
	hiddenEq(t, "refund unknown event", o.Refund(8, "nope", "ana", 1), false)
	hiddenEq(t, "refund all that is left", o.Refund(9, "gig", "ana", 3), true)
	hiddenEq(t, "back to capacity", o.Available(10, "gig"), 10)
}

func Test_l1_events_independent(t *testing.T) {
	o := NewOffice()
	o.CreateEvent(1, "a", 4)
	o.CreateEvent(2, "b", 4)
	o.Buy(3, "a", "ana", 3)
	hiddenEq(t, "other event untouched", o.Available(4, "b"), 4)
	hiddenEq(t, "tickets belong to one event", o.Refund(5, "b", "ana", 1), false)
	hiddenEq(t, "buy in b", o.Buy(6, "b", "ana", 4), true)
	hiddenEq(t, "a unchanged", o.Available(7, "a"), 1)
}

// ---------------------------------------------------------------- level 2

func Test_l2_top_buyers_order(t *testing.T) {
	o := NewOffice()
	o.CreateEvent(1, "gig", 20)
	o.Buy(2, "gig", "cy", 2)
	o.Buy(3, "gig", "bo", 5)
	o.Buy(4, "gig", "ana", 2)
	o.Buy(5, "gig", "dee", 1)
	hiddenSame(t, "top 3", o.TopBuyers(6, "gig", 3), []string{"bo(5)", "ana(2)", "cy(2)"})
	hiddenSame(t, "n bigger than buyers", o.TopBuyers(7, "gig", 10), []string{"bo(5)", "ana(2)", "cy(2)", "dee(1)"})
	hiddenSame(t, "n 0", o.TopBuyers(8, "gig", 0), []string{})
}

func Test_l2_top_buyers_after_refunds(t *testing.T) {
	o := NewOffice()
	o.CreateEvent(1, "gig", 20)
	o.Buy(2, "gig", "ana", 4)
	o.Buy(3, "gig", "bo", 3)
	o.Buy(4, "gig", "cy", 1)
	o.Refund(5, "gig", "ana", 2)
	o.Refund(6, "gig", "cy", 1)
	o.Buy(7, "gig", "ana", 1)
	hiddenSame(t, "refunds reorder, zero drops out", o.TopBuyers(8, "gig", 5), []string{"ana(3)", "bo(3)"})
}

func Test_l2_top_buyers_unknown_or_empty(t *testing.T) {
	o := NewOffice()
	hiddenSame(t, "unknown event", o.TopBuyers(1, "gig", 3), []string{})
	o.CreateEvent(2, "gig", 5)
	hiddenSame(t, "no buyers yet", o.TopBuyers(3, "gig", 3), []string{})
}

func Test_l2_busiest_events(t *testing.T) {
	o := NewOffice()
	for i, id := range []string{"d", "c", "b", "a"} {
		o.CreateEvent(i+1, id, 10)
	}
	o.Buy(5, "a", "ana", 3)
	o.Buy(6, "b", "bo", 7)
	o.Buy(7, "d", "cy", 2)
	o.Buy(8, "d", "dee", 1)
	hiddenSame(t, "all events", o.BusiestEvents(9, 10), []string{"b(7)", "a(3)", "d(3)", "c(0)"})
	hiddenSame(t, "top 2", o.BusiestEvents(10, 2), []string{"b(7)", "a(3)"})
}

func Test_l2_busiest_after_refund(t *testing.T) {
	o := NewOffice()
	hiddenSame(t, "no events", o.BusiestEvents(1, 3), []string{})
	o.CreateEvent(2, "a", 10)
	o.CreateEvent(3, "b", 10)
	o.Buy(4, "a", "ana", 5)
	o.Buy(5, "b", "bo", 4)
	o.Refund(6, "a", "ana", 2)
	hiddenSame(t, "refund lowers sold", o.BusiestEvents(7, 5), []string{"b(4)", "a(3)"})
}

// ---------------------------------------------------------------- level 3

func Test_l3_hold_reduces_available(t *testing.T) {
	o := NewOffice()
	o.CreateEvent(1, "gig", 10)
	hiddenEq(t, "first hold id", o.Hold(10, "gig", "ana", 4, 5), "h1")
	hiddenEq(t, "held seats are not available", o.Available(11, "gig"), 6)
	hiddenEq(t, "still held just before expiry", o.Available(14, "gig"), 6)
	hiddenEq(t, "released at expiry", o.Available(15, "gig"), 10)
}

func Test_l3_hold_blocks_buy(t *testing.T) {
	o := NewOffice()
	o.CreateEvent(1, "gig", 5)
	o.Hold(2, "gig", "ana", 4, 10)
	hiddenEq(t, "buy more than unheld", o.Buy(3, "gig", "bo", 2), false)
	hiddenEq(t, "buy the unheld seat", o.Buy(4, "gig", "bo", 1), true)
	hiddenEq(t, "hold more than available", o.Hold(5, "gig", "cy", 1, 10), "")
	hiddenEq(t, "buy after the hold expired", o.Buy(12, "gig", "cy", 4), true)
}

func Test_l3_confirm(t *testing.T) {
	o := NewOffice()
	o.CreateEvent(1, "gig", 10)
	id := o.Hold(2, "gig", "ana", 3, 10)
	hiddenEq(t, "confirm live hold", o.Confirm(5, id), true)
	hiddenEq(t, "confirmed seats stay taken after the ttl", o.Available(30, "gig"), 7)
	hiddenSame(t, "confirmed tickets are owned", o.TopBuyers(31, "gig", 5), []string{"ana(3)"})
	hiddenSame(t, "and sold", o.BusiestEvents(32, 5), []string{"gig(3)"})
	hiddenEq(t, "confirm twice", o.Confirm(33, id), false)
	hiddenEq(t, "refund confirmed tickets", o.Refund(34, "gig", "ana", 3), true)
	hiddenEq(t, "all back", o.Available(35, "gig"), 10)
}

func Test_l3_confirm_expired_or_unknown(t *testing.T) {
	o := NewOffice()
	o.CreateEvent(1, "gig", 10)
	id := o.Hold(2, "gig", "ana", 3, 5)
	hiddenEq(t, "confirm at the expiry time", o.Confirm(7, id), false)
	hiddenEq(t, "unknown hold", o.Confirm(8, "h9"), false)
	hiddenSame(t, "nothing owned", o.TopBuyers(9, "gig", 5), []string{})
	hiddenEq(t, "seats back", o.Available(10, "gig"), 10)
}

func Test_l3_hold_rules_and_ids(t *testing.T) {
	o := NewOffice()
	o.CreateEvent(1, "a", 5)
	o.CreateEvent(2, "b", 5)
	hiddenEq(t, "unknown event", o.Hold(3, "zz", "ana", 1, 5), "")
	hiddenEq(t, "qty 0", o.Hold(4, "a", "ana", 0, 5), "")
	hiddenEq(t, "ttl 0", o.Hold(5, "a", "ana", 1, 0), "")
	hiddenEq(t, "too many", o.Hold(6, "a", "ana", 6, 5), "")
	hiddenEq(t, "failures use no id", o.Hold(7, "a", "ana", 2, 5), "h1")
	hiddenEq(t, "ids count across events", o.Hold(8, "b", "bo", 2, 5), "h2")
	hiddenEq(t, "held seats are not sold", o.BusiestEvents(9, 5)[0], "a(0)")
}

// ---------------------------------------------------------------- level 4

func Test_l4_owned_at(t *testing.T) {
	o := NewOffice()
	o.CreateEvent(1, "gig", 20)
	o.Buy(5, "gig", "ana", 3)
	o.Buy(8, "gig", "ana", 2)
	o.Refund(12, "gig", "ana", 1)
	for _, c := range []struct{ at, want int }{{4, 0}, {5, 3}, {7, 3}, {8, 5}, {11, 5}, {12, 4}, {100, 4}} {
		hiddenEq(t, "owned at "+hiddenItoa(c.at), o.OwnedAt(20, "gig", "ana", c.at), c.want)
	}
}

func Test_l4_owned_at_edges(t *testing.T) {
	o := NewOffice()
	hiddenEq(t, "unknown event", o.OwnedAt(1, "gig", "ana", 1), -1)
	o.CreateEvent(10, "gig", 20)
	o.Buy(11, "gig", "ana", 2)
	hiddenEq(t, "before the event existed", o.OwnedAt(12, "gig", "ana", 3), 0)
	hiddenEq(t, "another buyer", o.OwnedAt(13, "gig", "bo", 11), 0)
	hiddenEq(t, "unknown event, other id", o.OwnedAt(14, "nope", "ana", 11), -1)
}

func Test_l4_sold_at(t *testing.T) {
	o := NewOffice()
	o.CreateEvent(1, "gig", 20)
	o.CreateEvent(2, "other", 20)
	o.Buy(3, "gig", "ana", 4)
	o.Buy(4, "other", "ana", 9)
	o.Buy(6, "gig", "bo", 5)
	o.Refund(9, "gig", "ana", 4)
	for _, c := range []struct{ at, want int }{{2, 0}, {3, 4}, {5, 4}, {6, 9}, {8, 9}, {9, 5}} {
		hiddenEq(t, "sold at "+hiddenItoa(c.at), o.SoldAt(10, "gig", c.at), c.want)
	}
	hiddenEq(t, "unknown event", o.SoldAt(11, "nope", 5), -1)
}

func Test_l4_confirm_counts_from_confirm_time(t *testing.T) {
	o := NewOffice()
	o.CreateEvent(1, "gig", 10)
	id := o.Hold(10, "gig", "ana", 3, 20)
	o.Confirm(15, id)
	hiddenEq(t, "held, not owned", o.OwnedAt(16, "gig", "ana", 12), 0)
	hiddenEq(t, "owned from the confirm", o.OwnedAt(17, "gig", "ana", 15), 3)
	hiddenEq(t, "not sold before the confirm", o.SoldAt(18, "gig", 14), 0)
	hiddenEq(t, "sold after", o.SoldAt(19, "gig", 40), 3)
}

func Test_l4_expired_hold_never_owned(t *testing.T) {
	o := NewOffice()
	o.CreateEvent(1, "gig", 10)
	o.Hold(2, "gig", "ana", 3, 5)
	o.Buy(3, "gig", "bo", 2)
	hiddenEq(t, "never owned", o.OwnedAt(20, "gig", "ana", 4), 0)
	hiddenEq(t, "only bo's sold", o.SoldAt(21, "gig", 4), 2)
	hiddenEq(t, "still only bo's", o.SoldAt(22, "gig", 30), 2)
}
