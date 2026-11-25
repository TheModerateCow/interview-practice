// Drives the ledger from stdin, one command per line, and prints each result:
//
//	merchant <id> <bps> [<CUR>=<fixed fee> ...]
//	capture <ts> <charge> <merchant> <cur> <amount> <card|bank>
//	refund <ts> <charge> <amount>
//	settle <ts> <merchant>
//	post <ts> <account> <cur> <amount> [<account> <cur> <amount> ...]
//	payout <ts> <payout> <merchant> <cur> <amount>
//	paid <ts> <payout>
//	failed <ts> <payout>
//	balance <account> <cur>
//
// Amounts are integer minor units. Accounts are names like merchant:m1:available or
// platform:fees. Add your own commands as you need them.
package main

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"

	"ledger"
)

func main() {
	l := ledger.New()
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
		case f[0] == "merchant" && len(f) >= 3:
			p := ledger.Pricing{Bps: num(2), Fixed: map[string]int64{}}
			for _, kv := range f[3:] {
				cur, v, _ := strings.Cut(kv, "=")
				p.Fixed[cur], _ = strconv.ParseInt(v, 10, 64)
			}
			report(l.AddMerchant(f[1], p))
		case f[0] == "capture" && len(f) == 7:
			_, err := l.Capture(f[2], f[3], f[4], num(5), f[6], num(1))
			report(err)
		case f[0] == "refund" && len(f) == 4:
			report(l.Refund(f[2], num(3), num(1)))
		case f[0] == "settle" && len(f) == 3:
			bs, err := l.Settle(f[2], num(1))
			if err != nil {
				report(err)
			}
			for _, b := range bs {
				fmt.Printf("%s %s gross=%d fees=%d net=%d charges=%s\n",
					b.ID, b.Currency, b.Gross, b.Fees, b.Net, strings.Join(b.Charges, ","))
			}
		case f[0] == "post" && len(f) >= 5 && (len(f)-2)%3 == 0:
			e := ledger.Entry{TS: num(1)}
			for i := 2; i < len(f); i += 3 {
				e.Postings = append(e.Postings, ledger.Posting{Account: f[i], Currency: f[i+1], Amount: num(i + 2)})
			}
			_, err := l.Post(e)
			report(err)
		case f[0] == "payout" && len(f) == 6:
			_, err := l.RequestPayout(f[2], f[3], f[4], num(5), num(1))
			report(err)
		case f[0] == "paid" && len(f) == 3:
			report(l.PayoutPaid(f[2], num(1)))
		case f[0] == "failed" && len(f) == 3:
			report(l.PayoutFailed(f[2], num(1)))
		case f[0] == "balance" && len(f) == 3:
			fmt.Println(ledger.Format(l.Balance(f[1], f[2]), f[2]))
		default:
			fmt.Println("unknown command:", sc.Text())
		}
	}
}
