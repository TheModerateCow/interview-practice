// Package library runs a public library's lending desk: copies of titles, members,
// loans with due dates and late fines, and each member's borrowing history.
package library

import (
	"sort"
	"strconv"
)

// MaxLoans is how many copies a member can have on loan at once.
const MaxLoans = 3

// LoanDays is the loan period: a copy checked out on day t is due on day t+LoanDays.
const LoanDays = 14

// FinePerDay is the late fine in cents for each day past the due date; FineCap caps it per loan.
const (
	FinePerDay = 25
	FineCap    = 1000
)

// loan is one checkout of one copy; back is -1 while the copy is still out.
type loan struct {
	copyID, title string
	member        string
	out, due      int
	back          int
	renewals      int
}

type bookCopy struct {
	id, title string
	current   *loan
}

type member struct {
	loans []*loan // every checkout, oldest first
}

// Library holds every copy and member. Timestamps passed to its methods only ever increase.
type Library struct {
	copies    map[string]*bookCopy
	members   map[string]*member
	checkouts map[string]int // successful checkouts per title
}

// NewLibrary returns an empty library.
func NewLibrary() *Library {
	return &Library{copies: map[string]*bookCopy{}, members: map[string]*member{}, checkouts: map[string]int{}}
}

func (m *member) onLoan() []*loan {
	out := []*loan{}
	for _, l := range m.loans {
		if l.back == -1 {
			out = append(out, l)
		}
	}
	return out
}

func (m *member) hasTitle(title string) bool {
	for _, l := range m.onLoan() {
		if l.title == title {
			return true
		}
	}
	return false
}

// AddMember registers a member. False if the id exists.
func (lib *Library) AddMember(ts int, memberID string) bool {
	if _, dup := lib.members[memberID]; dup {
		return false
	}
	lib.members[memberID] = &member{}
	return true
}

// AddCopy adds a copy of title to the shelves. False if the copy id exists.
func (lib *Library) AddCopy(ts int, copyID, title string) bool {
	if _, dup := lib.copies[copyID]; dup {
		return false
	}
	lib.copies[copyID] = &bookCopy{id: copyID, title: title}
	return true
}

// Checkout lends the member the available copy of title with the lowest id and returns it, or ""
// if the member is unknown, already has this title or MaxLoans copies on loan, or no copy is available.
func (lib *Library) Checkout(ts int, memberID, title string) string {
	m, ok := lib.members[memberID]
	if !ok || len(m.onLoan()) >= MaxLoans || m.hasTitle(title) {
		return ""
	}
	var best *bookCopy
	for _, c := range lib.copies {
		if c.title == title && c.current == nil && (best == nil || c.id < best.id) {
			best = c
		}
	}
	if best == nil {
		return ""
	}
	l := &loan{copyID: best.id, title: title, member: memberID, out: ts, due: ts + LoanDays, back: -1}
	best.current = l
	m.loans = append(m.loans, l)
	lib.checkouts[title]++
	return best.id
}

// ReturnCopy puts the copy back on the shelf. False if it isn't on loan.
func (lib *Library) ReturnCopy(ts int, copyID string) bool {
	c, ok := lib.copies[copyID]
	if !ok || c.current == nil {
		return false
	}
	c.current.back = ts
	c.current = nil
	return true
}

// Borrower is the member who has the copy on loan, or "".
func (lib *Library) Borrower(ts int, copyID string) string {
	if c, ok := lib.copies[copyID]; ok && c.current != nil {
		return c.current.member
	}
	return ""
}

// Available counts the copies of title that are not on loan.
func (lib *Library) Available(ts int, title string) int {
	n := 0
	for _, c := range lib.copies {
		if c.title == title && c.current == nil {
			n++
		}
	}
	return n
}

// LoansOf lists the copy ids the member has on loan, ascending.
func (lib *Library) LoansOf(ts int, memberID string) []string {
	out := []string{}
	if m, ok := lib.members[memberID]; ok {
		for _, l := range m.onLoan() {
			out = append(out, l.copyID)
		}
	}
	sort.Strings(out)
	return out
}

// Popular lists up to n titles as "title(checkouts)", most checkouts first, ties by title.
func (lib *Library) Popular(ts int, n int) []string {
	titles := []string{}
	for t := range lib.checkouts {
		titles = append(titles, t)
	}
	sort.Slice(titles, func(i, j int) bool {
		a, b := lib.checkouts[titles[i]], lib.checkouts[titles[j]]
		if a != b {
			return a > b
		}
		return titles[i] < titles[j]
	})
	out := []string{}
	for i := 0; i < len(titles) && i < n; i++ {
		out = append(out, titles[i]+"("+strconv.Itoa(lib.checkouts[titles[i]])+")")
	}
	return out
}

// DueDate is the day the copy's current loan is due, or -1 if it isn't on loan.
func (lib *Library) DueDate(ts int, copyID string) int {
	if c, ok := lib.copies[copyID]; ok && c.current != nil {
		return c.current.due
	}
	return -1
}

// Renew pushes the copy's due date back LoanDays and returns the new one, or -1 if the copy
// isn't on loan, is overdue, or this loan has been renewed twice already.
func (lib *Library) Renew(ts int, copyID string) int {
	c, ok := lib.copies[copyID]
	if !ok || c.current == nil {
		return -1
	}
	l := c.current
	if ts > l.due || l.renewals >= 2 {
		return -1
	}
	l.renewals++
	l.due += LoanDays
	return l.due
}

// Fines is what the member owes in cents for late returns: FinePerDay for each day a returned
// copy came back after its due date, at most FineCap per loan. Copies still out add nothing yet.
func (lib *Library) Fines(ts int, memberID string) int {
	total := 0
	if m, ok := lib.members[memberID]; ok {
		for _, l := range m.loans {
			if l.back != -1 && l.back > l.due {
				total += min(FineCap, FinePerDay*(l.back-l.due))
			}
		}
	}
	return total
}

// History lists the title of every checkout the member made, oldest first.
func (lib *Library) History(ts int, memberID string) []string {
	out := []string{}
	if m, ok := lib.members[memberID]; ok {
		for _, l := range m.loans {
			out = append(out, l.title)
		}
	}
	return out
}

// Merge folds dropID's account into keepID: its loans, history and fines move over and dropID
// stops existing. False if either is unknown, they're the same, both have the same title on loan,
// or the merged account would have more than MaxLoans copies on loan.
func (lib *Library) Merge(ts int, keepID, dropID string) bool {
	k, ok1 := lib.members[keepID]
	d, ok2 := lib.members[dropID]
	if !ok1 || !ok2 || keepID == dropID {
		return false
	}
	if len(k.onLoan())+len(d.onLoan()) > MaxLoans {
		return false
	}
	for _, l := range d.onLoan() {
		if k.hasTitle(l.title) {
			return false
		}
	}
	for _, l := range d.loans {
		l.member = keepID
	}
	k.loans = append(k.loans, d.loans...)
	sort.SliceStable(k.loans, func(i, j int) bool { return k.loans[i].out < k.loans[j].out })
	delete(lib.members, dropID)
	return true
}
