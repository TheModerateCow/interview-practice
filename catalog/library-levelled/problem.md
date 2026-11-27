# Library lending desk

You're building the in-memory system behind a public library's lending desk. It tracks copies of books and the members who borrow them, and later grows shelf queries, due dates with late fines, and borrowing history with account merges. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Keep building on the same `{{Library}}` type: later levels add methods to it.

**Timestamps.** Every method takes `ts` as its first argument: the time of the call, as a day number. Timestamps only ever increase from one call to the next. Level 1 doesn't use them yet, but keep them in the signatures.

**Copies and titles.** A library can own several copies of one title; each copy has its own id. Titles and ids are plain strings.

## Level 1: members, copies and loans

| Method | Behaviour |
|---|---|
| `{{add_member}}(ts, member_id) → bool` | Registers a member. Returns `false` if `{{member_id}}` already exists. |
| `{{add_copy}}(ts, copy_id, title) → bool` | Puts a copy of `title` on the shelf. Returns `false` if `{{copy_id}}` already exists. |
| `{{checkout}}(ts, member_id, title) → string` | Lends the member a copy of `title` and returns its id: the copy on the shelf with the **lowest copy id** (plain string order, so `"D-10"` comes before `"D-2"`). Returns `""`, changing nothing, if the member is unknown, the member already has a copy of this title on loan, the member already has 3 copies on loan, or no copy of `title` is on the shelf. |
| `{{return_copy}}(ts, copy_id) → bool` | The copy comes back to the shelf. Returns `false` if it isn't on loan. |
| `{{borrower}}(ts, copy_id) → string` | The member who has the copy on loan, or `""` if nobody does (or the copy doesn't exist). |

A member who returned a title can borrow it again later, getting whatever copy `{{checkout}}` picks then.

### Example

```
{{add_member}}(1, "ana")           → true
{{add_member}}(2, "bo")            → true
{{add_member}}(3, "ana")           → false
{{add_copy}}(4, "D-2", "Dune")     → true
{{add_copy}}(5, "D-1", "Dune")     → true
{{checkout}}(6, "ana", "Dune")    → "D-1"
{{checkout}}(7, "ana", "Dune")    → ""      (ana already has Dune)
{{checkout}}(8, "bo", "Dune")     → "D-2"
{{checkout}}(9, "zed", "Dune")    → ""      (unknown member)
{{return_copy}}(10, "D-1")             → true
{{return_copy}}(11, "D-1")             → false
{{borrower}}(12, "D-1")           → ""
{{borrower}}(13, "D-2")           → "bo"
```

## Checking your work

- **Run** checks your code against one example test per unlocked level and shows which fail and why.
- **Submit** runs the full hidden tests for every level you've unlocked. Passing them all opens the next level.
