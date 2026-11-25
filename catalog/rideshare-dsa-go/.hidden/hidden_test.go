package dispatch

import (
	"testing"
	"time"
)

func hiddenCheck(t *testing.T, riders, drivers []int, need, want int) {
	t.Helper()
	if got := MinDispatchRadius(riders, drivers, need); got != want {
		t.Fatalf("MinDispatchRadius(%v, %v, %d) = %d, want %d", riders, drivers, need, got, want)
	}
}

// positions returns n deterministic pseudo-random positions in [-1e9, 1e9].
func hiddenPositions(seed uint64, n int) []int {
	out := make([]int, n)
	for i := range out {
		seed = seed*6364136223846793005 + 1442695040888963407
		out[i] = int((seed>>33)%2000000001) - 1000000000
	}
	return out
}

func Test_p1_worked_example(t *testing.T) {
	hiddenCheck(t, []int{2, 9, 15}, []int{4, 10, 30}, 2, 2)
}

func Test_p1_serve_everyone(t *testing.T) {
	hiddenCheck(t, []int{2, 9, 15}, []int{4, 10, 30}, 3, 15)
}

func Test_p1_need_zero(t *testing.T) {
	hiddenCheck(t, nil, nil, 0, 0)
	hiddenCheck(t, []int{5}, []int{90}, 0, 0)
}

func Test_p1_too_few_drivers(t *testing.T) {
	hiddenCheck(t, []int{1, 2, 3}, []int{2, 4}, 3, -1)
	hiddenCheck(t, []int{1}, nil, 1, -1)
}

func Test_p1_too_few_riders(t *testing.T) {
	hiddenCheck(t, []int{7, 8}, []int{1, 2, 3, 4}, 3, -1)
}

func Test_p1_same_spot(t *testing.T) {
	hiddenCheck(t, []int{5, 5, 7}, []int{7, 5, 5}, 3, 0)
}

func Test_p1_exact_reach_counts(t *testing.T) {
	hiddenCheck(t, []int{0}, []int{4}, 1, 4)
	hiddenCheck(t, []int{10}, []int{3}, 1, 7)
}

func Test_p1_driver_takes_one_rider(t *testing.T) {
	hiddenCheck(t, []int{0, 1}, []int{0, 10}, 2, 9)
}

func Test_p1_nearest_first_is_not_optimal(t *testing.T) {
	hiddenCheck(t, []int{6, 5}, []int{5, 7}, 2, 1)
}

func Test_p1_skip_unreachable_rider(t *testing.T) {
	hiddenCheck(t, []int{0, 50, 100}, []int{1, 101}, 2, 1)
}

func Test_p1_choose_best_subset(t *testing.T) {
	hiddenCheck(t, []int{300, 0, 200, 100}, []int{1000, 198, -50, 103}, 3, 50)
	hiddenCheck(t, []int{300, 0, 200, 100}, []int{1000, 198, -50, 103}, 4, 700)
}

func Test_p1_far_ends_of_corridor(t *testing.T) {
	hiddenCheck(t, []int{-1000000000}, []int{1000000000}, 1, 2000000000)
}

func Test_p1_medium_random(t *testing.T) {
	hiddenCheck(t, hiddenPositions(7, 2000), hiddenPositions(11, 1500), 1200, 1340433)
}

func Test_p1_large_fast(t *testing.T) {
	riders, drivers := hiddenPositions(42, 200000), hiddenPositions(99, 200000)
	done := make(chan int, 1)
	go func() { done <- MinDispatchRadius(riders, drivers, 150000) }()
	select {
	case got := <-done:
		if got != 14866 {
			t.Fatalf("200000 riders and drivers, need 150000: got %d, want 14866", got)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("200000 riders and drivers took over 2s: aim for O((n+m) log(n+m) + (n+m) log C)")
	}
}
