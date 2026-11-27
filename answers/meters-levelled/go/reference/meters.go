// Package meters is the in-memory core of a smart-meter platform's home-battery fleet: tariffs, recorded actions,
// daily reports and best-schedule planning.
package meters

import (
	"fmt"
	"sort"
)

type dayLog struct {
	profit, discharged int
}

type battery struct {
	capacity, wear  int
	stored, cash    int
	acted           bool
	lastDay, lastSl int // day and slot of the latest recorded action, when acted
	days            map[int]*dayLog
	limit           int // kWh it may discharge per day; -1 = no limit
}

// Fleet holds batteries by id and the published tariffs by day.
type Fleet struct {
	batteries map[string]*battery
	tariffs   map[int][]int
}

// NewFleet returns a fleet with no batteries and no tariffs.
func NewFleet() *Fleet {
	return &Fleet{batteries: map[string]*battery{}, tariffs: map[int][]int{}}
}

func (f *Fleet) AddBattery(id string, capacity int, wear int) bool {
	if _, ok := f.batteries[id]; ok {
		return false
	}
	f.batteries[id] = &battery{capacity: capacity, wear: wear, days: map[int]*dayLog{}, limit: -1}
	return true
}

func (f *Fleet) PublishTariff(day int, prices []int) bool {
	if _, ok := f.tariffs[day]; ok {
		return false
	}
	f.tariffs[day] = append([]int(nil), prices...)
	return true
}

func (f *Fleet) act(id string, day, slot int, charging bool) (int, bool) {
	b, ok := f.batteries[id]
	prices, ok2 := f.tariffs[day]
	if !ok || !ok2 || slot < 0 || slot >= len(prices) {
		return 0, false
	}
	if b.acted && (day < b.lastDay || day == b.lastDay && slot <= b.lastSl) {
		return 0, false
	}
	d := b.days[day]
	if d == nil {
		d = &dayLog{}
	}
	var gain int
	if charging {
		if b.stored >= b.capacity {
			return 0, false
		}
		b.stored++
		gain = -prices[slot]
	} else {
		if b.stored == 0 || (b.limit >= 0 && d.discharged >= b.limit) {
			return 0, false
		}
		b.stored--
		d.discharged++
		gain = prices[slot] - b.wear
	}
	b.cash += gain
	d.profit += gain
	b.days[day] = d
	b.acted, b.lastDay, b.lastSl = true, day, slot
	return b.stored, true
}

func (f *Fleet) Charge(id string, day int, slot int) (int, bool) { return f.act(id, day, slot, true) }

func (f *Fleet) Discharge(id string, day int, slot int) (int, bool) { return f.act(id, day, slot, false) }

func (f *Fleet) Stored(id string) (int, bool) {
	b, ok := f.batteries[id]
	if !ok {
		return 0, false
	}
	return b.stored, true
}

func (f *Fleet) Cash(id string) (int, bool) {
	b, ok := f.batteries[id]
	if !ok {
		return 0, false
	}
	return b.cash, true
}

func (f *Fleet) DayProfit(id string, day int) (int, bool) {
	b, ok := f.batteries[id]
	if !ok {
		return 0, false
	}
	if d := b.days[day]; d != nil {
		return d.profit, true
	}
	return 0, true
}

func (f *Fleet) TopEarners(day int, n int) []string {
	ids := make([]string, 0, len(f.batteries))
	profit := map[string]int{}
	for id := range f.batteries {
		ids = append(ids, id)
		profit[id], _ = f.DayProfit(id, day)
	}
	sort.Slice(ids, func(i, j int) bool {
		if profit[ids[i]] != profit[ids[j]] {
			return profit[ids[i]] > profit[ids[j]]
		}
		return ids[i] < ids[j]
	})
	if n < len(ids) {
		ids = ids[:n]
	}
	out := []string{}
	for _, id := range ids {
		out = append(out, fmt.Sprintf("%s:%d", id, profit[id]))
	}
	return out
}

func (f *Fleet) BestProfit(id string, day int) (int, bool) {
	b, ok := f.batteries[id]
	prices, ok2 := f.tariffs[day]
	if !ok || !ok2 {
		return 0, false
	}
	n := len(prices)
	capacity := min(b.capacity, n)
	lim := n
	if b.limit >= 0 {
		lim = min(b.limit, n)
	}
	const unreached = -1 << 60
	// best[u][c]: most cash so far holding c kWh after u kWh discharged today.
	grid := func() [][]int {
		g := make([][]int, lim+1)
		for u := range g {
			g[u] = make([]int, capacity+1)
			for c := range g[u] {
				g[u][c] = unreached
			}
		}
		return g
	}
	best := grid()
	best[0][0] = 0
	for _, p := range prices {
		nxt := grid()
		for u := 0; u <= lim; u++ {
			copy(nxt[u], best[u]) // idle
		}
		for u := 0; u <= lim; u++ {
			for c := 0; c <= capacity; c++ {
				v := best[u][c]
				if v == unreached {
					continue
				}
				if c < capacity && v-p > nxt[u][c+1] {
					nxt[u][c+1] = v - p
				}
				if c > 0 && u < lim && v+p-b.wear > nxt[u+1][c-1] {
					nxt[u+1][c-1] = v + p - b.wear
				}
			}
		}
		best = nxt
	}
	out := 0
	for _, row := range best {
		for _, v := range row {
			out = max(out, v)
		}
	}
	return out, true
}

func (f *Fleet) SetDischargeLimit(id string, kwh int) bool {
	b, ok := f.batteries[id]
	if !ok {
		return false
	}
	b.limit = kwh
	return true
}
