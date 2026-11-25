package billing

import (
	"errors"
	"testing"
)

func hiddenEq[T comparable](t *testing.T, what string, got, want T) {
	t.Helper()
	if got != want {
		t.Fatalf("%s: got %v want %v", what, got, want)
	}
}

func hiddenNew(t *testing.T, day int, plan, cycle string, seats int) *Subscription {
	t.Helper()
	s, err := New(day, plan, cycle, seats)
	if err != nil || s == nil {
		t.Fatalf("New(%d, %q, %q, %d): unexpected error %v", day, plan, cycle, seats, err)
	}
	return s
}

func hiddenChange(t *testing.T, s *Subscription, day int, plan string, seats, want int) {
	t.Helper()
	got, err := s.Change(day, plan, seats)
	if err != nil {
		t.Fatalf("Change(%d, %q, %d): unexpected error %v", day, plan, seats, err)
	}
	if got != want {
		t.Fatalf("Change(%d, %q, %d): charged %d want %d", day, plan, seats, got, want)
	}
}

func hiddenChangeErr(t *testing.T, s *Subscription, day int, plan string, seats int, want error) {
	t.Helper()
	got, err := s.Change(day, plan, seats)
	if !errors.Is(err, want) {
		t.Fatalf("Change(%d, %q, %d): got error %v want %v", day, plan, seats, err, want)
	}
	if got != 0 {
		t.Fatalf("Change(%d, %q, %d): charged %d on error, want 0", day, plan, seats, got)
	}
}

func Test_p1_new_subscription(t *testing.T) {
	s := hiddenNew(t, 5, "team", "monthly", 3)
	hiddenEq(t, "price", s.PeriodPrice(), 7497)
	hiddenEq(t, "end", s.PeriodEnd(), 35)
	hiddenEq(t, "credit", s.Credit(), 0)
	a := hiddenNew(t, 0, "business", "annual", 2)
	hiddenEq(t, "annual price", a.PeriodPrice(), 119980)
	hiddenEq(t, "annual end", a.PeriodEnd(), 360)
	b := hiddenNew(t, 0, "starter", "annual", 1)
	hiddenEq(t, "starter annual price", b.PeriodPrice(), 12990)
}

func Test_p1_new_rejects_bad_input(t *testing.T) {
	cases := []struct {
		plan, cycle string
		seats       int
		want        error
	}{
		{"team", "weekly", 1, ErrUnknownCycle},
		{"pro", "monthly", 1, ErrUnknownPlan},
		{"Team", "monthly", 1, ErrUnknownPlan},
		{"pro", "weekly", 0, ErrUnknownCycle},
		{"team", "monthly", 0, ErrInvalidSeats},
		{"team", "monthly", -1, ErrInvalidSeats},
		{"team", "monthly", 501, ErrInvalidSeats},
		{"pro", "annual", 0, ErrUnknownPlan},
	}
	for _, c := range cases {
		s, err := New(0, c.plan, c.cycle, c.seats)
		if !errors.Is(err, c.want) || s != nil {
			t.Fatalf("New(0, %q, %q, %d): got %v, %v want nil, %v", c.plan, c.cycle, c.seats, s, err, c.want)
		}
	}
}

func Test_p1_seat_limits_accepted(t *testing.T) {
	hiddenEq(t, "1 seat", hiddenNew(t, 0, "team", "monthly", 1).PeriodPrice(), 2499)
	hiddenEq(t, "500 seats", hiddenNew(t, 0, "team", "monthly", 500).PeriodPrice(), 1249500)
}

func Test_p1_renew_charges_full_period(t *testing.T) {
	s := hiddenNew(t, 0, "starter", "monthly", 4)
	hiddenEq(t, "renew 1", s.Renew(), 5196)
	hiddenEq(t, "end after renew 1", s.PeriodEnd(), 60)
	hiddenEq(t, "renew 2", s.Renew(), 5196)
	hiddenEq(t, "end after renew 2", s.PeriodEnd(), 90)
	a := hiddenNew(t, 7, "team", "annual", 1)
	hiddenEq(t, "annual renew", a.Renew(), 24990)
	hiddenEq(t, "annual end", a.PeriodEnd(), 727)
}

func Test_p1_upgrade_prorated_and_rounded_half_up(t *testing.T) {
	s := hiddenNew(t, 0, "team", "monthly", 1)
	hiddenChange(t, s, 25, "team", 2, 417) // 2499 * 5/30 = 416.5
	hiddenChange(t, s, 26, "team", 3, 333) // 2499 * 4/30 = 333.2
	hiddenEq(t, "price", s.PeriodPrice(), 7497)
	u := hiddenNew(t, 0, "starter", "monthly", 1)
	hiddenChange(t, u, 20, "team", 1, 400) // 1200 * 10/30
	hiddenChange(t, u, 29, "team", 2, 83)  // 2499 * 1/30 = 83.3
	hiddenEq(t, "credit", u.Credit(), 0)
}

func Test_p1_change_on_first_day_is_full_difference(t *testing.T) {
	s := hiddenNew(t, 0, "team", "monthly", 1)
	hiddenChange(t, s, 0, "business", 1, 3500)
	hiddenEq(t, "price", s.PeriodPrice(), 5999)
}

