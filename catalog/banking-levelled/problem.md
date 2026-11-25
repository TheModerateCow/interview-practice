# Bank ledger

You're building the in-memory core of a retail bank's ledger. Customers hold **accounts** identified by a string id (like `acc-a`); money moves in by deposit, out by withdrawal, and between accounts by transfer. The ledger later grows spending rankings, scheduled payments, account merges and balance history. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Keep building on the same `{{Bank}}` type: later levels add methods to it.

**Timestamps.** Every method takes `{{ts}}` (an integer) as its first argument: the time of the call. Timestamps strictly increase from one call to the next. Level 1 doesn't need them yet, but keep them in the signatures.

**Money** is a whole number of cents. Every `{{amount}}` passed in is positive.

**Results.** Where a method returns a balance, it returns the number when the call succeeds and *none* when it fails (the signatures below show how your language expresses that).

## Level 1: accounts and money movement

| Method | Behaviour |
|---|---|
| `{{open_account}}(ts, id) → bool` | Opens an empty account (balance 0). Returns `false`, changing nothing, if an account with this id is already open. Ids are case-sensitive. |
| `{{deposit}}(ts, id, amount) → balance or none` | Adds `amount` to the account. Returns the new balance, or *none* if the account doesn't exist. |
| `{{withdraw}}(ts, id, amount) → balance or none` | Takes `amount` out. Returns the new balance, or *none* if the account doesn't exist or holds less than `amount`. Balances never go below zero. |
| `{{transfer}}(ts, from, to, amount) → balance or none` | Moves `amount` from `from` to `to`. Returns the **sender's** new balance. Returns *none*, changing nothing, if either account doesn't exist, `from` and `to` are the same account, or the sender holds less than `amount`. |
| `{{balance}}(ts, id) → balance or none` | The account's balance, or *none* if it doesn't exist. |

### Example

```
{{open_account}}(1, "acc-a")                  → true
{{open_account}}(2, "acc-b")                  → true
{{open_account}}(3, "acc-a")                  → false
{{deposit}}(4, "acc-a", 1000)                 → 1000
{{withdraw}}(5, "acc-a", 250)                 → 750
{{transfer}}(6, "acc-a", "acc-b", 400)        → 350
{{transfer}}(7, "acc-b", "acc-a", 500)        → none   (acc-b holds 400)
{{transfer}}(8, "acc-a", "acc-a", 10)         → none
{{balance}}(9, "acc-b")                       → 400
{{withdraw}}(10, "acc-z", 5)                  → none
```

## Checking your work

- **Run** runs `{{run_entry}}`, a small program that reads commands from stdin (`open`, `deposit`, `withdraw`, `transfer`, `balance`; see the top of the file). Extend it as you go.
- **My tests** runs your own test files (`{{your_tests}}`). The starter includes an example test to copy.
- **Submit** runs the hidden tests for every level you've unlocked.
