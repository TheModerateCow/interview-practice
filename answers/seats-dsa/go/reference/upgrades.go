package upgrades

import (
	"math"
	"sort"
)

// MaxUpgrades returns the most requests that can be upgraded at once: a request is upgraded
// only if every leg it flies still has a free seat. Requests are taken greedily by earliest
// alighting; a range-min tree with lazy range add tracks the free seats on each leg.
func MaxUpgrades(cap []int, requests [][]int) int {
	n := len(cap)
	byAlight := append([][]int(nil), requests...)
	sort.Slice(byAlight, func(i, j int) bool { return byAlight[i][1] < byAlight[j][1] })
	seats := newSeatTree(cap)
	upgraded := 0
	for _, r := range byAlight {
		lo, hi := r[0], r[1]-1
		if seats.min(1, 0, n-1, lo, hi) >= 1 {
			seats.add(1, 0, n-1, lo, hi, -1)
			upgraded++
		}
	}
	return upgraded
}

// seatTree: mn[x] includes lz[x] but not the lazies of x's ancestors.
type seatTree struct {
	mn, lz []int
}

func newSeatTree(cap []int) *seatTree {
	t := &seatTree{mn: make([]int, 4*len(cap)), lz: make([]int, 4*len(cap))}
	t.build(1, 0, len(cap)-1, cap)
	return t
}

func (t *seatTree) build(x, l, r int, cap []int) {
	if l == r {
		t.mn[x] = cap[l]
		return
	}
	m := (l + r) / 2
	t.build(2*x, l, m, cap)
	t.build(2*x+1, m+1, r, cap)
	t.mn[x] = min(t.mn[2*x], t.mn[2*x+1])
}

func (t *seatTree) min(x, l, r, lo, hi int) int {
	if hi < l || r < lo {
		return math.MaxInt
	}
	if lo <= l && r <= hi {
		return t.mn[x]
	}
	m := (l + r) / 2
	return t.lz[x] + min(t.min(2*x, l, m, lo, hi), t.min(2*x+1, m+1, r, lo, hi))
}

func (t *seatTree) add(x, l, r, lo, hi, v int) {
	if hi < l || r < lo {
		return
	}
	if lo <= l && r <= hi {
		t.mn[x] += v
		t.lz[x] += v
		return
	}
	m := (l + r) / 2
	t.add(2*x, l, m, lo, hi, v)
	t.add(2*x+1, m+1, r, lo, hi, v)
	t.mn[x] = t.lz[x] + min(t.mn[2*x], t.mn[2*x+1])
}
