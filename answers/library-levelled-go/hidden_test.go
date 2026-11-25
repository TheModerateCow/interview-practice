package library

import "testing"

func hiddenSame(t *testing.T, what string, got, want []string) {
	t.Helper()
	if len(got) != len(want) {
		t.Fatalf("%s: got %v want %v", what, got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("%s: got %v want %v", what, got, want)
		}
	}
}

func hiddenEq[T comparable](t *testing.T, what string, got, want T) {
	t.Helper()
	if got != want {
		t.Fatalf("%s: got %v want %v", what, got, want)
	}
}

// hiddenLib returns a library with the members added, then the copies added as id, title pairs,
// at ts 1, 2, ... (keep setups under 10 calls; tests start at 10 or later).
func hiddenLib(t *testing.T, members []string, idTitle ...string) *Library {
	t.Helper()
	lib := NewLibrary()
	ts := 1
	for _, m := range members {
		if !lib.AddMember(ts, m) {
			t.Fatalf("AddMember(%s) failed", m)
		}
		ts++
	}
	for i := 0; i+1 < len(idTitle); i += 2 {
		if !lib.AddCopy(ts, idTitle[i], idTitle[i+1]) {
			t.Fatalf("AddCopy(%s, %s) failed", idTitle[i], idTitle[i+1])
		}
		ts++
	}
	return lib
}

// ---------------------------------------------------------------- level 1

func Test_l1_add_rules(t *testing.T) {
	lib := NewLibrary()
	hiddenEq(t, "add member", lib.AddMember(1, "ana"), true)
	hiddenEq(t, "duplicate member", lib.AddMember(2, "ana"), false)
	hiddenEq(t, "add copy", lib.AddCopy(3, "C1", "Dune"), true)
	hiddenEq(t, "duplicate copy id", lib.AddCopy(4, "C1", "Emma"), false)
	hiddenEq(t, "second copy of a title", lib.AddCopy(5, "C2", "Dune"), true)
	hiddenEq(t, "rejected copy added nothing", lib.Checkout(6, "ana", "Emma"), "")
	hiddenEq(t, "duplicate kept its title", lib.Checkout(7, "ana", "Dune"), "C1")
	hiddenEq(t, "borrower", lib.Borrower(8, "C1"), "ana")
}

func Test_l1_checkout_lowest_copy_id(t *testing.T) {
	lib := hiddenLib(t, []string{"ana", "bo", "cy", "dee"}, "D-2", "Dune", "D-10", "Dune", "D-1", "Dune", "E-1", "Emma")
	hiddenEq(t, "lowest id first", lib.Checkout(10, "ana", "Dune"), "D-1")
	hiddenEq(t, "string order", lib.Checkout(11, "bo", "Dune"), "D-10")
	hiddenEq(t, "then D-2", lib.Checkout(12, "cy", "Dune"), "D-2")
	hiddenEq(t, "all copies out", lib.Checkout(13, "dee", "Dune"), "")
	hiddenEq(t, "other title unaffected", lib.Checkout(14, "dee", "Emma"), "E-1")
	hiddenEq(t, "borrower of D-10", lib.Borrower(15, "D-10"), "bo")
	hiddenEq(t, "borrower of D-2", lib.Borrower(16, "D-2"), "cy")
}

