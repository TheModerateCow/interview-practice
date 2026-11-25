package meters

import (
	"testing"
	"time"
)

func hiddenCheck(t *testing.T, prices []int, capacity, wear, want int) {
	t.Helper()
	if got := BestBatteryProfit(prices, capacity, wear); got != want {
		t.Fatalf("BestBatteryProfit(%v, %d, %d) = %d, want %d", prices, capacity, wear, got, want)
	}
}

// hiddenPrices returns n deterministic half-hourly prices between -50 and 350.
func hiddenPrices(seed uint64, n int) []int {
	prices := make([]int, n)
	next := func(m int) int {
		seed = seed*6364136223846793005 + 1442695040888963407
		return int((seed >> 33) % uint64(m))
	}
	for i := range prices {
		prices[i] = next(401) - 50
	}
	return prices
}

func Test_p1_worked_example(t *testing.T) {
	hiddenCheck(t, []int{12, 9, 25, 14, 30, 8, 11, 27}, 2, 3, 44)
}

func Test_p1_no_slots(t *testing.T) {
	hiddenCheck(t, nil, 2, 3, 0)
}

func Test_p1_no_capacity(t *testing.T) {
	hiddenCheck(t, []int{30, 30, 32, 31}, 0, 0, 0)
	hiddenCheck(t, []int{-20, -5}, 0, 0, 0)
}

func Test_p1_falling_prices(t *testing.T) {
	hiddenCheck(t, []int{40, 31, 22, 15, 9}, 3, 0, 0)
}

func Test_p1_wear_eats_small_spread(t *testing.T) {
	hiddenCheck(t, []int{10, 14}, 1, 4, 0)
	hiddenCheck(t, []int{10, 15}, 1, 4, 1)
}

func Test_p1_one_kwh_per_slot(t *testing.T) {
	hiddenCheck(t, []int{5, 50}, 4, 0, 45)
	hiddenCheck(t, []int{20, 1, 1, 1, 1, 40, 40}, 4, 0, 78)
}

func Test_p1_capacity_limits_profit(t *testing.T) {
	hiddenCheck(t, []int{5, 6, 7, 50, 51, 52}, 3, 1, 132)
	hiddenCheck(t, []int{5, 6, 7, 50, 51, 52}, 2, 1, 90)
}

func Test_p1_negative_prices_pay_to_charge(t *testing.T) {
	hiddenCheck(t, []int{-10, -4, 20}, 3, 2, 32)
	hiddenCheck(t, []int{-10, -4}, 3, 2, 14)
}

func Test_p1_battery_cycles_many_times(t *testing.T) {
	hiddenCheck(t, []int{10, 30, 10, 30, 10, 30}, 1, 5, 45)
	hiddenCheck(t, []int{10, 30, 10, 30, 10, 30}, 5, 5, 45)
}

func Test_p1_extreme_values(t *testing.T) {
	hiddenCheck(t, []int{1000, -1000, 1000, -1000}, 1, 1000, 2000)
	hiddenCheck(t, []int{-1000, 1000, -1000, 1000}, 2, 0, 4000)
}

func Test_p1_medium_random(t *testing.T) {
	hiddenCheck(t, hiddenPrices(7, 2000), 12, 15, 184485)
}

func Test_p1_large_fast(t *testing.T) {
	prices := hiddenPrices(42, 100000)
	done := make(chan int, 1)
	go func() { done <- BestBatteryProfit(prices, 100, 20) }()
	select {
	case got := <-done:
		if got != 9067714 {
			t.Fatalf("100000 slots, capacity 100: got %d, want 9067714", got)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("100000 slots with capacity 100 took over 2s: aim for O(n * capacity)")
	}
}
