// Drives the library from stdin, one command per line, and prints each result
// (strings are printed quoted, so an empty result shows as ""; titles are one word here):
//
//	member <ts> <member>
//	copy <ts> <copy> <title>
//	checkout <ts> <member> <title>
//	return <ts> <copy>
//	borrower <ts> <copy>
//
// Add your own commands here as you build later levels.
package main

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"

	"library"
)

func main() {
	lib := library.NewLibrary()
	sc := bufio.NewScanner(os.Stdin)
	for sc.Scan() {
		f := strings.Fields(sc.Text())
		if len(f) < 3 {
			continue
		}
		ts, _ := strconv.Atoi(f[1])
		switch {
		case f[0] == "member" && len(f) == 3:
			fmt.Println(lib.AddMember(ts, f[2]))
		case f[0] == "copy" && len(f) == 4:
			fmt.Println(lib.AddCopy(ts, f[2], f[3]))
		case f[0] == "checkout" && len(f) == 4:
			fmt.Printf("%q\n", lib.Checkout(ts, f[2], f[3]))
		case f[0] == "return" && len(f) == 3:
			fmt.Println(lib.ReturnCopy(ts, f[2]))
		case f[0] == "borrower" && len(f) == 3:
			fmt.Printf("%q\n", lib.Borrower(ts, f[2]))
		default:
			fmt.Println("unknown command:", sc.Text())
		}
	}
}
