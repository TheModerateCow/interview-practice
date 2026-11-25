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
	n := len(jobs)
	k = min(k, n)
	inputs := make([][]int, n)
	root := -1
	for i, j := range jobs {
		if j.Consumer < 0 {
			root = i
		} else {
			inputs[j.Consumer] = append(inputs[j.Consumer], i)
		}
	}
	if root < 0 {
		return -1
	}
	// BFS from the release over inputs; a job on a cycle is never reached.
	order := []int{root}
	for q := 0; q < len(order); q++ {
		order = append(order, inputs[order[q]]...)
	}
	if len(order) != n {
		return -1
	}
	// f[v][b]: fewest minutes to finish v using at most b warm caches in
	// v's subtree. Inputs run in parallel, so merging a child is a min-max
	// split of the budget.
	f := make([][]int, n)
	for q := n - 1; q >= 0; q-- {
		v := order[q]
		g := make([]int, k+1) // inputs ready with at most b warm: 0 with no inputs
		for _, c := range inputs[v] {
			fc := f[c]
			ng := make([]int, k+1)
			for b := 0; b <= k; b++ {
				best := -1
				for i := 0; i <= b; i++ {
					if t := max(g[b-i], fc[i]); best < 0 || t < best {
						best = t
					}
				}
				ng[b] = best
			}
			g = ng
			f[c] = nil
		}
		fv := make([]int, k+1)
		for b := 0; b <= k; b++ {
			fv[b] = jobs[v].Cold + g[b]
			if b > 0 {
				fv[b] = min(fv[b], jobs[v].Warm+g[b-1])
			}
		}
		f[v] = fv
	}
	return f[root][k]
}
