// Drives the bank from stdin, one command per line, and prints each result:
//
//	open <ts> <id>
//	deposit <ts> <id> <amount>          prints the new balance, or (failed)
//	withdraw <ts> <id> <amount>         prints the new balance, or (failed)
//	transfer <ts> <from> <to> <amount>  prints the sender's new balance, or (failed)
//	balance <ts> <id>                   prints the balance, or (none)
//
// Add your own commands as you build later levels.
package main

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"

	"bank"
)

// show prints an amount, or (failed) when the call was refused.
func show(v int, ok bool) {
	if ok {
		fmt.Println(v)
	} else {
		fmt.Println("(failed)")
	}
}

func main() {
	b := bank.NewBank()
	sc := bufio.NewScanner(os.Stdin)
	for sc.Scan() {
		f := strings.Fields(sc.Text())
		if len(f) < 2 {
			continue
		}
		ts, _ := strconv.Atoi(f[1])
		n, _ := strconv.Atoi(f[len(f)-1])
		switch {
		case f[0] == "open" && len(f) == 3:
			fmt.Println(b.OpenAccount(ts, f[2]))
		case f[0] == "deposit" && len(f) == 4:
			show(b.Deposit(ts, f[2], n))
		case f[0] == "withdraw" && len(f) == 4:
			show(b.Withdraw(ts, f[2], n))
		case f[0] == "transfer" && len(f) == 5:
			show(b.Transfer(ts, f[2], f[3], n))
		case f[0] == "balance" && len(f) == 3:
			if v, ok := b.Balance(ts, f[2]); ok {
				fmt.Println(v)
			} else {
				fmt.Println("(none)")
			}
		default:
			fmt.Println("unknown command:", sc.Text())
		}
	}
}
