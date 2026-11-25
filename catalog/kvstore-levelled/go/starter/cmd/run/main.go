// Drives the store from stdin, one command per line, and prints each result:
//
//	set <ts> <key> <field> <value>
//	get <ts> <key> <field>                 prints the value, or (none)
//	delete <ts> <key> <field>
//	cas <ts> <key> <field> <expected> <value>
//
// Values are single words here. Add your own commands as you build later levels.
package main

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"

	"configstore"
)

func main() {
	s := configstore.NewStore()
	sc := bufio.NewScanner(os.Stdin)
	for sc.Scan() {
		f := strings.Fields(sc.Text())
		if len(f) < 2 {
			continue
		}
		ts, _ := strconv.Atoi(f[1])
		switch {
		case f[0] == "set" && len(f) == 5:
			fmt.Println(s.Set(ts, f[2], f[3], f[4]))
		case f[0] == "get" && len(f) == 4:
			if v, ok := s.Get(ts, f[2], f[3]); ok {
				fmt.Println(v)
			} else {
				fmt.Println("(none)")
			}
		case f[0] == "delete" && len(f) == 4:
			fmt.Println(s.Delete(ts, f[2], f[3]))
		case f[0] == "cas" && len(f) == 6:
			fmt.Println(s.CompareAndSet(ts, f[2], f[3], f[4], f[5]))
		default:
			fmt.Println("unknown command:", sc.Text())
		}
	}
}
