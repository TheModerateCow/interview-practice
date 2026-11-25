package alerting

// LongestCompliantWindow returns the length of the longest run of consecutive minutes whose
// combined error rate is within budget: total errors * 1_000_000 <= total requests * budgetPPM.
func LongestCompliantWindow(requests, errors []int, budgetPPM int) int {
	n := len(requests)
	// Minute i weighs errors*1e6 - requests*budget; a window is compliant when its weights sum to <= 0,
	// i.e. prefix[j] <= prefix[i] for the window covering minutes i..j-1.
	prefix := make([]int, n+1)
	for i := 0; i < n; i++ {
		prefix[i+1] = prefix[i] + errors[i]*1_000_000 - requests[i]*budgetPPM
	}
	// Only a running maximum of prefix can be the best start: an earlier start that is at least as high wins.
	starts := []int{}
	for i := 0; i <= n; i++ {
		if len(starts) == 0 || prefix[i] > prefix[starts[len(starts)-1]] {
			starts = append(starts, i)
		}
	}
	best := 0
	for j := n; j >= 0 && len(starts) > 0; j-- {
		for len(starts) > 0 && prefix[starts[len(starts)-1]] >= prefix[j] {
			best = max(best, j-starts[len(starts)-1])
			starts = starts[:len(starts)-1]
		}
	}
	return best
}
