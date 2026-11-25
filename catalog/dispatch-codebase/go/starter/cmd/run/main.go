// Drives the dispatcher from stdin, one command per line, and prints each
// result (or "error: ..."):
//
//	courier <id> <x> <y> <capacity>
//	order <id> <restaurantX> <restaurantY> <customerX> <customerY> <placedAt> <prepMinutes>
//	assign <order>
//	advance <order> <picked_up|delivered|cancelled>
//	eta <order> <now>
//	dispatch <now>
//	bag <courier>
//
// Add your own commands here if they help.
package main

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"

	"dispatch"
)

func main() {
	d := dispatch.New()
	sc := bufio.NewScanner(os.Stdin)
	for sc.Scan() {
		f := strings.Fields(sc.Text())
		if len(f) == 0 {
			continue
		}
		num := func(i int) int { n, _ := strconv.Atoi(f[i]); return n }
		pt := func(i int) dispatch.Point { return dispatch.Point{X: num(i), Y: num(i + 1)} }
		switch {
		case f[0] == "courier" && len(f) == 5:
			report("ok", d.AddCourier(f[1], pt(2), num(4)))
		case f[0] == "order" && len(f) == 8:
			report("ok", d.PlaceOrder(f[1], pt(2), pt(4), num(6), num(7)))
		case f[0] == "assign" && len(f) == 2:
			c, err := d.Assign(f[1])
			report(c, err)
		case f[0] == "advance" && len(f) == 3:
			s, ok := dispatch.ParseState(f[2])
			if !ok {
				fmt.Println("error: unknown state", f[2])
				continue
			}
			report("ok", d.Advance(f[1], s))
		case f[0] == "eta" && len(f) == 3:
			m, err := d.ETA(f[1], num(2))
			report(strconv.Itoa(m), err)
		case f[0] == "dispatch" && len(f) == 2:
			var parts []string
			for _, a := range d.DispatchPending(num(1)) {
				parts = append(parts, a.OrderID+"->"+a.CourierID)
			}
			fmt.Println("[" + strings.Join(parts, " ") + "]")
		case f[0] == "bag" && len(f) == 2:
			ids, err := d.CourierOrders(f[1])
			report("["+strings.Join(ids, " ")+"]", err)
		default:
			fmt.Println("unknown command:", sc.Text())
		}
	}
}

func report(out string, err error) {
	if err != nil {
		fmt.Println("error:", err)
		return
	}
	fmt.Println(out)
}
