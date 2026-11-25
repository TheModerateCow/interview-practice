package route

import (
	"testing"
	"time"
)

func hiddenCheck(t *testing.T, n, capacity, charge int, rate []int, roads []Road, want int) {
	t.Helper()
	if got := FastestDelivery(n, capacity, charge, rate, roads); got != want {
		t.Fatalf("FastestDelivery(n=%d, capacity=%d, charge=%d, rate=%v, roads=%v) = %d, want %d", n, capacity, charge, rate, roads, got, want)
	}
}

func Test_p1_worked_example(t *testing.T) {
	hiddenCheck(t, 5, 10, 4, []int{0, 5, 1, 0, 0}, []Road{{0, 1, 10, 2}, {1, 2, 10, 2}, {2, 4, 10, 6}, {0, 3, 5, 4}, {3, 4, 5, 6}}, 36)
}

func Test_p1_single_junction(t *testing.T) {
	hiddenCheck(t, 1, 0, 0, []int{0}, []Road{}, 0)
}

func Test_p1_disconnected(t *testing.T) {
	hiddenCheck(t, 3, 5, 5, []int{1, 1, 1}, []Road{{0, 1, 1, 1}}, -1)
}

func Test_p1_too_little_charge_no_charger(t *testing.T) {
	hiddenCheck(t, 2, 5, 3, []int{0, 0}, []Road{{0, 1, 1, 4}}, -1)
}

func Test_p1_arrive_with_empty_battery(t *testing.T) {
	hiddenCheck(t, 3, 4, 4, []int{0, 0, 0}, []Road{{0, 1, 3, 1}, {1, 2, 4, 3}}, 7)
}

func Test_p1_road_longer_than_battery(t *testing.T) {
	hiddenCheck(t, 3, 3, 3, []int{1, 1, 0}, []Road{{0, 1, 1, 1}, {1, 2, 1, 4}}, -1)
}

func Test_p1_partial_charge_beats_full(t *testing.T) {
	hiddenCheck(t, 2, 10, 0, []int{3, 0}, []Road{{0, 1, 5, 2}}, 11)
}

func Test_p1_slow_road_saves_energy(t *testing.T) {
	hiddenCheck(t, 3, 5, 5, []int{0, 0, 0}, []Road{{0, 1, 2, 5}, {0, 1, 6, 1}, {1, 2, 2, 3}}, 8)
}

func Test_p1_detour_to_charger_and_back(t *testing.T) {
	hiddenCheck(t, 3, 6, 2, []int{0, 2, 0}, []Road{{0, 1, 1, 1}, {0, 2, 4, 5}}, 16)
}

func Test_p1_roads_work_both_ways(t *testing.T) {
	hiddenCheck(t, 4, 5, 5, []int{0, 0, 0, 0}, []Road{{3, 2, 1, 1}, {2, 1, 1, 1}, {1, 0, 1, 1}, {0, 3, 1, 9}}, 3)
}

func Test_p1_no_charger_means_no_charge(t *testing.T) {
	hiddenCheck(t, 2, 5, 0, []int{0, 0}, []Road{{0, 1, 1, 1}}, -1)
}

func Test_p1_split_charging_across_stations(t *testing.T) {
	hiddenCheck(t, 4, 10, 1, []int{2, 6, 1, 0}, []Road{{0, 1, 3, 1}, {1, 2, 3, 1}, {2, 3, 3, 10}, {0, 3, 40, 8}}, 21)
}

func Test_p1_equal_time_parallel_roads(t *testing.T) {
	hiddenCheck(t, 3, 5, 5, []int{0, 0, 0}, []Road{{0, 1, 3, 4}, {0, 1, 3, 1}, {1, 2, 3, 3}}, 6)
}

// hiddenBigNetwork builds a long, connected 1000-junction network with 5000 roads,
// so the van has to recharge many times on the way.
func hiddenBigNetwork() (int, int, int, []int, []Road) {
	seed := uint64(20261125)
	next := func(k int) int {
		seed = seed*6364136223846793005 + 1442695040888963407
		return int((seed >> 33) % uint64(k))
	}
	n, capacity := 1000, 100
	rate := make([]int, n)
	for i := range rate {
		if next(5) == 0 {
			rate[i] = 1 + next(20)
		}
	}
	rate[n-1] = 0
	roads := make([]Road, 0, 5000)
	for i := 1; i < n; i++ {
		roads = append(roads, Road{i - 1 - next(min(i, 4)), i, 1 + next(60), 5 + next(30)})
	}
	for len(roads) < 5000 {
		a := next(n)
		roads = append(roads, Road{a, min(n-1, a+1+next(6)), 1 + next(60), 5 + next(30)})
	}
	return n, capacity, 30, rate, roads
}

func Test_p1_large_network(t *testing.T) {
	n, capacity, charge, rate, roads := hiddenBigNetwork()
	start := time.Now()
	if got := FastestDelivery(n, capacity, charge, rate, roads); got != 14023 {
		t.Fatalf("large network: got %d, want 14023", got)
	}
	if d := time.Since(start); d > 2*time.Second {
		t.Fatalf("took %v on 1000 junctions, 5000 roads, capacity 100; expected well under 2*time.Second", d)
	}
}
