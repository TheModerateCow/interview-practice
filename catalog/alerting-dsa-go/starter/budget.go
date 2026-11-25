package alerting

// LongestCompliantWindow returns the length of the longest run of consecutive minutes whose
// combined error rate is within budget: total errors * 1_000_000 <= total requests * budgetPPM.
func LongestCompliantWindow(requests, errors []int, budgetPPM int) int {
	panic("not implemented")
}
