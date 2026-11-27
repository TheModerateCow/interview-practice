// Package routing is the in-memory routing core of a delivery company's road network.
package routing

// Network holds junctions and roads by id. Timestamps passed to its methods only ever increase.
type Network struct {
	// your state here
}

// NewNetwork returns an empty road network.
func NewNetwork() *Network {
	return &Network{}
}

// AddJunction adds a junction. False if the id exists.
func (n *Network) AddJunction(ts int, id string) bool {
	panic("not implemented")
}

// AddRoad adds a two-way road between junctions a and b that takes minutes to drive.
func (n *Network) AddRoad(ts int, road string, a string, b string, minutes int) bool {
	panic("not implemented")
}

// RoadsAt lists the roads touching a junction as "road:other:minutes", by road id.
func (n *Network) RoadsAt(ts int, junction string) []string {
	panic("not implemented")
}

// Reachable reports whether a van can drive from origin to dest.
func (n *Network) Reachable(ts int, origin string, dest string) bool {
	panic("not implemented")
}
