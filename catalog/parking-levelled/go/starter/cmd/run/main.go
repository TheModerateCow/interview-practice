// Drives the garage from stdin, one command per line, and prints each result
// (strings are printed quoted, so an empty result shows as ""):
//
//	add <ts> <spot> <size>
//	park <ts> <plate> <size>
//	leave <ts> <plate>
//	spot <ts> <plate>
//
// Add your own commands here as you build later levels.
package main

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"

	"parking"
)

func main() {
	g := parking.NewGarage()
	sc := bufio.NewScanner(os.Stdin)
	for sc.Scan() {
		f := strings.Fields(sc.Text())
		if len(f) < 3 {
			continue
		}
		ts, _ := strconv.Atoi(f[1])
		switch {
		case f[0] == "add" && len(f) == 4:
			fmt.Println(g.AddSpot(ts, f[2], f[3]))
		case f[0] == "park" && len(f) == 4:
			fmt.Printf("%q\n", g.Park(ts, f[2], f[3]))
		case f[0] == "leave" && len(f) == 3:
			fmt.Println(g.Leave(ts, f[2]))
		case f[0] == "spot" && len(f) == 3:
			fmt.Printf("%q\n", g.SpotOf(ts, f[2]))
		default:
			fmt.Println("unknown command:", sc.Text())
		}
	}
}
