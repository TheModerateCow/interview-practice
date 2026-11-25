package book

import "sort"

type Event struct {
	Kind  string
	Price int
	Qty   int
}

// RunBook replays ask-book events; returns one number per "quote" and "buy" event, in order.
func RunBook(events []Event) []int {
	seen := map[int]bool{}
	var prices []int
	for _, e := range events {
		if (e.Kind == "add" || e.Kind == "cancel") && !seen[e.Price] {
			seen[e.Price] = true
			prices = append(prices, e.Price)
		}
	}
	sort.Ints(prices)
	n := len(prices)
	level := make(map[int]int, n)
	for i, p := range prices {
		level[p] = i + 1
	}
	shares := make([]int, n+1)   // Fenwick tree: shares resting per level
	notional := make([]int, n+1) // Fenwick tree: price * shares per level
	resting := make([]int, n+1)  // plain shares per level
	top := 1
	for top <= n {
		top <<= 1
	}
	change := func(i, dq int) {
		resting[i] += dq
		dn := dq * prices[i-1]
		for j := i; j <= n; j += j & -j {
			shares[j] += dq
			notional[j] += dn
		}
	}
	// 0 < q <= total: the level holding the q-th cheapest share, the cost of
	// all shares on cheaper levels, and how many shares come from that level.
	sweep := func(q int) (int, int, int) {
		pos, got, cost := 0, 0, 0
		for step := top; step > 0; step >>= 1 {
			nxt := pos + step
			if nxt <= n && got+shares[nxt] < q {
				pos = nxt
				got += shares[nxt]
				cost += notional[nxt]
			}
		}
		return pos + 1, cost, q - got
	}

	total := 0
	out := []int{}
	for _, e := range events {
		switch e.Kind {
		case "add":
			change(level[e.Price], e.Qty)
			total += e.Qty
		case "cancel":
			change(level[e.Price], -e.Qty)
			total -= e.Qty
		case "quote":
			if e.Qty > total {
				out = append(out, -1)
			} else {
				k, cost, part := sweep(e.Qty)
				out = append(out, cost+part*prices[k-1])
			}
		default: // buy: fill what is there, the rest is cancelled
			q := min(e.Qty, total)
			if q == 0 {
				out = append(out, 0)
				continue
			}
			k, cost, part := sweep(q)
			out = append(out, cost+part*prices[k-1])
			for { // empty every cheaper level; each emptied level was paid for by an add
				j, _, _ := sweep(1)
				if j == k {
					break
				}
				change(j, -resting[j])
			}
			change(k, -part)
			total -= q
		}
	}
	return out
}
