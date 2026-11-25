package route

import "container/heap"

// Road connects junctions A and B in both directions. Driving it takes
// Minutes and uses Energy units of battery.
type Road struct{ A, B, Minutes, Energy int }

// FastestDelivery returns the fewest minutes for an electric van to drive
// from the depot (junction 0) to the customer (junction n-1), or -1 if it
// can't get there. The van starts with charge units (0 <= charge <= capacity).
// rate[i] is the minutes to add one unit at junction i; 0 means no charger.
func FastestDelivery(n, capacity, charge int, rate []int, roads []Road) int {
	adj := make([][]Road, n)
	for _, r := range roads {
		adj[r.A] = append(adj[r.A], r)
		adj[r.B] = append(adj[r.B], Road{r.B, r.A, r.Minutes, r.Energy})
	}
	// State (junction, battery); charging one unit at a time keeps the
	// graph at n*(capacity+1) states and covers every partial charge.
	w := capacity + 1
	dist := make([]int, n*w)
	for i := range dist {
		dist[i] = -1
	}
	pq := &minHeap{}
	push := func(u, b, d int) {
		if s := u*w + b; dist[s] == -1 || d < dist[s] {
			dist[s] = d
			heap.Push(pq, item{d, s})
		}
	}
	push(0, charge, 0)
	for pq.Len() > 0 {
		it := heap.Pop(pq).(item)
		if it.d != dist[it.s] {
			continue
		}
		u, b := it.s/w, it.s%w
		if u == n-1 {
			return it.d
		}
		if rate[u] > 0 && b < capacity {
			push(u, b+1, it.d+rate[u])
		}
		for _, r := range adj[u] {
			if nb := b - r.Energy; nb >= 0 {
				push(r.B, nb, it.d+r.Minutes)
			}
		}
	}
	return -1
}

type item struct{ d, s int }

type minHeap []item

func (h minHeap) Len() int           { return len(h) }
func (h minHeap) Less(i, j int) bool { return h[i].d < h[j].d }
func (h minHeap) Swap(i, j int)      { h[i], h[j] = h[j], h[i] }
func (h *minHeap) Push(x any)        { *h = append(*h, x.(item)) }
func (h *minHeap) Pop() any {
	old := *h
	x := old[len(old)-1]
	*h = old[:len(old)-1]
	return x
}
