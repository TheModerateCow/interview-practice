// Package library runs a public library's lending desk.
package library

// MaxLoans is how many copies a member can have on loan at once.
const MaxLoans = 3

// Library holds every copy and member. Timestamps passed to its methods only ever increase.
type Library struct {
	// your state here
}

// NewLibrary returns an empty library.
func NewLibrary() *Library {
	return &Library{}
}

// AddMember registers a member. False if the id exists.
func (lib *Library) AddMember(ts int, memberID string) bool {
	panic("not implemented")
}

// AddCopy adds a copy of title to the shelves. False if the copy id exists.
func (lib *Library) AddCopy(ts int, copyID, title string) bool {
	panic("not implemented")
}

// Checkout lends the member the available copy of title with the lowest id and returns it, or ""
// if the member is unknown, already has this title or MaxLoans copies on loan, or no copy is available.
func (lib *Library) Checkout(ts int, memberID, title string) string {
	panic("not implemented")
}

// Return puts the copy back on the shelf. False if it isn't on loan.
func (lib *Library) Return(ts int, copyID string) bool {
	panic("not implemented")
}

// Borrower is the member who has the copy on loan, or "".
func (lib *Library) Borrower(ts int, copyID string) string {
	panic("not implemented")
}
