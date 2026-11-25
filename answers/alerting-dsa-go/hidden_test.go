package alerting

import (
	"testing"
	"time"
)

func hiddenCheck(t *testing.T, requests, errors []int, budgetPPM, want int) {
	t.Helper()
	if got := LongestCompliantWindow(requests, errors, budgetPPM); got != want {
		t.Fatalf("LongestCompliantWindow(%v, %v, %d) = %d, want %d", requests, errors, budgetPPM, got, want)
	}
}

// hiddenTraffic returns n deterministic minutes: 500-1500 requests and 0-40 errors each (about 2% errors).
func hiddenTraffic(seed uint64, n int) ([]int, []int) {
	requests, errors := make([]int, n), make([]int, n)
	next := func(m int) int {
		seed = seed*6364136223846793005 + 1442695040888963407
		return int((seed >> 33) % uint64(m))
	}
	for i := range requests {
		requests[i] = 500 + next(1001)
		errors[i] = next(41)
	}
	return requests, errors
}

func Test_p1_worked_example(t *testing.T) {
	hiddenCheck(t, []int{120, 80, 200, 40, 160, 100}, []int{2, 6, 1, 5, 0, 9}, 20000, 3)
}

func Test_p1_no_minutes(t *testing.T) {
	hiddenCheck(t, nil, nil, 20000, 0)
}

func Test_p1_every_minute_over_budget(t *testing.T) {
	hiddenCheck(t, []int{10, 20, 5}, []int{5, 5, 5}, 100000, 0)
}

func Test_p1_whole_range_within_budget(t *testing.T) {
	hiddenCheck(t, []int{100, 100, 100, 100}, []int{0, 1, 0, 1}, 20000, 4)
	hiddenCheck(t, []int{3, 7, 1}, []int{3, 7, 1}, 1000000, 3)
}

func Test_p1_exactly_on_budget_counts(t *testing.T) {
	hiddenCheck(t, []int{100}, []int{2}, 20000, 1)
	hiddenCheck(t, []int{50, 30, 20}, []int{3, 0, 0}, 30000, 3)
}

func Test_p1_zero_budget(t *testing.T) {
	hiddenCheck(t, []int{5, 3, 0, 7, 2, 4, 9, 9, 9}, []int{0, 0, 0, 1, 0, 0, 0, 0, 1}, 0, 4)
}

func Test_p1_quiet_minutes(t *testing.T) {
	hiddenCheck(t, []int{0, 0, 0}, []int{0, 0, 0}, 0, 3)
	hiddenCheck(t, []int{100, 0, 0, 100}, []int{3, 0, 0, 1}, 20000, 4)
}

func Test_p1_bad_first_minute_absorbed(t *testing.T) {
	hiddenCheck(t, []int{10, 1000}, []int{1, 0}, 20000, 2)
}

func Test_p1_bad_minutes_inside_window(t *testing.T) {
	hiddenCheck(t, []int{10, 400, 10, 10, 400, 10}, []int{9, 0, 3, 3, 0, 9}, 20000, 5)
}

func Test_p1_rate_weighted_by_traffic(t *testing.T) {
	hiddenCheck(t, []int{1, 1000000}, []int{1, 0}, 1000, 2)
	hiddenCheck(t, []int{1000000, 1}, []int{500000, 0}, 300000, 1)
}

func Test_p1_longest_is_not_the_first(t *testing.T) {
	hiddenCheck(t, []int{100, 100, 10, 10, 100, 100, 100}, []int{0, 0, 10, 10, 0, 0, 0}, 20000, 3)
}

func Test_p1_large_counts(t *testing.T) {
	hiddenCheck(t, []int{1000000, 1000000, 1000000, 1000000, 1000000}, []int{1000000, 0, 0, 0, 0}, 200000, 5)
	hiddenCheck(t, []int{1000000, 1000000, 1000000, 1000000, 1000000}, []int{1000000, 0, 0, 0, 1}, 200000, 4)
}

func Test_p1_medium_random(t *testing.T) {
	requests, errors := hiddenTraffic(7, 3000)
	hiddenCheck(t, requests, errors, 19000, 528)
}

func Test_p1_large_fast(t *testing.T) {
	requests, errors := hiddenTraffic(42, 200000)
	done := make(chan int, 1)
	go func() { done <- LongestCompliantWindow(requests, errors, 19000) }()
	select {
	case got := <-done:
		if got != 1597 {
			t.Fatalf("200000 minutes at 19000 ppm: got %d, want 1597", got)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("200000 minutes took over 2s: checking every window is O(n^2); aim for O(n log n) or O(n)")
	}
}
