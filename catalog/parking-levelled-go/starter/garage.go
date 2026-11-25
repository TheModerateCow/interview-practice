// Package parking runs a multi-storey parking garage.
package parking

// Garage holds every spot. Timestamps passed to its methods only ever increase.
type Garage struct {
	// your state here
}

// NewGarage returns an empty garage.
func NewGarage() *Garage {
	return &Garage{}
}

// AddSpot adds a spot. False if the id exists or size isn't small, medium or large.
func (g *Garage) AddSpot(ts int, spotID, size string) bool {
	panic("not implemented")
}

// Park puts the vehicle in the smallest free spot that fits it (lowest id on ties) and returns
// the spot id, or "" if the size is invalid, the plate is already parked or nothing fits.
func (g *Garage) Park(ts int, plate, size string) string {
	panic("not implemented")
}

// Leave frees the plate's spot. False if the plate isn't parked.
func (g *Garage) Leave(ts int, plate string) bool {
	panic("not implemented")
}

// SpotOf is the spot the plate is parked in, or "".
func (g *Garage) SpotOf(ts int, plate string) string {
	panic("not implemented")
}
