package dispatch

import "sort"

// MinDispatchRadius returns the smallest radius R >= 0 such that at least need riders can
// each be picked up by a different driver standing within distance R of them, or -1 if
// that is impossible.
func MinDispatchRadius(riders, drivers []int, need int) int {
	if need <= 0 {
		return 0
	}
	if need > len(riders) || need > len(drivers) {
		return -1
	}
	r, d := sortedCopy(riders), sortedCopy(drivers)
	lo, hi := 0, max(r[len(r)-1], d[len(d)-1])-min(r[0], d[0])
	for lo < hi {
		mid := lo + (hi-lo)/2
		if matched(r, d, mid) >= need {
			hi = mid
		} else {
			lo = mid + 1
		}
	}
	return lo
}

func sortedCopy(a []int) []int {
	s := append([]int(nil), a...)
	sort.Ints(s)
	return s
}

// matched is the most riders served when every pickup is within radius. Both slices are
// sorted; each rider takes the leftmost free driver in reach.
func matched(r, d []int, radius int) int {
	count, j := 0, 0
	for _, x := range r {
		for j < len(d) && d[j] < x-radius {
			j++
		}
		if j == len(d) {
			break
		}
		if d[j] <= x+radius {
			count++
			j++
		}
	}
	return count
}
