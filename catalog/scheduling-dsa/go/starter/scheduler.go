package scheduler

type Attendee struct {
	Offset    int
	WorkStart int
	WorkEnd   int
	Busy      [][]int
}

func EarliestQuorumSlot(attendees []Attendee, days int, duration int, quorum int) int {
	panic("not implemented")
}