func Test_p1_downgrade_credit_rounded_down(t *testing.T) {
	s := hiddenNew(t, 0, "team", "monthly", 2)
	hiddenChange(t, s, 25, "team", 1, 0) // 2499 * 5/30 = 416.5
	hiddenEq(t, "credit", s.Credit(), 416)
	hiddenEq(t, "price", s.PeriodPrice(), 2499)
	d := hiddenNew(t, 0, "business", "monthly", 1)
	hiddenChange(t, d, 10, "starter", 1, 0) // 4700 * 20/30 = 3133.3
	hiddenEq(t, "credit", d.Credit(), 3133)
	e := hiddenNew(t, 0, "team", "monthly", 3)
	hiddenChange(t, e, 4, "starter", 2, 0) // 4899 * 26/30 = 4245.8
	hiddenEq(t, "credit", e.Credit(), 4245)
}

func Test_p1_same_price_change_is_free(t *testing.T) {
	s := hiddenNew(t, 0, "team", "monthly", 2)
	hiddenChange(t, s, 5, "team", 2, 0)
	hiddenEq(t, "credit", s.Credit(), 0)
	hiddenChange(t, s, 5, "team", 1, 0)
	hiddenChange(t, s, 6, "team", 1, 0)
	hiddenEq(t, "credit", s.Credit(), 2082)
}

func Test_p1_credit_pays_renewal_and_rest_carries_over(t *testing.T) {
	s := hiddenNew(t, 0, "business", "monthly", 2)
	hiddenChange(t, s, 15, "business", 1, 0)
	hiddenEq(t, "credit", s.Credit(), 2999)
	hiddenChange(t, s, 20, "team", 1, 0)
	hiddenEq(t, "credit", s.Credit(), 4165)
	hiddenEq(t, "renew", s.Renew(), 0)
	hiddenEq(t, "credit after renew", s.Credit(), 1666)
	hiddenEq(t, "second renew", s.Renew(), 833)
	hiddenEq(t, "credit after second renew", s.Credit(), 0)
	hiddenEq(t, "third renew", s.Renew(), 2499)
}

func Test_p1_credit_lasts_several_renewals(t *testing.T) {
	s := hiddenNew(t, 0, "business", "monthly", 1)
	hiddenChange(t, s, 3, "starter", 1, 0)
	hiddenEq(t, "credit", s.Credit(), 4230)
	hiddenEq(t, "renew 1", s.Renew(), 0)
	hiddenEq(t, "credit 1", s.Credit(), 2931)
	hiddenEq(t, "renew 2", s.Renew(), 0)
	hiddenEq(t, "credit 2", s.Credit(), 1632)
	hiddenEq(t, "renew 3", s.Renew(), 0)
	hiddenEq(t, "credit 3", s.Credit(), 333)
	hiddenEq(t, "renew 4", s.Renew(), 966)
	hiddenEq(t, "credit 4", s.Credit(), 0)
}

func Test_p1_credit_pays_upgrade(t *testing.T) {
	s := hiddenNew(t, 0, "business", "monthly", 1)
	hiddenChange(t, s, 0, "starter", 1, 0)
	hiddenEq(t, "credit", s.Credit(), 4700)
	hiddenChange(t, s, 10, "team", 1, 0) // 800 of credit pays it
	hiddenEq(t, "credit", s.Credit(), 3900)
	hiddenChange(t, s, 10, "business", 2, 2433) // 6333 less 3900 credit
	hiddenEq(t, "credit", s.Credit(), 0)
}

func Test_p1_change_day_must_be_in_current_period(t *testing.T) {
	s := hiddenNew(t, 10, "team", "monthly", 1)
	hiddenChangeErr(t, s, 40, "team", 2, ErrOutsidePeriod)
	hiddenChangeErr(t, s, 9, "team", 2, ErrOutsidePeriod)
	hiddenEq(t, "price after errors", s.PeriodPrice(), 2499)
	hiddenChange(t, s, 39, "team", 2, 83)
	hiddenEq(t, "renew", s.Renew(), 4998)
	hiddenChangeErr(t, s, 39, "team", 1, ErrOutsidePeriod)
	hiddenChangeErr(t, s, 70, "team", 1, ErrOutsidePeriod)
	hiddenChange(t, s, 40, "team", 1, 0)
	hiddenEq(t, "credit", s.Credit(), 2499)
}

func Test_p1_bad_change_changes_nothing(t *testing.T) {
	s := hiddenNew(t, 0, "team", "monthly", 2)
	hiddenChange(t, s, 5, "team", 1, 0)
	hiddenChangeErr(t, s, 6, "pro", 1, ErrUnknownPlan)
	hiddenChangeErr(t, s, 6, "team", 0, ErrInvalidSeats)
	hiddenChangeErr(t, s, 6, "team", 501, ErrInvalidSeats)
	hiddenChangeErr(t, s, 30, "pro", 0, ErrOutsidePeriod)
	hiddenEq(t, "price", s.PeriodPrice(), 2499)
	hiddenEq(t, "credit", s.Credit(), 2082)
	hiddenEq(t, "renew", s.Renew(), 417)
}

func Test_p1_annual_proration(t *testing.T) {
	s := hiddenNew(t, 0, "team", "annual", 1)
	hiddenChange(t, s, 354, "team", 2, 417) // 24990 * 6/360 = 416.5
	hiddenChange(t, s, 300, "team", 1, 0)   // 24990 * 60/360 = 4165
	hiddenEq(t, "credit", s.Credit(), 4165)
	b := hiddenNew(t, 0, "business", "annual", 10)
	hiddenChange(t, b, 90, "starter", 10, 0)
	hiddenEq(t, "credit", b.Credit(), 352500)
	hiddenEq(t, "renew", b.Renew(), 0)
	hiddenEq(t, "credit after renew", b.Credit(), 222600)
	hiddenEq(t, "end", b.PeriodEnd(), 720)
}