func Test_l1_checkout_rejects(t *testing.T) {
	lib := hiddenLib(t, []string{"ana", "bo"}, "D-1", "Dune", "D-2", "Dune", "E-1", "Emma", "H-1", "Hamlet", "O-1", "Odyssey")
	hiddenEq(t, "unknown member", lib.Checkout(10, "zed", "Dune"), "")
	hiddenEq(t, "unknown title", lib.Checkout(11, "ana", "Ulysses"), "")
	hiddenEq(t, "first Dune", lib.Checkout(12, "ana", "Dune"), "D-1")
	hiddenEq(t, "one copy of a title per member", lib.Checkout(13, "ana", "Dune"), "")
	hiddenEq(t, "D-2 still on the shelf", lib.Borrower(14, "D-2"), "")
	hiddenEq(t, "second loan", lib.Checkout(15, "ana", "Emma"), "E-1")
	hiddenEq(t, "third loan", lib.Checkout(16, "ana", "Hamlet"), "H-1")
	hiddenEq(t, "fourth loan is over the limit", lib.Checkout(17, "ana", "Odyssey"), "")
	hiddenEq(t, "the limit is per member", lib.Checkout(18, "bo", "Odyssey"), "O-1")
	hiddenEq(t, "and bo can take the other Dune", lib.Checkout(19, "bo", "Dune"), "D-2")
}

func Test_l1_return_frees_copy(t *testing.T) {
	lib := hiddenLib(t, []string{"ana", "bo"}, "D-1", "Dune", "E-1", "Emma", "H-1", "Hamlet", "O-1", "Odyssey")
	lib.Checkout(10, "ana", "Dune")
	lib.Checkout(11, "ana", "Emma")
	lib.Checkout(12, "ana", "Hamlet")
	hiddenEq(t, "return", lib.Return(13, "D-1"), true)
	hiddenEq(t, "no borrower after return", lib.Borrower(14, "D-1"), "")
	hiddenEq(t, "return twice", lib.Return(15, "D-1"), false)
	hiddenEq(t, "return unknown copy", lib.Return(16, "Z-9"), false)
	hiddenEq(t, "return a copy never lent", lib.Return(17, "O-1"), false)
	hiddenEq(t, "returned copy lent again", lib.Checkout(18, "bo", "Dune"), "D-1")
	hiddenEq(t, "returning made room under the limit", lib.Checkout(19, "ana", "Odyssey"), "O-1")
	hiddenEq(t, "others untouched", lib.Borrower(20, "E-1"), "ana")
}

func Test_l1_borrow_again_after_return(t *testing.T) {
	lib := hiddenLib(t, []string{"ana", "bo"}, "E-1", "Emma", "E-2", "Emma")
	hiddenEq(t, "unknown copy", lib.Borrower(10, "Z-9"), "")
	hiddenEq(t, "copy on the shelf", lib.Borrower(11, "E-1"), "")
	hiddenEq(t, "ana", lib.Checkout(12, "ana", "Emma"), "E-1")
	hiddenEq(t, "bo", lib.Checkout(13, "bo", "Emma"), "E-2")
	lib.Return(14, "E-1")
	hiddenEq(t, "bo still can't take a second Emma", lib.Checkout(15, "bo", "Emma"), "")
	hiddenEq(t, "ana borrows the title again", lib.Checkout(16, "ana", "Emma"), "E-1")
	lib.Return(17, "E-2")
	lib.Return(18, "E-1")
	hiddenEq(t, "bo takes the lowest free copy", lib.Checkout(19, "bo", "Emma"), "E-1")
}

// ---------------------------------------------------------------- level 2

func Test_l2_available(t *testing.T) {
	lib := hiddenLib(t, []string{"ana", "bo"}, "D-1", "Dune", "D-2", "Dune", "D-3", "Dune", "E-1", "Emma")
	hiddenEq(t, "unknown title", lib.Available(10, "Ulysses"), 0)
	hiddenEq(t, "three Dune", lib.Available(11, "Dune"), 3)
	hiddenEq(t, "one Emma", lib.Available(12, "Emma"), 1)
	lib.Checkout(13, "ana", "Dune")
	lib.Checkout(14, "bo", "Dune")
	lib.Checkout(15, "ana", "Ulysses")
	hiddenEq(t, "two Dune out", lib.Available(16, "Dune"), 1)
	hiddenEq(t, "Emma untouched", lib.Available(17, "Emma"), 1)
	lib.Return(18, "D-1")
	hiddenEq(t, "back on the shelf", lib.Available(19, "Dune"), 2)
}

