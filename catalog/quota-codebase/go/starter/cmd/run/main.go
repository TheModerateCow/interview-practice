// Drives the quota service from stdin, one command per line, and prints each
// result (or "error: ..."):
//
//	plan <name> <limit> <windowSeconds> <burst>
//	key <id> <org> <plan>
//	allow <key> <now> <cost>     prints "allowed <remaining>" or "denied <remaining> retry <seconds>"
//	usage <key> <now>            prints "<used>/<limit>"
//	revoke <key>
//	setplan <key> <plan>
//	report <org> <from> <to>     prints one "<key> <plan> <requests> <units> <denied>" line per key
//
// Add your own commands here if they help.
package main

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"

	"quota"
)

func main() {
	s := quota.New()
	sc := bufio.NewScanner(os.Stdin)
	for sc.Scan() {
		f := strings.Fields(sc.Text())
		if len(f) == 0 {
			continue
		}
		num := func(i int) int64 { n, _ := strconv.ParseInt(f[i], 10, 64); return n }
		switch {
		case f[0] == "plan" && len(f) == 5:
			report("ok", s.AddPlan(quota.Plan{Name: f[1], Limit: int(num(2)), Window: num(3), Burst: int(num(4))}))
		case f[0] == "key" && len(f) == 4:
			report("ok", s.IssueKey(f[1], f[2], f[3]))
		case f[0] == "allow" && len(f) == 4:
			d, err := s.Allow(f[1], num(2), int(num(3)))
			if d.Allowed {
				report(fmt.Sprintf("allowed %d", d.Remaining), err)
			} else {
				report(fmt.Sprintf("denied %d retry %d", d.Remaining, d.RetryAfter), err)
			}
		case f[0] == "usage" && len(f) == 3:
			used, limit, err := s.Usage(f[1], num(2))
			report(fmt.Sprintf("%d/%d", used, limit), err)
		case f[0] == "revoke" && len(f) == 2:
			report("ok", s.Revoke(f[1]))
		case f[0] == "setplan" && len(f) == 3:
			report("ok", s.ChangePlan(f[1], f[2]))
		case f[0] == "report" && len(f) == 4:
			lines, err := s.Report(f[1], num(2), num(3))
			if err != nil {
				report("", err)
				continue
			}
			for _, l := range lines {
				fmt.Println(l.KeyID, l.Plan, l.Requests, l.Units, l.Denied)
			}
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
