// Drives the inventory service from stdin, one command per line, and prints each result:
//
//	warehouse <id>
//	rule <warehouse> <sku> <min> <max> <pack>
//	receive <ts> <warehouse> <bin> <sku> <qty>
//	reserve <ts> <id> <warehouse> <sku> <qty> <ttl>
//	release <ts> <id>
//	commit <ts> <id>
//	transfer <ts> <id> <from> <to> <sku> <qty>
//	arrive <ts> <transfer> <bin>
//	available <ts> <warehouse> <sku>
//	onhand <warehouse> <sku>
//	bin <warehouse> <bin> <sku>
//	replenish <ts> <warehouse>
//
// Times are Unix seconds; ttl is in seconds. Add your own commands as you need them.
package main

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"

	"inventory"
)

func main() {
	s := inventory.New()
	sc := bufio.NewScanner(os.Stdin)
	for sc.Scan() {
		f := strings.Fields(sc.Text())
		if len(f) == 0 {
			continue
		}
		num := func(i int) int64 { n, _ := strconv.ParseInt(f[i], 10, 64); return n }
		report := func(err error) {
			if err != nil {
				fmt.Println("error:", err)
			} else {
				fmt.Println("ok")
			}
		}
		switch {
		case f[0] == "warehouse" && len(f) == 2:
			report(s.AddWarehouse(f[1]))
		case f[0] == "rule" && len(f) == 6:
			report(s.SetRule(f[1], f[2], inventory.Rule{Min: int(num(3)), Max: int(num(4)), Pack: int(num(5))}))
		case f[0] == "receive" && len(f) == 6:
			report(s.Receive(f[2], f[3], f[4], int(num(5)), num(1)))
		case f[0] == "reserve" && len(f) == 7:
			_, err := s.Reserve(f[2], f[3], f[4], int(num(5)), num(6), num(1))
			report(err)
		case f[0] == "release" && len(f) == 3:
			report(s.Release(f[2], num(1)))
		case f[0] == "commit" && len(f) == 3:
			report(s.Commit(f[2], num(1)))
		case f[0] == "transfer" && len(f) == 7:
			_, err := s.StartTransfer(f[2], f[3], f[4], f[5], int(num(6)), num(1))
			report(err)
		case f[0] == "arrive" && len(f) == 4:
			report(s.ReceiveTransfer(f[2], f[3], num(1)))
		case f[0] == "available" && len(f) == 4:
			n, err := s.Available(f[2], f[3], num(1))
			if err != nil {
				report(err)
			} else {
				fmt.Println(n)
			}
		case f[0] == "onhand" && len(f) == 3:
			fmt.Println(s.OnHand(f[1], f[2]))
		case f[0] == "bin" && len(f) == 4:
			fmt.Println(s.BinQty(f[1], f[2], f[3]))
		case f[0] == "replenish" && len(f) == 3:
			plan, err := s.Replenishment(f[2], num(1))
			if err != nil {
				report(err)
			}
			for _, sg := range plan {
				from := sg.From
				if from == "" {
					from = "supplier"
				}
				fmt.Printf("%s position=%d qty=%d from=%s\n", sg.SKU, sg.Position, sg.Qty, from)
			}
			if err == nil && len(plan) == 0 {
				fmt.Println("nothing to replenish")
			}
		default:
			fmt.Println("unknown command:", sc.Text())
		}
	}
}
