package pipeline

// Job is one step of a fan-in pipeline. Its artifact is used by exactly one
// downstream job, Consumer (-1 for the release job). It takes Cold minutes,
// or Warm minutes if its cache was pre-warmed (0 <= Warm <= Cold).
type Job struct{ Consumer, Cold, Warm int }

// FastestRelease returns the fewest minutes until the release job finishes
// when at most k jobs are pre-warmed and every job starts as soon as all the
// jobs that feed it have finished. It returns -1 if the consumer links
// contain a cycle.
func FastestRelease(jobs []Job, k int) int {
	panic("not implemented")
}
