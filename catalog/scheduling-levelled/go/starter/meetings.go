// Package meetings is the core of a team calendar's "find a time" feature.
package meetings

// TeamCalendar holds attendees by id. All times are minutes in UTC.
type TeamCalendar struct {
	// your state here
}

// NewTeamCalendar returns a calendar with no attendees.
func NewTeamCalendar() *TeamCalendar {
	panic("not implemented")
}

// AddAttendee adds an attendee. False if the id is taken.
func (t *TeamCalendar) AddAttendee(id string, offset int, workStart int, workEnd int) bool {
	panic("not implemented")
}

// AddBusy marks [start, end) busy for the attendee and returns the block's id.
func (t *TeamCalendar) AddBusy(id string, start int, end int) (string, bool) {
	panic("not implemented")
}

// RemoveBusy deletes one of the attendee's busy blocks.
func (t *TeamCalendar) RemoveBusy(id string, busyID string) bool {
	panic("not implemented")
}

// IsFree reports whether the attendee is working and not busy at that minute.
func (t *TeamCalendar) IsFree(id string, minute int) bool {
	panic("not implemented")
}
