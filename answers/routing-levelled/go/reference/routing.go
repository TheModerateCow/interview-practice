// Package routing is the in-memory routing core of a delivery company's road network.
package routing

import (
	"container/heap"
	"sort"
	"strconv"
)

type road struct {
	a, b            int // junction indexes
	minutes, energy int
	open            bool
}

// Network holds junctions and roads by id. Timestamps passed to its methods only ever increase.
type Network struct {
	index map[string]int // junction id -> index
	names []string       // index -> junction id
	at    [][]string     // index -> ids of the roads touching it
	rate  []int          // index -> minutes per unit at its charger, 0 = none
	roads map[string]*road
}

// NewNetwork returns an empty road network.
func NewNetwork() *Network {
	return &Network{index: map[string]int{}, roads: map[string]*road{}}
}

// Level 1

func (n *Network) AddJunction(ts int, id string) bool {
	if _, ok := n.index[id]; ok {
		return false
	}
	n.index[id] = len(n.names)
	n.names = append(n.names, id)
	n.at = append(n.at, nil)
	n.rate = append(n.rate, 0)
	return true
}

func (n *Network) AddRoad(ts int, id string, a string, b string, minutes int) bool {
	ia, okA := n.index[a]
	ib, okB := n.index[b]
	if _, taken := n.roads[id]; taken || !okA || !okB || a == b {
		return false
	}
	n.roads[id] = &road{a: ia, b: ib, minutes: minutes, open: true}
	n.at[ia] = append(n.at[ia], id)
	n.at[ib] = append(n.at[ib], id)
	return true
}

func (r *road) other(u int) int {
	if r.a == u {
		return r.b
	}
	return r.a
}

func (n *Network) RoadsAt(ts int, junction string) []string {
	out := []string{}
	u, ok := n.index[junction]
	if !ok {
		return out
	}
	ids := append([]string(nil), n.at[u]...)
	sort.Strings(ids)
	for _, id := range ids {
		r := n.roads[id]
		if r.open {
			out = append(out, id+":"+n.names[r.other(u)]+":"+strconv.Itoa(r.minutes))
		}
	}
	return out
}

// next calls f for every open road at u.
func (n *Network) next(u int, f func(v int, r *road)) {
	for _, id := range n.at[u] {
		r := n.roads[id]
		if r.open {
			f(r.other(u), r)
		}
	}
}

func (n *Network) component(start int) []bool {
	seen := make([]bool, len(n.names))
	seen[start] = true
	todo := []int{start}
	for len(todo) > 0 {
		u := todo[len(todo)-1]
		todo = todo[:len(todo)-1]
		n.next(u, func(v int, _ *road) {
			if !seen[v] {
				seen[v] = true
				todo = append(todo, v)
			}
		})
	}
	return seen
}

func (n *Network) Reachable(ts int, origin string, dest string) bool {
	o, ok1 := n.index[origin]
	d, ok2 := n.index[dest]
	if !ok1 || !ok2 {
		return false
	}
	return n.component(o)[d]
}

// Level 2

func (n *Network) CloseRoad(ts int, id string) bool {
	r, ok := n.roads[id]
	if !ok || !r.open {
		return false
	}
	r.open = false
	return true
}

func (n *Network) ReopenRoad(ts int, id string) bool {
	r, ok := n.roads[id]
	if !ok || r.open {
		return false
	}
	r.open = true
	return true
}

func (n *Network) ReachableFrom(ts int, junction string) []string {
	out := []string{}
	u, ok := n.index[junction]
	if !ok {
		return out
	}
	for v, in := range n.component(u) {
		if in {
			out = append(out, n.names[v])
		}
	}
	sort.Strings(out)
	return out
}

// Level 3

func (n *Network) SetMinutes(ts int, id string, minutes int) bool {
	r, ok := n.roads[id]
	if !ok {
		return false
	}
	r.minutes = minutes
	return true
}

type item struct{ d, s int } // time so far, state

type pq []item

func (h pq) Len() int            { return len(h) }
func (h pq) Less(i, j int) bool  { return h[i].d < h[j].d }
func (h pq) Swap(i, j int)       { h[i], h[j] = h[j], h[i] }
func (h *pq) Push(x interface{}) { *h = append(*h, x.(item)) }
func (h *pq) Pop() interface{} {
	old := *h
	x := old[len(old)-1]
	*h = old[:len(old)-1]
	return x
}

func (n *Network) FastestRoute(ts int, origin string, dest string) int {
	o, ok1 := n.index[origin]
	t, ok2 := n.index[dest]
	if !ok1 || !ok2 {
		return -1
	}
	best := make([]int, len(n.names))
	for i := range best {
		best[i] = -1
	}
	best[o] = 0
	h := &pq{{0, o}}
	for h.Len() > 0 {
		it := heap.Pop(h).(item)
		if it.d > best[it.s] {
			continue
		}
		if it.s == t {
			return it.d
		}
		n.next(it.s, func(v int, r *road) {
			nd := it.d + r.minutes
			if best[v] == -1 || nd < best[v] {
				best[v] = nd
				heap.Push(h, item{nd, v})
			}
		})
	}
	return -1
}

// Level 4

func (n *Network) AddCharger(ts int, junction string, rate int) bool {
	u, ok := n.index[junction]
	if !ok || n.rate[u] != 0 {
		return false
	}
	n.rate[u] = rate
	return true
}

func (n *Network) SetEnergy(ts int, id string, units int) bool {
	r, ok := n.roads[id]
	if !ok {
		return false
	}
	r.energy = units
	return true
}

// FastestDelivery: fewest minutes over (junction, units in the battery) states. Charging one unit is a move to the
// state with one unit more, so every partial charge is covered.
func (n *Network) FastestDelivery(ts int, origin string, dest string, capacity int, charge int) int {
	o, ok1 := n.index[origin]
	t, ok2 := n.index[dest]
	if !ok1 || !ok2 {
		return -1
	}
	w := capacity + 1
	best := make([]int, len(n.names)*w)
	for i := range best {
		best[i] = -1
	}
	push := func(h *pq, s, d int) {
		if best[s] == -1 || d < best[s] {
			best[s] = d
			heap.Push(h, item{d, s})
		}
	}
	h := &pq{}
	push(h, o*w+charge, 0)
	for h.Len() > 0 {
		it := heap.Pop(h).(item)
		if it.d > best[it.s] {
			continue
		}
		u, b := it.s/w, it.s%w
		if u == t {
			return it.d
		}
		if n.rate[u] > 0 && b < capacity {
			push(h, it.s+1, it.d+n.rate[u])
		}
		n.next(u, func(v int, r *road) {
			if r.energy <= b {
				push(h, v*w+b-r.energy, it.d+r.minutes)
			}
		})
	}
	return -1
}
