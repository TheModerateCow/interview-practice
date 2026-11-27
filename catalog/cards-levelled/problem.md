# Card authorisations

You're building the in-memory authorisation service of a credit card issuer. It issues cards with a credit limit, approves or declines purchases by placing a hold on the card's credit, and settles those holds when the merchant captures them. It later grows hold expiry, refunds and statements, and spending controls. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Everything lives in the `{{Issuer}}` type. Keep building on it: later levels add methods to it. Standard library only.

**Days.** Dates are integers. Every method takes `day` as its first argument: today, the day of the call. Days never decrease from one call to the next (several calls can share a day). Level 1 doesn't use `day` yet, but keep it in the signatures.

**Money** is in integer cents. No rounding happens anywhere.

## Level 1: cards, holds and captures

| Method | Behaviour |
|---|---|
| `{{issue_card}}(day, card_id, limit)` | Issues a card with a credit limit of `limit`. Returns `false` if `card_id` already exists or `limit <= 0`. |
| `{{authorize}}(day, card_id, category, amount)` | A merchant asks to charge `amount` to the card; `category` is the merchant's category (for example `"grocery"`). If approved, places a **hold** of `amount` and returns the authorisation's id: `"a1"`, `"a2"`, `"a3"`, … in order, counted across all cards; a declined call uses no id. Returns `""` (declined, changing nothing) if the card doesn't exist, `amount <= 0`, or `amount` is more than the card's available credit. |
| `{{capture}}(day, auth_id, amount)` | The merchant settles the authorisation for `amount`, which may be less than was authorised. `amount` is **posted** to the card and the whole hold is released, so any difference goes back to available credit. An authorisation is captured at most once. Returns `false`, changing nothing, if the authorisation doesn't exist, isn't open (already captured or voided), or `amount` is `<= 0` or more than the authorised amount. |
| `{{void_auth}}(day, auth_id)` | Cancels an open authorisation and releases its hold. Returns `false` if the authorisation doesn't exist or isn't open. |
| `{{available}}(day, card_id)` | The card's available credit: `limit` minus everything posted minus every open hold. `-1` if the card doesn't exist. |

### Example

```
issue_card(1, "c1", 50000)                  -> true
issue_card(1, "c1", 9000)                   -> false
authorize(2, "c1", "grocery", 12000)        -> "a1"
authorize(2, "c1", "travel", 45000)         -> ""      (38000 available)
authorize(3, "c1", "travel", 30000)         -> "a2"
available(3, "c1")                          -> 8000
capture(4, "a1", 9500)                      -> true    (the other 2500 is released)
available(4, "c1")                          -> 10500
void_auth(5, "a2")                          -> true
available(5, "c1")                          -> 40500
capture(6, "a2", 100)                       -> false   (voided)
```

## Checking your work

- **Run** checks your code against one example test per unlocked level and shows which fail and why.
- **Submit** runs the full hidden tests for every level you've unlocked. Passing them all opens the next level.
