# Library lending desk

You're building the in-memory system behind a public library's lending desk. It tracks copies of books and the members who borrow them, and later grows shelf queries, due dates with late fines, and borrowing history with account merges. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Everything lives in package `library`, in `library.go`. Keep building on the same `Library` type: later levels add methods to it.

**Timestamps.** Every method takes `ts int` as its first argument: the time of the call, as a day number. Timestamps only ever increase from one call to the next. Level 1 doesn't use them yet, but keep them in the signatures.

**Copies and titles.** A library can own several copies of one title; each copy has its own id. Titles and ids are plain strings.

## Level 1: members, copies and loans

| Method | Behaviour |
|---|---|
| `AddMember(ts int, memberID string) bool` | Registers a member. Returns `false` if `memberID` already exists. |
| `AddCopy(ts int, copyID, title string) bool` | Puts a copy of `title` on the shelf. Returns `false` if `copyID` already exists. |
| `Checkout(ts int, memberID, title string) string` | Lends the member a copy of `title` and returns its id: the copy on the shelf with the **lowest copy id** (plain string order, so `"D-10"` comes before `"D-2"`). Returns `""`, changing nothing, if the member is unknown, the member already has a copy of this title on loan, the member already has `MaxLoans` (3) copies on loan, or no copy of `title` is on the shelf. |
| `Return(ts int, copyID string) bool` | The copy comes back to the shelf. Returns `false` if it isn't on loan. |
| `Borrower(ts int, copyID string) string` | The member who has the copy on loan, or `""` if nobody does (or the copy doesn't exist). |

A member who returned a title can borrow it again later, getting whatever copy `Checkout` picks then.

### Example

```
AddMember(1, "ana")           -> true
AddMember(2, "bo")            -> true
AddMember(3, "ana")           -> false
AddCopy(4, "D-2", "Dune")     -> true
AddCopy(5, "D-1", "Dune")     -> true
Checkout(6, "ana", "Dune")    -> "D-1"
Checkout(7, "ana", "Dune")    -> ""      (ana already has Dune)
Checkout(8, "bo", "Dune")     -> "D-2"
Checkout(9, "zed", "Dune")    -> ""      (unknown member)
Return(10, "D-1")             -> true
Return(11, "D-1")             -> false
Borrower(12, "D-1")           -> ""
Borrower(13, "D-2")           -> "bo"
```

## Checking your work

- **Run** runs `cmd/run/main.go`, a small program that reads commands from stdin (`member`, `copy`, `checkout`, `return`, `borrower`; see the top of the file). Extend it as you go.
- **My tests** runs your own `*_test.go` files. `library_example_test.go` is an example to copy.
- **Submit** runs the hidden tests for every level you've unlocked.
