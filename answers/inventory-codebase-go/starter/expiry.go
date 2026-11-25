package inventory

// holdQueue lists every reservation in the order it was placed.
type holdQueue []*Reservation

// track registers a newly placed reservation for expiry.
func (s *store) track(r *Reservation) { s.holds = append(s.holds, r) }

// expire ends every active reservation whose hold has run out by now (ExpiresAt <= now)
// and returns its stock to available.
func (s *store) expire(now int64) {
	for _, r := range s.holds {
		if r.Status == Active && r.ExpiresAt <= now {
			s.endHold(r, Expired, r.ExpiresAt)
		}
	}
}
