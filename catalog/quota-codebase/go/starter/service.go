package quota

// Service is the quota service for one gateway region.
type Service struct {
	store *Store
}

// New returns an empty service with no plans or keys.
func New() *Service {
	return &Service{store: newStore()}
}

// AddPlan registers a pricing tier.
func (s *Service) AddPlan(p Plan) error {
	if p.Limit <= 0 || p.Window <= 0 || p.Burst < 0 {
		return ErrInvalidPlan
	}
	if _, ok := s.store.plan(p.Name); ok {
		return ErrDuplicatePlan
	}
	s.store.addPlan(p)
	return nil
}

// IssueKey creates an API key for org on the named plan.
func (s *Service) IssueKey(id, org, plan string) error {
	if _, ok := s.store.plan(plan); !ok {
		return ErrUnknownPlan
	}
	if _, ok := s.store.key(id); ok {
		return ErrDuplicateKey
	}
	s.store.addKey(Key{ID: id, Org: org, Plan: plan})
	return nil
}

// Key returns a key's current record.
func (s *Service) Key(id string) (Key, error) {
	k, ok := s.store.key(id)
	if !ok {
		return Key{}, ErrUnknownKey
	}
	return k, nil
}

// Revoke disables a key for good. Its usage stays in the log.
func (s *Service) Revoke(id string) error {
	if _, ok := s.store.key(id); !ok {
		return ErrUnknownKey
	}
	s.store.revoke(id)
	return nil
}

// ChangePlan moves a key to another plan; the new limit applies from the
// next request on.
func (s *Service) ChangePlan(id, plan string) error {
	if _, ok := s.store.key(id); !ok {
		return ErrUnknownKey
	}
	if _, ok := s.store.plan(plan); !ok {
		return ErrUnknownPlan
	}
	s.store.setPlan(id, plan)
	return nil
}

// Allow decides whether a request costing cost units, made at now, fits the
// key's plan, and logs the decision. A denied request spends nothing.
func (s *Service) Allow(id string, now int64, cost int) (Decision, error) {
	k, ok := s.store.key(id)
	if !ok {
		return Decision{}, ErrUnknownKey
	}
	if k.Revoked {
		return Decision{}, ErrRevoked
	}
	if cost <= 0 {
		return Decision{}, ErrBadCost
	}
	p, _ := s.store.plan(k.Plan)
	used, limit := s.window(id, p, now)
	if used+cost > limit {
		s.store.record(id, Event{At: now, Cost: cost})
		return Decision{Remaining: limit - used, RetryAfter: resetIn(now, p.Window)}, nil
	}
	s.store.record(id, Event{At: now, Cost: cost, Allowed: true})
	return Decision{Allowed: true, Remaining: limit - used - cost}, nil
}

// Usage reports what the key has spent in the window containing now and how
// much it may spend there in total.
func (s *Service) Usage(id string, now int64) (used, limit int, err error) {
	k, ok := s.store.key(id)
	if !ok {
		return 0, 0, ErrUnknownKey
	}
	p, _ := s.store.plan(k.Plan)
	used, limit = s.window(id, p, now)
	return used, limit, nil
}

// window returns the units a key has spent in the window containing now, and
// that window's capacity.
func (s *Service) window(id string, p Plan, now int64) (used, limit int) {
	start := windowStart(now, p.Window)
	used = s.store.unitsBetween(id, start, start+p.Window)
	prev := s.store.unitsBetween(id, start-p.Window, start)
	return used, capacity(p, prev)
}
