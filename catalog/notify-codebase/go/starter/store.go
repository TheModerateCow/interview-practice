package notify

// Store keeps users, the per-user notification log and the indexes the
// fan-out checks on every send, all in memory.
type Store struct {
	users  map[string]User
	seen   map[string]int64    // dedupeID -> At of the last accepted notification
	recent map[chanKey][]int64 // delivery times per user and channel, oldest first
	logs   map[string][]Record // per user, oldest first
}

type chanKey struct {
	user string
	ch   Channel
}

func newStore() *Store {
	return &Store{
		users:  map[string]User{},
		seen:   map[string]int64{},
		recent: map[chanKey][]int64{},
		logs:   map[string][]Record{},
	}
}

func (st *Store) user(id string) (User, bool) {
	u, ok := st.users[id]
	return u, ok
}

func (st *Store) putUser(u User) { st.users[u.ID] = u }

func (st *Store) setChannels(id string, chans []Channel) {
	u := st.users[id]
	u.Channels = chans
	st.users[id] = u
}

// dedupeID is the index key for a user's dedupe key.
func dedupeID(user, key string) string {
	return key
}

// lastAccepted returns when the user last had a non-duplicate notification
// with this dedupe key.
func (st *Store) lastAccepted(user, key string) (int64, bool) {
	at, ok := st.seen[dedupeID(user, key)]
	return at, ok
}

func (st *Store) accept(user, key string, at int64) { st.seen[dedupeID(user, key)] = at }

// deliveriesSince counts the user's deliveries on ch with At > since.
func (st *Store) deliveriesSince(user string, ch Channel, since int64) int {
	n := 0
	for _, r := range st.logs[user] {
		if r.At <= since {
			continue
		}
		for _, c := range r.Channels {
			if c == ch {
				n++
			}
		}
	}
	return n
}

func (st *Store) delivered(user string, ch Channel, at int64) {
	k := chanKey{user, ch}
	st.recent[k] = append(st.recent[k], at)
}

func (st *Store) record(r Record) { st.logs[r.User] = append(st.logs[r.User], r) }

// log returns the user's records, oldest first.
func (st *Store) log(user string) []Record { return st.logs[user] }
