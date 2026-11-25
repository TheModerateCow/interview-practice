// Drives the box office from stdin, one command per line, and prints each result:
//
//	create <ts> <event> <capacity>
//	buy <ts> <event> <buyer> <qty>
//	refund <ts> <event> <buyer> <qty>
//	available <ts> <event>
//
// Add your own commands here as you build later levels.
package main

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"

	"tickets"
)

func main() {
	o := tickets.NewOffice()
	sc := bufio.NewScanner(os.Stdin)
	for sc.Scan() {
		f := strings.Fields(sc.Text())
		if len(f) < 3 {
			continue
		}
		ts, _ := strconv.Atoi(f[1])
		num := func(i int) int { n, _ := strconv.Atoi(f[i]); return n }
		switch {
		case f[0] == "create" && len(f) == 4:
			fmt.Println(o.CreateEvent(ts, f[2], num(3)))
		case f[0] == "buy" && len(f) == 5:
			fmt.Println(o.Buy(ts, f[2], f[3], num(4)))
		case f[0] == "refund" && len(f) == 5:
			fmt.Println(o.Refund(ts, f[2], f[3], num(4)))
		case f[0] == "available" && len(f) == 3:
			fmt.Println(o.Available(ts, f[2]))
		default:
			fmt.Println("unknown command:", sc.Text())
		}
	}
}
