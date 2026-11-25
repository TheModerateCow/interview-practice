// Reads "n m", then the n capacities, then m lines "board alight" (any whitespace),
// and prints MaxUpgrades.
package main

import (
	"bufio"
	"fmt"
	"os"

	"upgrades"
)

func main() {
	in := bufio.NewReader(os.Stdin)
	var n, m int
	fmt.Fscan(in, &n, &m)
	cap := make([]int, n)
	for i := range cap {
		fmt.Fscan(in, &cap[i])
	}
	requests := make([][]int, m)
	for i := range requests {
		requests[i] = make([]int, 2)
		fmt.Fscan(in, &requests[i][0], &requests[i][1])
	}
	fmt.Println(upgrades.MaxUpgrades(cap, requests))
}