func Test_l2_loans_of(t *testing.T) {
	lib := hiddenLib(t, []string{"ana", "bo"}, "H-1", "Hamlet", "D-9", "Dune", "E-1", "Emma", "A-5", "Aeneid")
	hiddenSame(t, "unknown member", lib.LoansOf(10, "zed"), []string{})
	hiddenSame(t, "nothing on loan", lib.LoansOf(11, "ana"), []string{})
	lib.Checkout(12, "ana", "Hamlet")
	lib.Checkout(13, "ana", "Dune")
	lib.Checkout(14, "bo", "Emma")
	lib.Checkout(15, "ana", "Aeneid")
	hiddenSame(t, "ascending copy ids", lib.LoansOf(16, "ana"), []string{"A-5", "D-9", "H-1"})
	hiddenSame(t, "bo's own", lib.LoansOf(17, "bo"), []string{"E-1"})
	lib.Return(18, "D-9")
	hiddenSame(t, "returned copy gone", lib.LoansOf(19, "ana"), []string{"A-5", "H-1"})
}

func Test_l2_popular_order(t *testing.T) {
	lib := hiddenLib(t, []string{"ana"}, "D-1", "Dune", "E-1", "Emma", "H-1", "Hamlet", "O-1", "Odyssey")
	ts := 10
	for _, c := range []struct{ title, copyID string }{
		{"Hamlet", "H-1"}, {"Emma", "E-1"}, {"Dune", "D-1"}, {"Emma", "E-1"},
		{"Odyssey", "O-1"}, {"Emma", "E-1"}, {"Hamlet", "H-1"}, {"Dune", "D-1"},
	} {
		lib.Checkout(ts, "ana", c.title)
		lib.Return(ts+1, c.copyID)
		ts += 2
	}
	hiddenSame(t, "top 3", lib.Popular(ts, 3), []string{"Emma(3)", "Dune(2)", "Hamlet(2)"})
	hiddenSame(t, "n bigger than titles", lib.Popular(ts+1, 10), []string{"Emma(3)", "Dune(2)", "Hamlet(2)", "Odyssey(1)"})
	hiddenSame(t, "n 0", lib.Popular(ts+2, 0), []string{})
}

func Test_l2_popular_counts_checkouts(t *testing.T) {
	lib := hiddenLib(t, []string{"ana", "bo", "cy"}, "D-1", "Dune", "D-2", "Dune", "E-1", "Emma")
	hiddenSame(t, "nothing lent yet", lib.Popular(10, 5), []string{})
	lib.Checkout(11, "ana", "Emma")
	lib.Checkout(12, "bo", "Emma")
	lib.Checkout(13, "ana", "Emma")
	lib.Checkout(14, "zed", "Dune")
	hiddenSame(t, "failed checkouts don't count", lib.Popular(15, 5), []string{"Emma(1)"})
	lib.Checkout(16, "bo", "Dune")
	lib.Checkout(17, "cy", "Dune")
	hiddenSame(t, "every copy counts for its title", lib.Popular(18, 5), []string{"Dune(2)", "Emma(1)"})
	lib.Return(19, "D-1")
	lib.Return(20, "E-1")
	hiddenSame(t, "counts stay after return", lib.Popular(21, 5), []string{"Dune(2)", "Emma(1)"})
	hiddenEq(t, "shelf has no copies left to count", lib.Available(22, "Ulysses"), 0)
}

func Test_l2_popular_ties_by_title(t *testing.T) {
	lib := hiddenLib(t, []string{"ana", "bo"}, "Z-1", "Zorba", "A-1", "Aeneid", "M-1", "Middlemarch")
	lib.Checkout(10, "ana", "Zorba")
	lib.Checkout(11, "bo", "Middlemarch")
	lib.Checkout(12, "ana", "Aeneid")
	hiddenSame(t, "alphabetical", lib.Popular(13, 3), []string{"Aeneid(1)", "Middlemarch(1)", "Zorba(1)"})
	hiddenSame(t, "first two", lib.Popular(14, 2), []string{"Aeneid(1)", "Middlemarch(1)"})
}

