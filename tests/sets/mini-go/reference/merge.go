package mini

import "sort"

// Interval is a closed range [Start, End].
type Interval struct{ Start, End int }

// Merge returns the union of the intervals as sorted, disjoint intervals.
// Intervals that overlap or touch (a.End == b.Start) are merged. The input is not modified.
func Merge(in []Interval) []Interval {
	if len(in) == 0 {
		return []Interval{}
	}
	s := append([]Interval(nil), in...)
	sort.Slice(s, func(i, j int) bool { return s[i].Start < s[j].Start })
	out := []Interval{s[0]}
	for _, v := range s[1:] {
		last := &out[len(out)-1]
		if v.Start <= last.End {
			if v.End > last.End {
				last.End = v.End
			}
		} else {
			out = append(out, v)
		}
	}
	return out
}
