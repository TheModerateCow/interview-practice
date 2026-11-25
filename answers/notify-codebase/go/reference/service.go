package notify

// Service is the notification fan-out for one region.
type Service struct {
	store *Store
}

// New returns an empty service.
func New() *Service {
	return &Service{store: newStore()}
}

// AddUser registers a user at a fixed UTC offset. New users get email only
// and no quiet hours.
func (s *Service) AddUser(id string, offsetMin int) error {
	if offsetMin < -720 || offsetMin > 840 {
		return ErrBadOffset
	}
	if _, ok := s.store.user(id); ok {
		return ErrDuplicateUser
	}
	s.store.putUser(User{ID: id, OffsetMin: offsetMin, Channels: []Channel{Email}})
	return nil
}

// User returns a user's current settings.
func (s *Service) User(id string) (User, error) {
	u, ok := s.store.user(id)
	if !ok {
		return User{}, ErrUnknownUser
	}
	return u, nil
}

// SetChannels replaces the user's enabled channels. An empty list means
// everything goes to the digest.
func (s *Service) SetChannels(id string, chans []Channel) error {
	if _, ok := s.store.user(id); !ok {
		return ErrUnknownUser
	}
	seen := map[Channel]bool{}
	for _, ch := range chans {
		if _, known := hourlyCap[ch]; !known || seen[ch] {
			return ErrBadChannel
		}
		seen[ch] = true
	}
	s.store.setChannels(id, chans)
	return nil
}

// SetQuietHours sets the local hours [from, to) during which only urgent
// notifications go out. from == to turns quiet hours off.
func (s *Service) SetQuietHours(id string, from, to int) error {
	u, ok := s.store.user(id)
	if !ok {
		return ErrUnknownUser
	}
	if from < 0 || from > 23 || to < 0 || to > 23 {
		return ErrBadQuietHours
	}
	u.QuietFrom, u.QuietTo = from, to
	s.store.putUser(u)
	return nil
}

// Send fans one notification out to the user's channels and logs the result.
// Sends for one user must come in time order.
func (s *Service) Send(n Notification) (Result, error) {
	u, ok := s.store.user(n.User)
	if !ok {
		return Result{}, ErrUnknownUser
	}
	if n.Topic == "" || n.Key == "" {
		return Result{}, ErrBadNotification
	}
	if last, ok := s.store.lastAccepted(n.User, n.Key); ok && n.At-last < DedupeWindow {
		res := Result{Status: Duplicate}
		s.store.record(Record{n, res})
		return res, nil
	}
	s.store.accept(n.User, n.Key, n.At)
	res := Result{Status: Held}
	if n.Urgent || !inQuietHours(u, n.At) {
		for _, ch := range u.Channels {
			if s.store.deliveriesSince(n.User, ch, n.At-capWindow) < hourlyCap[ch] {
				s.store.delivered(n.User, ch, n.At)
				res.Channels = append(res.Channels, ch)
			}
		}
		if len(res.Channels) > 0 {
			res.Status = Sent
		}
	}
	s.store.record(Record{n, res})
	return res, nil
}
