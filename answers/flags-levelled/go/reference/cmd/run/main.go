// Drives the flag service from stdin, one command per line, and prints each result:
//
//	create <ts> <flag>
//	set <ts> <flag> <env> on|off
//	target <ts> <flag> <env> <user>
//	untarget <ts> <flag> <env> <user>
//	check <ts> <flag> <env> <user>
//
// Add your own commands here as you build later levels.
package main

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"

	"flags"
)

func main() {
	svc := flags.NewFlagService()
	sc := bufio.NewScanner(os.Stdin)
	for sc.Scan() {
		f := strings.Fields(sc.Text())
		if len(f) < 3 {
			continue
		}
		ts, _ := strconv.Atoi(f[1])
		switch {
		case f[0] == "create" && len(f) == 3:
			fmt.Println(svc.CreateFlag(ts, f[2]))
		case f[0] == "set" && len(f) == 5:
			fmt.Println(svc.SetEnabled(ts, f[2], f[3], f[4] == "on"))
		case f[0] == "target" && len(f) == 5:
			fmt.Println(svc.AddTarget(ts, f[2], f[3], f[4]))
		case f[0] == "untarget" && len(f) == 5:
			fmt.Println(svc.RemoveTarget(ts, f[2], f[3], f[4]))
		case f[0] == "check" && len(f) == 5:
			fmt.Println(svc.IsEnabled(ts, f[2], f[3], f[4]))
		default:
			fmt.Println("unknown command:", sc.Text())
		}
	}
}
