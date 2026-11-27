// Package autocomplete is the autocomplete behind a site search box.
package autocomplete

// SearchBox holds the query log.
type SearchBox struct {
	// your state here
}

// NewSearchBox returns a search box with an empty log.
func NewSearchBox() *SearchBox {
	panic("not implemented")
}

// LogQuery records one search and returns the query's new popularity.
func (s *SearchBox) LogQuery(query string) int {
	panic("not implemented")
}

// Popularity returns how many times the query has been logged.
func (s *SearchBox) Popularity(query string) int {
	panic("not implemented")
}

// Suggest returns the most popular logged query starting with prefix.
func (s *SearchBox) Suggest(prefix string) (string, bool) {
	panic("not implemented")
}
