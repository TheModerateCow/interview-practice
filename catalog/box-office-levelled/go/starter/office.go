// Package tickets is the box office for a concert promoter.
package tickets

// Office holds every event. Timestamps passed to its methods only ever increase.
type Office struct {
	// your state here
}

// NewOffice returns an empty office.
func NewOffice() *Office {
	return &Office{}
}

// CreateEvent adds an event with capacity seats. False if the id exists or capacity <= 0.
func (o *Office) CreateEvent(ts int, eventID string, capacity int) bool {
	panic("not implemented")
}

// Buy gives buyer qty tickets. False if the event is unknown, qty <= 0 or fewer than qty seats are available.
func (o *Office) Buy(ts int, eventID, buyer string, qty int) bool {
	panic("not implemented")
}

// Refund returns qty of buyer's tickets to the event. False if the event is unknown, qty <= 0 or buyer owns fewer.
func (o *Office) Refund(ts int, eventID, buyer string, qty int) bool {
	panic("not implemented")
}

// Available is the number of seats that can still be bought, or -1 for an unknown event.
func (o *Office) Available(ts int, eventID string) int {
	panic("not implemented")
}