// ---------------------------------------------------------------- level 3

func Test_l3_due_date(t *testing.T) {
	lib := hiddenLib(t, []string{"ana"}, "D-1", "Dune", "E-1", "Emma")
	hiddenEq(t, "unknown copy", lib.DueDate(10, "Z-9"), -1)
	hiddenEq(t, "on the shelf", lib.DueDate(11, "D-1"), -1)
	lib.Checkout(20, "ana", "Dune")
	lib.Checkout(25, "ana", "Emma")
	hiddenEq(t, "14 days after checkout", lib.DueDate(26, "D-1"), 34)
	hiddenEq(t, "per loan", lib.DueDate(27, "E-1"), 39)
	hiddenEq(t, "still due when overdue", lib.DueDate(50, "D-1"), 34)
	lib.Return(51, "D-1")
	hiddenEq(t, "returned", lib.DueDate(52, "D-1"), -1)
}

func Test_l3_renew(t *testing.T) {
	lib := hiddenLib(t, []string{"ana", "bo"}, "D-1", "Dune", "E-1", "Emma")
	hiddenEq(t, "not on loan", lib.Renew(10, "D-1"), -1)
	hiddenEq(t, "unknown copy", lib.Renew(11, "Z-9"), -1)
	lib.Checkout(20, "ana", "Dune")
	hiddenEq(t, "extends from the due date", lib.Renew(25, "D-1"), 48)
	hiddenEq(t, "due date moved", lib.DueDate(26, "D-1"), 48)
	hiddenEq(t, "renew on the due date", lib.Renew(48, "D-1"), 62)
	hiddenEq(t, "third renewal refused", lib.Renew(50, "D-1"), -1)
	hiddenEq(t, "refusal changes nothing", lib.DueDate(51, "D-1"), 62)
	lib.Return(52, "D-1")
	lib.Checkout(53, "bo", "Dune")
	hiddenEq(t, "a new loan starts over", lib.Renew(54, "D-1"), 81)
}

func Test_l3_renew_overdue_refused(t *testing.T) {
	lib := hiddenLib(t, []string{"ana"}, "E-1", "Emma")
	lib.Checkout(20, "ana", "Emma")
	hiddenEq(t, "a day late", lib.Renew(35, "E-1"), -1)
	hiddenEq(t, "due date unchanged", lib.DueDate(36, "E-1"), 34)
	lib.Return(37, "E-1")
	hiddenEq(t, "fined for the late days", lib.Fines(38, "ana"), 75)
}

func Test_l3_fines_per_day(t *testing.T) {
	lib := hiddenLib(t, []string{"ana", "bo"}, "D-1", "Dune", "E-1", "Emma", "H-1", "Hamlet")
	hiddenEq(t, "unknown member", lib.Fines(10, "zed"), 0)
	lib.Checkout(20, "ana", "Dune")
	lib.Checkout(21, "ana", "Emma")
	lib.Checkout(22, "bo", "Hamlet")
	lib.Return(34, "D-1")
	hiddenEq(t, "on the due date is on time", lib.Fines(35, "ana"), 0)
	hiddenEq(t, "overdue but still out", lib.Fines(40, "ana"), 0)
	lib.Return(41, "E-1")
	hiddenEq(t, "6 days late", lib.Fines(42, "ana"), 150)
	lib.Return(43, "H-1")
	hiddenEq(t, "fines are per member", lib.Fines(44, "bo"), 175)
	hiddenEq(t, "ana unchanged", lib.Fines(45, "ana"), 150)
	lib.Checkout(46, "ana", "Dune")
	lib.Return(65, "D-1")
	hiddenEq(t, "fines add up across loans", lib.Fines(66, "ana"), 275)
}

