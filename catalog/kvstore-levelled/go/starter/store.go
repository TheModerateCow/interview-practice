// Package configstore is an in-memory configuration store for a platform team.
package configstore

// Store holds records: a key maps to a set of named fields. Timestamps passed to its methods only ever increase.
type Store struct {
	// your state here
}

// NewStore returns an empty store.
func NewStore() *Store {
	return &Store{}
}

// Set stores value in key's field. True if the field had no value before.
func (s *Store) Set(ts int, key, field, value string) bool {
	panic("not implemented")
}

// Get returns key's field and whether it has a value.
func (s *Store) Get(ts int, key, field string) (string, bool) {
	panic("not implemented")
}

// Delete removes key's field. True if it had a value.
func (s *Store) Delete(ts int, key, field string) bool {
	panic("not implemented")
}

// CompareAndSet sets key's field to value only if it currently holds expected.
func (s *Store) CompareAndSet(ts int, key, field, expected, value string) bool {
	panic("not implemented")
}
