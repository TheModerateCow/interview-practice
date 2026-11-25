package pipeline

import (
	"testing"
	"time"
)

func hiddenCheck(t *testing.T, jobs []Job, k, want int) {
	t.Helper()
	if got := FastestRelease(jobs, k); got != want {
		t.Fatalf("FastestRelease(%v, k=%d) = %d, want %d", jobs, k, got, want)
	}
}

func Test_p1_worked_example(t *testing.T) {
	hiddenCheck(t, []Job{{-1, 5, 2}, {0, 10, 3}, {0, 10, 4}, {1, 2, 2}}, 2, 10)
}

func Test_p1_single_job(t *testing.T) {
	hiddenCheck(t, []Job{{-1, 7, 3}}, 1, 3)
}

func Test_p1_no_warm_slots(t *testing.T) {
	hiddenCheck(t, []Job{{2, 4, 0}, {2, 6, 1}, {-1, 3, 0}, {0, 5, 0}, {1, 1, 0}}, 0, 12)
}

func Test_p1_more_slots_than_jobs(t *testing.T) {
	hiddenCheck(t, []Job{{-1, 8, 2}, {0, 6, 1}, {0, 9, 3}}, 10, 5)
}

func Test_p1_equal_branches_one_slot(t *testing.T) {
	hiddenCheck(t, []Job{{-1, 6, 1}, {0, 9, 1}, {0, 9, 1}}, 1, 10)
}

func Test_p1_all_slots_into_one_branch(t *testing.T) {
	hiddenCheck(t, []Job{{-1, 1, 1}, {0, 10, 0}, {1, 10, 0}, {2, 10, 0}, {0, 5, 5}}, 3, 6)
}

func Test_p1_cycle_beside_release(t *testing.T) {
	hiddenCheck(t, []Job{{-1, 3, 1}, {0, 2, 1}, {3, 4, 1}, {2, 5, 1}}, 1, -1)
}

func Test_p1_job_consumes_itself(t *testing.T) {
	hiddenCheck(t, []Job{{1, 2, 1}, {-1, 3, 1}, {2, 1, 0}}, 0, -1)
}

func Test_p1_release_listed_last(t *testing.T) {
	hiddenCheck(t, []Job{{3, 7, 2}, {5, 4, 4}, {5, 6, 0}, {5, 2, 1}, {1, 3, 3}, {-1, 2, 1}}, 2, 8)
}

func Test_p1_warm_no_faster(t *testing.T) {
	hiddenCheck(t, []Job{{-1, 4, 4}, {0, 6, 6}, {0, 3, 3}, {1, 0, 0}}, 3, 10)
}

func Test_p1_linear_chain(t *testing.T) {
	hiddenCheck(t, []Job{{-1, 5, 4}, {0, 9, 2}, {1, 3, 0}, {2, 8, 7}, {3, 6, 1}, {4, 2, 2}}, 2, 21)
}

func Test_p1_split_budget_unevenly(t *testing.T) {
	hiddenCheck(t, []Job{{-1, 2, 0}, {0, 12, 4}, {1, 6, 1}, {0, 7, 2}, {3, 7, 2}, {0, 9, 8}}, 3, 10)
}

// hiddenBigPipeline builds a deep 5000-job fan-in tree; every job feeds one
// of the five jobs listed just before it, and job 0 is the release.
func hiddenBigPipeline() []Job {
	seed := uint64(20261125)
	next := func(m int) int {
		seed = seed*6364136223846793005 + 1442695040888963407
		return int((seed >> 33) % uint64(m))
	}
	jobs := make([]Job, 5000)
	jobs[0] = Job{-1, 1 + next(1000), 0}
	for i := 1; i < len(jobs); i++ {
		cold := 1 + next(1000)
		jobs[i] = Job{i - 1 - next(min(i, 5)), cold, next(cold + 1)}
	}
	return jobs
}

func Test_p1_large_pipeline(t *testing.T) {
	jobs := hiddenBigPipeline()
	start := time.Now()
	if got := FastestRelease(jobs, 100); got != 772029 {
		t.Fatalf("large pipeline: got %d, want 772029", got)
	}
	if d := time.Since(start); d > 2*time.Second {
		t.Fatalf("took %v on 5000 jobs with k=100; expected well under 2*time.Second", d)
	}
}
