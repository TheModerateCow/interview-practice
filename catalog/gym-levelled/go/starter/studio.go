// Package gym is the class booking desk of a gym.
package gym

// Studio holds every class. Timestamps (minutes) passed to its methods only ever increase.
type Studio struct {
	// your state here
}

// NewStudio returns an empty studio.
func NewStudio() *Studio {
	return &Studio{}
}

// AddClass schedules a class with capacity spots starting at start. False if the id exists, capacity <= 0 or start <= ts.
func (s *Studio) AddClass(ts int, classID string, start int, capacity int) bool {
	panic("not implemented")
}

// Book books one spot for member. False if the class is unknown, has started, is full or member already has a spot.
func (s *Studio) Book(ts int, classID string, member string) bool {
	panic("not implemented")
}

// Cancel gives up member's spot. False if the class is unknown, has started or member has no spot in it.
func (s *Studio) Cancel(ts int, classID string, member string) bool {
	panic("not implemented")
}

// SpotsLeft is the number of spots not yet booked, or -1 for an unknown class.
func (s *Studio) SpotsLeft(ts int, classID string) int {
	panic("not implemented")
}

// Upcoming lists the classes member has a spot in that haven't started: earliest start first, ties by id.
func (s *Studio) Upcoming(ts int, member string) []string {
	panic("not implemented")
}
