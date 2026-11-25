// Drives the shop from stdin, one command per line, and prints each result:
//
//	product <ts> <sku> <priceCents> <stock>
//	add <ts> <cart> <sku> <qty>
//	remove <ts> <cart> <sku> <qty>
//	total <ts> <cart>
//	items <ts> <cart>
//
// Add your own commands here as you build later levels.
package main

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"

	"shop"
)

func main() {
	s := shop.NewShop()
	sc := bufio.NewScanner(os.Stdin)
	for sc.Scan() {
		f := strings.Fields(sc.Text())
		if len(f) < 3 {
			continue
		}
		num := func(i int) int { n, _ := strconv.Atoi(f[i]); return n }
		ts := num(1)
		switch {
		case f[0] == "product" && len(f) == 5:
			fmt.Println(s.AddProduct(ts, f[2], num(3), num(4)))
		case f[0] == "add" && len(f) == 5:
			fmt.Println(s.AddToCart(ts, f[2], f[3], num(4)))
		case f[0] == "remove" && len(f) == 5:
			fmt.Println(s.RemoveFromCart(ts, f[2], f[3], num(4)))
		case f[0] == "total" && len(f) == 3:
			fmt.Println(s.CartTotal(ts, f[2]))
		case f[0] == "items" && len(f) == 3:
			fmt.Println("[" + strings.Join(s.Items(ts, f[2]), ", ") + "]")
		default:
			fmt.Println("unknown command:", sc.Text())
		}
	}
}
