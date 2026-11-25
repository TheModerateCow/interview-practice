// Package configstore is an in-memory configuration store for a platform team.
package configstore

import (
	"sort"
	"strconv"
	"strings"
)

// entry is one field's value. expiresAt 0 means it never expires.
type entry struct {
	value     string
	expiresAt int
}

func (e entry) live(ts int) bool { return e.expiresAt == 0 || ts < e.expiresAt }

// saved is a field as a backup keeps it. remaining 0 means no TTL.
type saved struct {
	value     string
	remaining int
}

// change is one step in a field's history. deleted marks a removal.
type change struct {
	ts      int
	e       entry
	deleted bool
}

// Store holds records: a key maps to a set of named fields. Timestamps only ever increase.
type Store struct {
	records map[string]map[string]entry
	history map[string][]change                    // "key\x00field" -> changes in time order
	backups map[string]map[string]map[string]saved // backup id -> key -> field
}

// NewStore returns an empty store.
func NewStore() *Store {
	return &Store{records: map[string]map[string]entry{}, history: map[string][]change{}, backups: map[string]map[string]map[string]saved{}}
}

func (s *Store) lookup(ts int, key, field string) (entry, bool) {
	e, ok := s.records[key][field]
	if !ok || !e.live(ts) {
		return entry{}, false
	}
	return e, true
}

func (s *Store) put(ts int, key, field string, e entry) {
	if s.records[key] == nil {
		s.records[key] = map[string]entry{}
	}
	s.records[key][field] = e
	s.log(ts, key, field, change{ts: ts, e: e})
}

func (s *Store) remove(ts int, key, field string) {
	delete(s.records[key], field)
	if len(s.records[key]) == 0 {
		delete(s.records, key)
	}
	s.log(ts, key, field, change{ts: ts, deleted: true})
}

func (s *Store) log(ts int, key, field string, c change) {
	h := key + "\x00" + field
	s.history[h] = append(s.history[h], c)
}

// ---------------------------------------------------------------- level 1

// Set stores value in key's field, with no expiry. True if the field had no value before.
func (s *Store) Set(ts int, key, field, value string) bool {
	_, had := s.lookup(ts, key, field)
	s.put(ts, key, field, entry{value: value})
	return !had
}

// Get returns key's field and whether it has a value.
func (s *Store) Get(ts int, key, field string) (string, bool) {
	e, ok := s.lookup(ts, key, field)
	return e.value, ok
}

// Delete removes key's field. True if it had a value.
func (s *Store) Delete(ts int, key, field string) bool {
	if _, ok := s.lookup(ts, key, field); !ok {
		return false
	}
	s.remove(ts, key, field)
	return true
}

// CompareAndSet sets key's field to value only if it currently holds expected.
func (s *Store) CompareAndSet(ts int, key, field, expected, value string) bool {
	e, ok := s.lookup(ts, key, field)
	if !ok || e.value != expected {
		return false
	}
	e.value = value
	s.put(ts, key, field, e)
	return true
}

// ---------------------------------------------------------------- level 2

// Scan lists key's fields as "field=value", by field ascending.
func (s *Store) Scan(ts int, key string) []string {
	return s.ScanPrefix(ts, key, "")
}

// ScanPrefix is Scan limited to fields that start with prefix.
func (s *Store) ScanPrefix(ts int, key, prefix string) []string {
	fields := []string{}
	for f, e := range s.records[key] {
		if strings.HasPrefix(f, prefix) && e.live(ts) {
			fields = append(fields, f)
		}
	}
	sort.Strings(fields)
	out := make([]string, len(fields))
	for i, f := range fields {
		out[i] = f + "=" + s.records[key][f].value
	}
	return out
}

// ListKeys lists keys that start with prefix and hold at least one field, ascending.
func (s *Store) ListKeys(ts int, prefix string) []string {
	keys := []string{}
	for k := range s.records {
		if strings.HasPrefix(k, prefix) && len(s.ScanPrefix(ts, k, "")) > 0 {
			keys = append(keys, k)
		}
	}
	sort.Strings(keys)
	return keys
}

// ---------------------------------------------------------------- level 3

// SetWithTTL is Set, but the field expires at ts+ttl. ttl is always positive.
func (s *Store) SetWithTTL(ts int, key, field, value string, ttl int) bool {
	_, had := s.lookup(ts, key, field)
	s.put(ts, key, field, entry{value: value, expiresAt: ts + ttl})
	return !had
}

// RemainingTTL is the time left before key's field expires: 0 if it never expires, -1 if it has no value.
func (s *Store) RemainingTTL(ts int, key, field string) int {
	e, ok := s.lookup(ts, key, field)
	if !ok {
		return -1
	}
	if e.expiresAt == 0 {
		return 0
	}
	return e.expiresAt - ts
}

// ---------------------------------------------------------------- level 4

// Backup saves every field that has a value now, with its remaining TTL. Returns "b1", "b2", ...
func (s *Store) Backup(ts int) string {
	b := map[string]map[string]saved{}
	for k, fields := range s.records {
		for f, e := range fields {
			if !e.live(ts) {
				continue
			}
			if b[k] == nil {
				b[k] = map[string]saved{}
			}
			sv := saved{value: e.value}
			if e.expiresAt != 0 {
				sv.remaining = e.expiresAt - ts
			}
			b[k][f] = sv
		}
	}
	id := "b" + strconv.Itoa(len(s.backups)+1)
	s.backups[id] = b
	return id
}

// Restore replaces the whole store with a backup. TTLs restart from ts with the time they had left.
func (s *Store) Restore(ts int, backupID string) bool {
	b, ok := s.backups[backupID]
	if !ok {
		return false
	}
	for k, fields := range s.records {
		for f := range fields {
			if _, kept := b[k][f]; !kept {
				s.remove(ts, k, f)
			}
		}
	}
	for k, fields := range b {
		for f, sv := range fields {
			e := entry{value: sv.value}
			if sv.remaining != 0 {
				e.expiresAt = ts + sv.remaining
			}
			s.put(ts, k, f, e)
		}
	}
	return true
}

// GetAt is what Get would have returned at time atTs (atTs <= ts).
func (s *Store) GetAt(ts int, key, field string, atTs int) (string, bool) {
	var last *change
	for i, c := range s.history[key+"\x00"+field] {
		if c.ts <= atTs {
			last = &s.history[key+"\x00"+field][i]
		}
	}
	if last == nil || last.deleted || !last.e.live(atTs) {
		return "", false
	}
	return last.e.value, true
}
