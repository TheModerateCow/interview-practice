package meters

import (
	"math"
	"slices"
)

// BestBatteryProfit returns the most money the battery can make over the day: it starts empty, holds
// up to capacity kWh, and each half-hour charges 1 kWh (paying the price), discharges 1 kWh (earning
// the price minus wear) or idles. Energy left at the end is worth nothing.
func BestBatteryProfit(prices []int, capacity, wear int) int {
	// best[c] = most money made so far while holding c kWh. Levels above 0 start unreachable.
	const unreachable = math.MinInt / 2
	best := make([]int, capacity+1)
	for c := 1; c <= capacity; c++ {
		best[c] = unreachable
	}
	next := make([]int, capacity+1)
	for _, p := range prices {
		for c := 0; c <= capacity; c++ {
			v := best[c]
			if c > 0 {
				v = max(v, best[c-1]-p)
			}
			if c < capacity {
				v = max(v, best[c+1]+p-wear)
			}
			next[c] = v
		}
		best, next = next, best
	}
	return slices.Max(best)
}
