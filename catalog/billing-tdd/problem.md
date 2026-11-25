# Subscription billing with proration (TDD)

You're building the billing core for one customer of a SaaS product sold per seat. Customers pick a plan and a billing cycle, renew each period, and can change plan or seat count mid-cycle: upgrades are charged pro rata, downgrades earn credit that pays future charges.

**This is a TDD round.** Write your tests first, then the implementation:

1. Write tests for the rules below in your own test file (`{{your_tests}}`); the example test in the starter shows the style.
2. Run them with **My tests**. They should fail against the stub.
3. Implement the subscription until your tests pass.
4. **Submit** runs the hidden tests against your implementation.

Your tests are scored too: afterwards they're run against a correct implementation (every test must pass) and against several subtly wrong ones (a good suite catches them). Cover the boundaries, the rounding, the error paths and the state.

Standard library only. All money is a whole number of **cents**. `day` is a day number (0, 1, 2, ...).

## API

| Function / method | Behaviour |
|---|---|
| `{{new Subscription}}` | An empty subscription. Call `{{start}}` before anything else. |
| `{{start}}(day, plan, cycle, seats)` | Starts the subscription with its first period beginning on `day`. The first period is paid outside this code: it charges nothing and starts with 0 credit. On error nothing is started. |
| `{{period_price}}()` | Full price of one period for the current plan, seats and cycle: per-seat price × seats. |
| `{{period_end}}()` | The day the current period ends, which is also the first day of the next period. |
| `{{credit}}()` | Unused credit, in cents. |
| `{{change}}(day, plan, seats)` | Moves to `plan` with `seats` (either or both may change) from `day` on, and returns the cents charged now. |
| `{{renew}}()` | Starts the next period on `{{period_end}}()` and returns the cents charged for it. |

The four errors are `{{unknown_plan}}`, `{{unknown_cycle}}`, `{{invalid_seats}}` and `{{outside_period}}`.

## Rules

**Prices** are per seat, per period, in cents. Plan and cycle names are exact and case-sensitive.

| Plan | `"monthly"` (30 days) | `"annual"` (360 days) |
|---|---|---|
| `"starter"` | 1,299 (12.99) | 12,990 (129.90) |
| `"team"` | 2,499 (24.99) | 24,990 (249.90) |
| `"business"` | 5,999 (59.99) | 59,990 (599.90) |

A period that starts on day `d` runs from `d` to `d + 29` (monthly) or `d + 359` (annual); `{{period_end}}()` is `d + 30` or `d + 360`. The cycle never changes after `New`.

**Validation.** `seats` must be 1 to 500 inclusive. `{{start}}` checks in this order and returns the first error: cycle (`{{unknown_cycle}}`), plan (`{{unknown_plan}}`), seats (`{{invalid_seats}}`). `{{change}}` checks in this order: `day` must be in the current period, so period start ≤ `day` < `{{period_end}}()` (`{{outside_period}}`); then plan; then seats. A `{{change}}` that fails charges 0 and changes nothing.

**Proration.** For a change on `day`, let `diff` = new `{{period_price}}()` − old `{{period_price}}()`, `left` = `{{period_end}}() − day` (the change day counts as a day left), and `length` = 30 or 360. The prorated amount is `diff × left / length`.
- **Upgrade** (`diff > 0`): charge the prorated amount **rounded to the nearest cent, an exact half rounding up**. (A 2,499 difference with 5 of 30 days left is 416.5, so 417.)
- **Downgrade** (`diff < 0`): nothing is charged; add the prorated amount (as a positive number) to credit, **rounded down** to the cent. (The same 416.5 becomes 416 of credit.)
- **No price change** (`diff == 0`): charge 0, credit unchanged. The new plan and seats still apply.

**Credit** is used automatically against every charge, from `{{change}}` (after rounding) or `{{renew}}`: as much credit as the charge needs, never more. What's left of the charge is what the method returns; unused credit carries over. Credit is never paid out and a charge is never negative.

**Renewal** charges the full `{{period_price}}()` of the current plan and seats (less credit) and moves the period forward by one cycle.

## Example

```
s = {{new Subscription}}
s.{{start}}(0, "team", "monthly", 2)  // period days 0-29, period price 4998
s.{{change}}(25, "team", 1)    -> 0         (-2499 x 5/30 = -416.5: credit 416)
s.{{credit}}()                 -> 416
s.{{change}}(26, "pro", 1)     -> fails: {{unknown_plan}}
s.{{change}}(30, "team", 2)    -> fails: {{outside_period}}   (day 30 is the next period)
s.{{renew}}()                  -> 2083      (2499 less 416 credit)
s.{{period_end}}()             -> 60
s.{{change}}(55, "team", 3)    -> 833       (4998 x 5/30 = 833)
```

## Checking your work

- **My tests** runs your own test files.
- **Submit** runs the hidden tests against your implementation.
