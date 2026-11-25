// Drives the hotel from stdin, one command per line, and prints each result:
//
//	room <day> <room_id> <room_type> <rate>
//	book <day> <guest> <room_id> <check_in> <check_out>
//	cancel <day> <booking_id>
//	cost <day> <booking_id>
//
// A failed book prints an empty line. Add your own commands here as you build later levels.
package main

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"

	"hotel"
)

func main() {
	h := hotel.NewHotel()
	sc := bufio.NewScanner(os.Stdin)
	for sc.Scan() {
		f := strings.Fields(sc.Text())
		if len(f) < 3 {
			continue
		}
		num := func(i int) int { n, _ := strconv.Atoi(f[i]); return n }
		switch {
		case f[0] == "room" && len(f) == 5:
			fmt.Println(h.AddRoom(num(1), f[2], f[3], num(4)))
		case f[0] == "book" && len(f) == 6:
			fmt.Println(h.Book(num(1), f[2], f[3], num(4), num(5)))
		case f[0] == "cancel" && len(f) == 3:
			fmt.Println(h.Cancel(num(1), f[2]))
		case f[0] == "cost" && len(f) == 3:
			fmt.Println(h.Cost(num(1), f[2]))
		default:
			fmt.Println("unknown command:", sc.Text())
		}
	}
}
