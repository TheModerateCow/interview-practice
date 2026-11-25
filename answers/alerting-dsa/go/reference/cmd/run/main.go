// Reads "n budgetPPM", then n request counts, then n error counts (any whitespace),
// and prints LongestCompliantWindow.
package main

import (
	"bufio"
	"fmt"
	"os"

	"alerting"
)

func main() {
	in := bufio.NewReader(os.Stdin)
	var n, budget int
	fmt.Fscan(in, &n, &budget)
	requests, errors := make([]int, n), make([]int, n)
	for i := range requests {
		fmt.Fscan(in, &requests[i])
	}
	for i := range errors {
		fmt.Fscan(in, &errors[i])
	}
	fmt.Println(alerting.LongestCompliantWindow(requests, errors, budget))
}
