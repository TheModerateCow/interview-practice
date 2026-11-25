package loyalty

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

func hiddenEarn(t *testing.T, a *Account, day, cents, want int) {
	t.Helper()
	got, err := a.Earn(day, cents)
	if err != nil {
		t.Fatalf("Earn(%d, %d): unexpected error %v", day, cents, err)
	}
	if got != want {
		t.Fatalf("Earn(%d, %d): got %d points want %d", day, cents, got, want)
	}
}

func hiddenIs(t *testing.T, what string, got, want error) {
	t.Helper()
	if !errors.Is(got, want) {
		t.Fatalf("%s: got error %v want %v", what, got, want)
	}
}

func Test_p1_new_account(t *testing.T) {
	a := NewAccount()
	hiddenEq(t, "tier", a.Tier(), "base")
	hiddenEq(t, "balance", a.Balance(0), 0)
	hiddenIs(t, "redeem from empty", a.Redeem(0, 1), ErrInsufficientPoints)
}

func Test_p1_base_points_round_half_up(t *testing.T) {
	a := NewAccount()
	hiddenEarn(t, a, 1, 1000, 10)
	hiddenEarn(t, a, 1, 1049, 10)
	hiddenEarn(t, a, 1, 1050, 11)
	hiddenEarn(t, a, 1, 49, 0)
	hiddenEarn(t, a, 1, 50, 1)
	hiddenEarn(t, a, 1, 1, 0)
	hiddenEq(t, "balance", a.Balance(1), 32)
}

func Test_p1_silver_rate_and_rounding(t *testing.T) {
	a := NewAccount()
	hiddenEarn(t, a, 1, 50_000, 500)
	hiddenEq(t, "tier", a.Tier(), "silver")
	hiddenEarn(t, a, 2, 1000, 13) // 12.5
	hiddenEarn(t, a, 2, 1030, 13) // 12.875
	hiddenEarn(t, a, 2, 1080, 14) // 13.5
	hiddenEarn(t, a, 2, 1039, 13) // 12.9875
	hiddenEq(t, "balance", a.Balance(2), 553)
}

func Test_p1_gold_rate_and_rounding(t *testing.T) {
	a := NewAccount()
	hiddenEarn(t, a, 1, 200_000, 500)
	hiddenEq(t, "tier", a.Tier(), "gold")
	hiddenEarn(t, a, 2, 1000, 15)
	hiddenEarn(t, a, 2, 1033, 15) // 15.495
	hiddenEarn(t, a, 2, 1034, 16) // 15.51
}

func Test_p1_tier_thresholds(t *testing.T) {
	a := NewAccount()
	hiddenEarn(t, a, 1, 49_999, 500)
	hiddenEq(t, "tier at 499.99", a.Tier(), "base")
	hiddenEarn(t, a, 1, 1, 0)
	hiddenEq(t, "tier at 500.00", a.Tier(), "silver")
	hiddenEarn(t, a, 1, 149_999, 500)
	hiddenEq(t, "tier at 1999.99", a.Tier(), "silver")
	hiddenEarn(t, a, 1, 1, 0)
	hiddenEq(t, "tier at 2000.00", a.Tier(), "gold")
}

func Test_p1_crossing_purchase_earns_at_old_tier(t *testing.T) {
	a := NewAccount()
	hiddenEarn(t, a, 1, 40_000, 400)
	hiddenEarn(t, a, 2, 20_000, 200)
	hiddenEq(t, "tier", a.Tier(), "silver")
	hiddenEarn(t, a, 3, 1000, 13)
	hiddenEarn(t, a, 4, 139_000, 500)
	hiddenEq(t, "tier", a.Tier(), "gold")
	hiddenEarn(t, a, 5, 1000, 15)
}

func Test_p1_cap_per_purchase(t *testing.T) {
	a := NewAccount()
	hiddenEarn(t, a, 1, 50_000, 500)
	hiddenEarn(t, a, 1, 60_000, 500)
	b := NewAccount()
	hiddenEarn(t, b, 1, 200_000, 500)
	hiddenEarn(t, b, 1, 40_000, 500)
	hiddenEq(t, "balance", b.Balance(1), 1000)
}