func Test_l3_fine_cap_and_renewed_due(t *testing.T) {
	lib := hiddenLib(t, []string{"ana", "bo", "cy"}, "D-1", "Dune", "E-1", "Emma", "H-1", "Hamlet")
	lib.Checkout(20, "ana", "Dune")
	lib.Checkout(21, "bo", "Emma")
	lib.Checkout(22, "cy", "Hamlet")
	lib.Renew(23, "H-1")
	lib.Return(73, "D-1")
	hiddenEq(t, "39 days late", lib.Fines(74, "ana"), 975)
	lib.Return(75, "E-1")
	hiddenEq(t, "40 days late reaches the cap", lib.Fines(76, "bo"), 1000)
	lib.Return(200, "H-1")
	hiddenEq(t, "capped per loan, counted from the renewed due date", lib.Fines(201, "cy"), 1000)
	lib.Checkout(202, "cy", "Hamlet")
	lib.Return(220, "H-1")
	hiddenEq(t, "a second loan has its own cap", lib.Fines(221, "cy"), 1100)
}

// ---------------------------------------------------------------- level 4

func Test_l4_history(t *testing.T) {
	lib := hiddenLib(t, []string{"ana", "bo"}, "D-1", "Dune", "E-1", "Emma", "H-1", "Hamlet")
	hiddenSame(t, "unknown member", lib.History(10, "zed"), []string{})
	hiddenSame(t, "nothing yet", lib.History(11, "ana"), []string{})
	lib.Checkout(12, "ana", "Hamlet")
	lib.Checkout(13, "ana", "Dune")
	lib.Checkout(14, "ana", "Dune")
	lib.Checkout(15, "bo", "Emma")
	lib.Return(16, "D-1")
	lib.Checkout(17, "ana", "Dune")
	lib.Checkout(18, "ana", "Ulysses")
	hiddenSame(t, "oldest first, repeats kept", lib.History(19, "ana"), []string{"Hamlet", "Dune", "Dune"})
	hiddenSame(t, "bo's own", lib.History(20, "bo"), []string{"Emma"})
}

func Test_l4_merge_moves_loans(t *testing.T) {
	lib := hiddenLib(t, []string{"ana", "ana2"}, "D-1", "Dune", "E-1", "Emma")
	lib.Checkout(10, "ana", "Dune")
	lib.Checkout(11, "ana2", "Emma")
	hiddenEq(t, "merge", lib.Merge(12, "ana", "ana2"), true)
	hiddenEq(t, "loan moved", lib.Borrower(13, "E-1"), "ana")
	hiddenSame(t, "kept account holds both", lib.LoansOf(14, "ana"), []string{"D-1", "E-1"})
	hiddenSame(t, "dropped account gone", lib.LoansOf(15, "ana2"), []string{})
	hiddenEq(t, "due date kept", lib.DueDate(16, "E-1"), 25)
	hiddenEq(t, "dropped id can't borrow", lib.Checkout(17, "ana2", "Dune"), "")
	hiddenEq(t, "merge again", lib.Merge(18, "ana", "ana2"), false)
	hiddenEq(t, "dropped id can be registered again", lib.AddMember(19, "ana2"), true)
	hiddenSame(t, "as a fresh account", lib.History(20, "ana2"), []string{})
	hiddenEq(t, "moved copy returns normally", lib.Return(21, "E-1"), true)
	hiddenEq(t, "fresh ana2 borrows it", lib.Checkout(22, "ana2", "Emma"), "E-1")
}

