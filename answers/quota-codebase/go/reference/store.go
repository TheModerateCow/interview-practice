package quota

import "sort"

// Store keeps plans, keys and each key's request log in memory.
type Store struct {
	plans  map[string]Plan
	keys   map[string]Key
	events map[string][]Event // per key, oldest first
}

func newStore() *Store {
	return &Store{
		plans:  map[string]Plan{},
		keys:   map[string]Key{},
		events: map[string][]Event{},
	}
}

func (st *Store) plan(name string) (Plan, bool) {
	p, ok := st.plans[name]
	return p, ok
}

func (st *Store) addPlan(p Plan) { st.plans[p.Name] = p }

func (st *Store) key(id string) (Key, bool) {
	k, ok := st.keys[id]
	return k, ok
}

func (st *Store) addKey(k Key) { st.keys[k.ID] = k }

// setPlan moves a key to another plan.
func (st *Store) setPlan(id, plan string) {
	k := st.keys[id]
	k.Plan = plan
	st.keys[id] = k
}

func (st *Store) revoke(id string) {
	k := st.keys[id]
	k.Revoked = true
	st.keys[id] = k
}

// keysOf returns the ids of an organisation's keys, sorted.
func (st *Store) keysOf(org string) []string {
	var ids []string
	for id, k := range st.keys {
		if k.Org == org {
			ids = append(ids, id)
		}
	}
	sort.Strings(ids)
	return ids
}

// record appends a decision to the key's log. Requests for one key arrive in
// time order, so the log stays sorted by At.
func (st *Store) record(id string, e Event) {
	st.events[id] = append(st.events[id], e)
}

// eventsBetween returns the key's events with from <= At < to.
func (st *Store) eventsBetween(id string, from, to int64) []Event {
	log := st.events[id]
	i := sort.Search(len(log), func(i int) bool { return log[i].At >= from })
	j := sort.Search(len(log), func(j int) bool { return log[j].At >= to })
	return log[i:j]
}

// unitsBetween is the number of units the key spent with from <= At < to.
func (st *Store) unitsBetween(id string, from, to int64) int {
	n := 0
	for _, e := range st.eventsBetween(id, from, to) {
		if e.Allowed {
			n += e.Cost
		}
	}
	return n
}
