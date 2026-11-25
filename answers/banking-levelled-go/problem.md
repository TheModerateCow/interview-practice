# Bank ledger

You're building the in-memory core of a retail bank's ledger. Customers hold **accounts** identified by a string id (like `acc-a`); money moves in by deposit, out by withdrawal, and between accounts by transfer. The ledger later grows spending rankings, scheduled payments, account merges and balance history. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Everything lives in package `bank`, in `bank.go`. Keep building on the same `Bank` type: later levels add methods to it.

**Timestamps.** Every method takes `ts int` as its first argument: the time of the call. Timestamps strictly increase from one call to the next. Level 1 doesn't need them yet, but keep them in the signatures.

**Money** is a whole number of cents (`int`). Every `amount` passed in is positive.

## Level 1: accounts and money movement

| Method | Behaviour |
|---|---|
| `OpenAccount(ts int, id string) bool` | Opens an empty account (balance 0). Returns `false`, changing nothing, if an account with this id is already open. Ids are case-sensitive. |
| `Deposit(ts int, id string, amount int) (int, bool)` | Adds `amount` to the account. Returns the new balance and `true`, or `0, false` if the account doesn't exist. |
| `Withdraw(ts int, id string, amount int) (int, bool)` | Takes `amount` out. Returns the new balance and `true`, or `0, false` if the account doesn't exist or holds less than `amount`. Balances never go below zero. |
| `Transfer(ts int, from, to string, amount int) (int, bool)` | Moves `amount` from `from` to `to`. Returns the **sender's** new balance and `true`. Returns `0, false`, changing nothing, if either account doesn't exist, `from` and `to` are the same account, or the sender holds less than `amount`. |
| `Balance(ts int, id string) (int, bool)` | The account's balance and `true`, or `0, false` if it doesn't exist. |

### Example

```
OpenAccount(1, "acc-a")                    -> true
OpenAccount(2, "acc-b")                    -> true
OpenAccount(3, "acc-a")                    -> false
Deposit(4, "acc-a", 1000)                  -> 1000, true
Withdraw(5, "acc-a", 250)                  -> 750, true
Transfer(6, "acc-a", "acc-b", 400)         -> 350, true
Transfer(7, "acc-b", "acc-a", 500)         -> 0, false   (acc-b holds 400)
Transfer(8, "acc-a", "acc-a", 10)          -> 0, false
Balance(9, "acc-b")                        -> 400, true
Withdraw(10, "acc-z", 5)                   -> 0, false
```

## Checking your work

- **Run** runs `cmd/run/main.go`, a small program that reads commands from stdin (`open`, `deposit`, `withdraw`, `transfer`, `balance`; see the top of the file). Extend it as you go.
- **My tests** runs your own `*_test.go` files. `bank_example_test.go` is an example to copy.
- **Submit** runs the hidden tests for every level you've unlocked.