func Test_l4_merge_history_and_fines(t *testing.T) {
	lib := hiddenLib(t, []string{"ana", "bo"}, "D-1", "Dune", "E-1", "Emma", "H-1", "Hamlet", "O-1", "Odyssey")
	lib.Checkout(10, "bo", "Odyssey")
	lib.Checkout(11, "ana", "Hamlet")
	lib.Return(12, "O-1")
	lib.Checkout(13, "bo", "Dune")
	lib.Return(30, "D-1")
	lib.Checkout(31, "ana", "Emma")
	lib.Checkout(32, "bo", "Odyssey")
	hiddenEq(t, "bo's fine", lib.Fines(33, "bo"), 75)
	hiddenEq(t, "merge", lib.Merge(34, "ana", "bo"), true)
	hiddenSame(t, "histories interleave by checkout time", lib.History(35, "ana"),
		[]string{"Odyssey", "Hamlet", "Dune", "Emma", "Odyssey"})
	hiddenEq(t, "fines move over", lib.Fines(36, "ana"), 75)
	hiddenEq(t, "dropped id owes nothing", lib.Fines(37, "bo"), 0)
	lib.Return(50, "O-1")
	hiddenEq(t, "late return of a moved loan fines the kept account", lib.Fines(51, "ana"), 175)
	hiddenSame(t, "popularity unchanged", lib.Popular(52, 2), []string{"Odyssey(2)", "Dune(1)"})
}

func Test_l4_merge_rejects(t *testing.T) {
	lib := hiddenLib(t, []string{"ana", "bo", "cy"}, "D-1", "Dune", "D-2", "Dune", "E-1", "Emma", "H-1", "Hamlet", "O-1", "Odyssey")
	hiddenEq(t, "unknown keep", lib.Merge(10, "zed", "ana"), false)
	hiddenEq(t, "unknown drop", lib.Merge(11, "ana", "zed"), false)
	hiddenEq(t, "same member", lib.Merge(12, "ana", "ana"), false)
	lib.Checkout(13, "ana", "Dune")
	lib.Checkout(14, "bo", "Dune")
	hiddenEq(t, "both have Dune", lib.Merge(15, "ana", "bo"), false)
	hiddenEq(t, "refused merge moved nothing", lib.Borrower(16, "D-2"), "bo")
	lib.Return(17, "D-2")
	lib.Checkout(18, "ana", "Emma")
	lib.Checkout(19, "bo", "Hamlet")
	lib.Checkout(20, "bo", "Odyssey")
	hiddenEq(t, "four loans is over the limit", lib.Merge(21, "ana", "bo"), false)
	hiddenSame(t, "bo keeps his", lib.LoansOf(22, "bo"), []string{"H-1", "O-1"})
	lib.Return(23, "O-1")
	hiddenEq(t, "three loans is fine", lib.Merge(24, "ana", "bo"), true)
	hiddenSame(t, "all three", lib.LoansOf(25, "ana"), []string{"D-1", "E-1", "H-1"})
}

func Test_l4_merged_account_follows_rules(t *testing.T) {
	lib := hiddenLib(t, []string{"ana", "bo", "cy"}, "D-1", "Dune", "D-2", "Dune", "E-1", "Emma", "H-1", "Hamlet", "O-1", "Odyssey")
	lib.Checkout(10, "bo", "Dune")
	lib.Checkout(11, "bo", "Emma")
	lib.Merge(12, "ana", "bo")
	hiddenEq(t, "already has Dune via the merge", lib.Checkout(13, "ana", "Dune"), "")
	hiddenEq(t, "third loan", lib.Checkout(14, "ana", "Hamlet"), "H-1")
	lib.Return(15, "D-1")
	hiddenEq(t, "merge into cy", lib.Merge(16, "cy", "ana"), true)
	hiddenSame(t, "chained history", lib.History(17, "cy"), []string{"Dune", "Emma", "Hamlet"})
	hiddenEq(t, "borrower follows the chain", lib.Borrower(18, "E-1"), "cy")
	hiddenEq(t, "cy borrows Dune again", lib.Checkout(19, "cy", "Dune"), "D-1")
	hiddenEq(t, "now at the limit", lib.Checkout(20, "cy", "Odyssey"), "")
}
