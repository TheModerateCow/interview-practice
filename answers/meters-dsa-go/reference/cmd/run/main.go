// Reads "n capacity wear", then n half-hourly prices (any whitespace), and prints BestBatteryProfit.
package main

import (
	"bufio"
	"fmt"
	"os"

	"meters"
)

func main() {
	in := bufio.NewReader(os.Stdin)
	var n, capacity, wear int
	fmt.Fscan(in, &n, &capacity, &wear)
	prices := make([]int, n)
	for i := range prices {
		fmt.Fscan(in, &prices[i])
	}
	fmt.Println(meters.BestBatteryProfit(prices, capacity, wear))
}
