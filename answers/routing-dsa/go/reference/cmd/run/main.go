// Reads one network from stdin and prints FastestDelivery's answer:
//
//	n m capacity charge
//	rate_0 rate_1 ... rate_{n-1}
//	a b minutes energy      (m lines, one per road)
package main

import (
	"bufio"
	"fmt"
	"os"

	"route"
)

func main() {
	in := bufio.NewReader(os.Stdin)
	var n, m, capacity, charge int
	fmt.Fscan(in, &n, &m, &capacity, &charge)
	rate := make([]int, n)
	for i := range rate {
		fmt.Fscan(in, &rate[i])
	}
	roads := make([]route.Road, m)
	for i := range roads {
		r := &roads[i]
		fmt.Fscan(in, &r.A, &r.B, &r.Minutes, &r.Energy)
	}
	fmt.Println(route.FastestDelivery(n, capacity, charge, rate, roads))
}