func Test_p1_zero_point_purchases_count_towards_tier(t *testing.T) {
	a := NewAccount()
	hiddenEarn(t, a, 1, 49_990, 500)
	hiddenEarn(t, a, 1, 10, 0)
	hiddenEq(t, "tier", a.Tier(), "silver")
	hiddenEq(t, "balance", a.Balance(1), 500)
}

func Test_p1_invalid_spend(t *testing.T) {
	a := NewAccount()
	for _, c := range []int{0, -100} {
		p, err := a.Earn(1, c)
		hiddenIs(t, "earn error", err, ErrInvalidAmount)
		hiddenEq(t, "points on error", p, 0)
	}
	hiddenEarn(t, a, 1, 49_999, 500)
	_, err := a.Earn(1, 0)
	hiddenIs(t, "earn 0 error", err, ErrInvalidAmount)
	hiddenEq(t, "tier unchanged", a.Tier(), "base")
	hiddenEq(t, "balance unchanged", a.Balance(1), 500)
}

func Test_p1_points_expire_after_365_days(t *testing.T) {
	a := NewAccount()
	hiddenEarn(t, a, 10, 1000, 10)
	hiddenEq(t, "balance day 10", a.Balance(10), 10)
	hiddenEq(t, "balance day 374", a.Balance(374), 10)
	hiddenEq(t, "balance day 375", a.Balance(375), 0)
	hiddenIs(t, "redeem expired", a.Redeem(375, 1), ErrInsufficientPoints)
}

func Test_p1_redeem_rules(t *testing.T) {
	a := NewAccount()
	hiddenEarn(t, a, 0, 2500, 25)
	hiddenIs(t, "redeem 0", a.Redeem(1, 0), ErrInvalidAmount)
	hiddenIs(t, "redeem negative", a.Redeem(1, -5), ErrInvalidAmount)
	hiddenIs(t, "redeem too many", a.Redeem(1, 26), ErrInsufficientPoints)
	hiddenEq(t, "balance after failed redeem", a.Balance(1), 25)
	hiddenIs(t, "redeem 10", a.Redeem(1, 10), nil)
	hiddenEq(t, "balance", a.Balance(1), 15)
	hiddenIs(t, "redeem all", a.Redeem(1, 15), nil)
	hiddenEq(t, "balance", a.Balance(1), 0)
}

func Test_p1_redeem_uses_oldest_points_first(t *testing.T) {
	a := NewAccount()
	hiddenEarn(t, a, 0, 10_000, 100)
	hiddenEarn(t, a, 100, 5000, 50)
	hiddenIs(t, "redeem 120", a.Redeem(200, 120), nil)
	hiddenEq(t, "balance day 200", a.Balance(200), 30)
	hiddenEq(t, "balance day 365", a.Balance(365), 30)
	hiddenEq(t, "balance day 464", a.Balance(464), 30)
	hiddenEq(t, "balance day 465", a.Balance(465), 0)
}

func Test_p1_redeem_ignores_expired_points(t *testing.T) {
	a := NewAccount()
	hiddenEarn(t, a, 0, 10_000, 100)
	hiddenEarn(t, a, 300, 5000, 50)
	hiddenEq(t, "balance day 364", a.Balance(364), 150)
	hiddenEq(t, "balance day 365", a.Balance(365), 50)
	hiddenIs(t, "redeem 60", a.Redeem(365, 60), ErrInsufficientPoints)
	hiddenIs(t, "redeem 50", a.Redeem(365, 50), nil)
	hiddenEq(t, "balance", a.Balance(365), 0)
}

func Test_p1_redeeming_keeps_tier(t *testing.T) {
	a := NewAccount()
	hiddenEarn(t, a, 0, 60_000, 500)
	hiddenIs(t, "redeem all", a.Redeem(10, 500), nil)
	hiddenEq(t, "tier after redeem", a.Tier(), "silver")
	hiddenEarn(t, a, 400, 1000, 13)
}
