// Package autocomplete is the autocomplete behind a site search box, built from the query log: popularity,
// suggestions, top-k lists and the fewest keystrokes to reach a query.
package autocomplete

import (
	"sort"
	"strconv"
	"strings"
)

type entry struct {
	count int
	query string
}

// before: more popular first, ties alphabetical.
func before(a, b entry) bool {
	if a.count != b.count {
		return a.count > b.count
	}
	return a.query < b.query
}

type node struct {
	kids map[byte]*node
	// every logged query under this prefix, best suggestion first
	ranked []entry
}

func newNode() *node { return &node{kids: map[byte]*node{}} }

func (n *node) remove(e entry) {
	i := sort.Search(len(n.ranked), func(i int) bool { return !before(n.ranked[i], e) })
	n.ranked = append(n.ranked[:i], n.ranked[i+1:]...)
}

func (n *node) insert(e entry) {
	i := sort.Search(len(n.ranked), func(i int) bool { return !before(n.ranked[i], e) })
	n.ranked = append(n.ranked, entry{})
	copy(n.ranked[i+1:], n.ranked[i:])
	n.ranked[i] = e
}

// SearchBox holds the query log, indexed by prefix.
type SearchBox struct {
	count map[string]int
	root  *node
}

// NewSearchBox returns a search box with an empty log.
func NewSearchBox() *SearchBox {
	return &SearchBox{count: map[string]int{}, root: newNode()}
}

func (s *SearchBox) path(query string) []*node {
	n := s.root
	out := []*node{n}
	for i := 0; i < len(query); i++ {
		next := n.kids[query[i]]
		if next == nil {
			next = newNode()
			n.kids[query[i]] = next
		}
		n = next
		out = append(out, n)
	}
	return out
}

func (s *SearchBox) find(prefix string) *node {
	n := s.root
	for i := 0; i < len(prefix) && n != nil; i++ {
		n = n.kids[prefix[i]]
	}
	return n
}

// set changes query's popularity to n (0 removes it) in every prefix's ranking.
func (s *SearchBox) set(query string, n int) {
	old := s.count[query]
	for _, nd := range s.path(query) {
		if old > 0 {
			nd.remove(entry{old, query})
		}
		if n > 0 {
			nd.insert(entry{n, query})
		}
	}
	if n > 0 {
		s.count[query] = n
	} else {
		delete(s.count, query)
	}
}

func (s *SearchBox) LogQuery(query string) int {
	n := s.count[query] + 1
	s.set(query, n)
	return n
}

func (s *SearchBox) Popularity(query string) int {
	return s.count[query]
}

func (s *SearchBox) Suggest(prefix string) (string, bool) {
	n := s.find(prefix)
	if n == nil || len(n.ranked) == 0 {
		return "", false
	}
	return n.ranked[0].query, true
}

// level 2

func (s *SearchBox) DeleteQuery(query string) bool {
	if _, ok := s.count[query]; !ok {
		return false
	}
	s.set(query, 0)
	return true
}

func (s *SearchBox) MergeQueries(from string, into string) (int, bool) {
	moved, ok := s.count[from]
	if !ok || from == into {
		return 0, false
	}
	s.set(from, 0)
	n := s.count[into] + moved
	s.set(into, n)
	return n, true
}

// level 3

func (s *SearchBox) ImportLog(log []string) int {
	// One batch: take the old entries out while every ranking is still sorted, append the new ones,
	// then sort each touched ranking once instead of inserting one by one.
	batch := map[string]int{}
	for _, q := range log {
		batch[q]++
	}
	for q := range batch {
		if old := s.count[q]; old > 0 {
			for _, nd := range s.path(q) {
				nd.remove(entry{old, q})
			}
		}
	}
	touched := map[*node]bool{}
	for q, c := range batch {
		n := s.count[q] + c
		s.count[q] = n
		for _, nd := range s.path(q) {
			nd.ranked = append(nd.ranked, entry{n, q})
			touched[nd] = true
		}
	}
	for nd := range touched {
		sort.Slice(nd.ranked, func(i, j int) bool { return before(nd.ranked[i], nd.ranked[j]) })
	}
	return len(s.count)
}

func (s *SearchBox) TopSuggestions(prefix string, k int) []string {
	out := []string{}
	n := s.find(prefix)
	if n == nil {
		return out
	}
	for i := 0; i < k && i < len(n.ranked); i++ {
		out = append(out, n.ranked[i].query+":"+strconv.Itoa(n.ranked[i].count))
	}
	return out
}

// level 4

func (s *SearchBox) FewestKeystrokes(target string) int {
	// Each keystroke costs 1: breadth-first over box texts. Only prefixes of logged queries
	// and of the target are worth visiting; any other text can only be backspaced away.
	dist := map[string]int{"": 0}
	todo := []string{""}
	for len(todo) > 0 {
		cur := todo[0]
		todo = todo[1:]
		d := dist[cur]
		if cur == target {
			return d
		}
		var nexts []string
		if cur != "" {
			nexts = append(nexts, cur[:len(cur)-1])
		}
		if n := s.find(cur); n != nil && len(n.ranked) > 0 {
			nexts = append(nexts, n.ranked[0].query) // Tab
			for ch, kid := range n.kids {
				if len(kid.ranked) > 0 {
					nexts = append(nexts, cur+string(ch))
				}
			}
		}
		if len(cur) < len(target) && strings.HasPrefix(target, cur) {
			nexts = append(nexts, target[:len(cur)+1])
		}
		for _, n := range nexts {
			if _, seen := dist[n]; !seen {
				dist[n] = d + 1
				todo = append(todo, n)
			}
		}
	}
	return -1
}
