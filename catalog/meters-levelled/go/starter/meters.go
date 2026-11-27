// Package meters is the in-memory core of a smart-meter platform's home-battery fleet.
package meters

// Fleet holds batteries by id and the published tariffs by day.
type Fleet struct {
	// your state here
}

// NewFleet returns a fleet with no batteries and no tariffs.
func NewFleet() *Fleet {
	return &Fleet{}
}

// AddBattery registers an empty battery. False if the id is already registered.
func (f *Fleet) AddBattery(id string, capacity int, wear int) bool {
	panic("not implemented")
}

// PublishTariff publishes a day's half-hourly prices. False if the day already has a tariff.
func (f *Fleet) PublishTariff(day int, prices []int) bool {
	panic("not implemented")
}

// Charge takes in 1 kWh during the slot and returns the kWh stored afterwards.
func (f *Fleet) Charge(id string, day int, slot int) (int, bool) {
	panic("not implemented")
}

// Discharge sends out 1 kWh during the slot and returns the kWh stored afterwards.
func (f *Fleet) Discharge(id string, day int, slot int) (int, bool) {
	panic("not implemented")
}

// Stored returns the energy the battery holds now.
func (f *Fleet) Stored(id string) (int, bool) {
	panic("not implemented")
}

// Cash returns everything the battery has earned minus everything it has paid.
func (f *Fleet) Cash(id string) (int, bool) {
	panic("not implemented")
}
