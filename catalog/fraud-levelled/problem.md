# Payment risk screen

You're building the in-memory risk screen of a payment provider. Every card payment is screened before it goes through: the screen approves it, declines it, or sends it to a human for review. It starts with blocklists and later grows velocity rules, rule priorities with an allowlist, and an analysts' review queue. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Everything lives in the `{{RiskScreen}}` type. Keep building on it: later levels add methods to it. Standard library only.

**Timestamps.** Every method takes `{{ts}}` (an integer, in seconds) as its first argument: the time of the call. Timestamps never go down from one call to the next (two calls can share one). Level 1 doesn't use them yet, but keep them in the signatures.

**Money** is in integer cents.

**Strings** are compared exactly (case-sensitive).

## Level 1: blocklists

A transaction has an id, a card number, a merchant, an amount and the country it comes from. The risk team keeps a blocklist of cards, merchants and countries.

| Method | Behaviour |
|---|---|
| `{{block}}({{ts}}, {{kind}}, {{value}}) → bool` | Puts `{{value}}` on the blocklist for `{{kind}}`, which is `"card"`, `"merchant"` or `"country"`. Returns `false`, changing nothing, for any other `{{kind}}` or if `{{value}}` is already blocked for that kind. |
| `{{unblock}}({{ts}}, {{kind}}, {{value}}) → bool` | Takes `{{value}}` off the blocklist for `{{kind}}`. Returns `false` if it isn't blocked for that kind. |
| `{{screen}}({{ts}}, {{txn_id}}, {{card}}, {{merchant}}, {{amount}}, {{country}}) → string` | Screens a transaction, records it, and returns its decision: `"decline"` if its card is on the card blocklist, its merchant on the merchant blocklist, or its country on the country blocklist; otherwise `"approve"`. Returns `""`, recording nothing, if `{{txn_id}}` was already screened or `{{amount}} <= 0`. |
| `{{decision}}({{ts}}, {{txn_id}}) → string` | The decision recorded for the transaction, `""` if it was never screened. |

Each kind has its own list: blocking the merchant `"x1"` doesn't block a card or a country called `"x1"`. Changing the blocklist never changes a decision already made.

### Example

```
{{block}}(1, "card", "4111")                                → true
{{block}}(2, "card", "4111")                                → false   (already blocked)
{{block}}(3, "bank", "b-1")                                 → false   (no such kind)
{{screen}}(4, "t1", "4111", "m-shoes", 2500, "GB")          → "decline"
{{screen}}(5, "t2", "5500", "m-shoes", 2500, "GB")          → "approve"
{{block}}(6, "country", "ZZ")                               → true
{{screen}}(7, "t3", "5500", "m-books", 900, "ZZ")           → "decline"
{{unblock}}(8, "card", "4111")                              → true
{{screen}}(9, "t4", "4111", "m-books", 1200, "GB")          → "approve"
{{decision}}(10, "t1")                                      → "decline"
{{screen}}(11, "t4", "5500", "m-books", 1200, "GB")         → ""        (t4 already screened)
```

## Checking your work

- **Run** checks your code against one example test per unlocked level and shows which fail and why.
- **Submit** runs the full hidden tests for every level you've unlocked. Passing them all opens the next level.
