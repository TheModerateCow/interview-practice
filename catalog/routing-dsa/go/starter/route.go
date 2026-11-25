package route

// Road connects junctions A and B in both directions. Driving it takes
// Minutes and uses Energy units of battery.
type Road struct{ A, B, Minutes, Energy int }

// FastestDelivery returns the fewest minutes for an electric van to drive
// from the depot (junction 0) to the customer (junction n-1), or -1 if it
// can't get there. The van starts with charge units (0 <= charge <= capacity).
// rate[i] is the minutes to add one unit at junction i; 0 means no charger.
func FastestDelivery(n, capacity, charge int, rate []int, roads []Road) int {
	panic("not implemented")
}
