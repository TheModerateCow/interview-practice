// Reads the number of events, then one event per line (add/cancel <price> <qty>, quote/buy <qty>),
// and prints RunBook's answers, one per line.
package main

import (
	"bufio"
	"fmt"
	"os"

	"book"
)

func main() {
	in := bufio.NewReader(os.Stdin)
	var m int
	fmt.Fscan(in, &m)
	events := make([]book.Event, 0, m)
	for i := 0; i < m; i++ {
		var kind string
		fmt.Fscan(in, &kind)
		if kind == "add" || kind == "cancel" {
			var price, qty int
			fmt.Fscan(in, &price, &qty)
			events = append(events, book.Event{Kind: kind, Price: price, Qty: qty})
		} else {
			var qty int
			fmt.Fscan(in, &qty)
			events = append(events, book.Event{Kind: kind, Qty: qty})
		}
	}
	for _, v := range book.RunBook(events) {
		fmt.Println(v)
	}
}
