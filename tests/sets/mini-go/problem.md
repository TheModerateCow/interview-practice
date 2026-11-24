# Merge intervals

In `merge.go`, implement `Merge(in []Interval) []Interval`: return the union of closed integer intervals as sorted,
disjoint intervals. Intervals that overlap **or touch** (`[1,3]` and `[3,5]`) merge. Do not modify the input slice.
Empty input gives an empty (non-nil) slice.

`cmd/run/main.go` reads `start end` lines from stdin and prints the merged intervals, one per line.
