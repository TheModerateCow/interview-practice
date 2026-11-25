# Loyalty points ledger (TDD)

You're building the points ledger for one member of a retail loyalty programme. Members earn points on every purchase, move up tiers as they spend, and redeem points before they expire.

**This is a TDD round.** Write your tests first, then the implementation:

1. Write tests for the rules below in your own test file; the example test in the starter shows the style.
2. Run them with **My tests**. They should fail against the stub.
3. Implement the ledger until your tests pass.
4. **Submit** runs the hidden tests against your implementation.

Your tests are scored too: afterwards they're run against a correct implementation (every test must pass) and against several subtly wrong ones (a good suite catches them). Cover the boundaries, the rounding, the error paths and the state.

All money is an integer number of **cents**; all points are whole integers. `day` is a day number (0, 1, 2, ...), and the days passed to an account's methods never decrease.

## API

| Method | Behaviour |
|---|---|
| `{{new Account}}` | A member with no spend and no points, in tier `"base"`. |
| `{{earn}}(day, spend_cents)` | Records a purchase and returns the points it earned. `spend_cents <= 0` fails with `{{invalid_amount}}` and changes nothing. |
| `{{balance}}(day)` | Points usable on `day`. |
| `{{redeem}}(day, points)` | Spends `points`. `points <= 0` fails with `{{invalid_amount}}`; more than the balance on `day` fails with `{{insufficient_points}}`. Either error changes nothing. |
| `{{tier}}()` | `"base"`, `"silver"` or `"gold"`. |

## Rules

**Tiers** come from lifetime spend: the total `spend_cents` of every successful `Earn`, including purchases that earned 0 points.

| Lifetime spend | Tier | Rate |
|---|---|---|
| below 50,000 cents (500.00) | base | 100% |
| 50,000 up to 199,999 cents | silver | 125% |
| 200,000 cents (2,000.00) or more | gold | 150% |

**Points for a purchase** = `spend_cents / 100 × rate`: one point per 1.00 spent at base, 1.25 at silver, 1.5 at gold.
- The rate is the tier **before** this purchase. A purchase that takes the member into a new tier still earns at the old rate; the new rate applies from the next purchase.
- **Rounding:** round to the nearest whole point; an exact half rounds up. (10.50 at base is 10.5 points, so 11; 10.49 is 10.)
- **Cap:** a single purchase earns at most 500 points, applied after rounding.
- A purchase can earn 0 points (e.g. 0.30 at base). That's not an error.

**Expiry:** points earned on day `d` are usable on days `d` to `d + 364` and expired from day `d + 365`. Expired points don't count in `Balance` and can't be redeemed.

**Redeeming** takes the oldest usable points first. Redeeming never changes lifetime spend or tier.

## Example

```
a = {{new Account}}
{{earn}}(0, 1050)    -> 11          (10.5 rounds up)
{{earn}}(30, 0)      -> fails: {{invalid_amount}}
{{earn}}(30, 49000)  -> 490         (lifetime spend now 50,050: silver)
{{tier}}()           -> "silver"
{{earn}}(40, 1000)   -> 13          (12.5 at silver rounds up)
{{redeem}}(50, 20)   -> ok          (takes the 11 from day 0, then 9 from day 30)
{{balance}}(364)     -> 494
{{balance}}(365)     -> 494         (day 0's points were already spent)
{{balance}}(395)     -> 13          (day 30's points expired)
```

## Checking your work

- **My tests** runs your own test files.
- **Submit** runs the hidden tests against your implementation.
