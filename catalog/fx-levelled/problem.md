# Multi-currency wallets

You're building the in-memory core of a wallet app whose customers hold money in several currencies at once. It keeps each wallet's balance per currency, and later grows published exchange rates, conversions with a fee, rate history and standing conversion orders. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Keep building on the same `{{Wallets}}` type: later levels add methods to it. Standard library only.

**Timestamps.** Every method takes `ts` (an integer) as its first argument: the time of the call. Timestamps never decrease from one call to the next. Level 1 doesn't use them yet, but keep them in the signatures.

**Currencies** are ISO-style codes: exactly three uppercase letters `A`–`Z`, like `"USD"` or `"JPY"`. Anything else (`"usd"`, `"US"`, `"U5D"`) is not a currency.

**Money** is a whole number of the currency's minor unit (cents for USD, yen for JPY). You never need to know how many minor units make a major one.

## Level 1: wallets and balances

| Method | Behaviour |
|---|---|
| `{{open_wallet}}(ts, {{wallet_id}}) → bool` | Opens an empty wallet. Returns `false`, changing nothing, if a wallet with this id is already open. Ids are case-sensitive. |
| `{{deposit}}(ts, {{wallet_id}}, currency, amount) → int` | Adds `amount` of `currency` to the wallet and returns the wallet's new balance in that currency. Returns `-1`, changing nothing, if the wallet doesn't exist, `currency` isn't a currency, or `amount <= 0`. |
| `{{withdraw}}(ts, {{wallet_id}}, currency, amount) → int` | Takes `amount` of `currency` out and returns the new balance in that currency. Returns `-1`, changing nothing, if the wallet doesn't exist, `amount <= 0`, or the wallet holds less than `amount` of that currency. Taking out the whole balance is allowed. |
| `{{balance}}(ts, {{wallet_id}}, currency) → int` | The wallet's balance in `currency`: `0` for a currency it has never held. `-1` if the wallet doesn't exist. |
| `{{holdings}}(ts, {{wallet_id}}) → list of strings` | Every currency the wallet holds a balance above zero in, as `"CODE:amount"`, sorted by code. A currency whose balance went back to 0 is left out. An empty list for an unknown wallet. |

### Example

```
{{open_wallet}}(1, "ana")                → true
{{open_wallet}}(2, "ana")                → false
{{deposit}}(3, "ana", "USD", 5000)       → 5000
{{deposit}}(4, "ana", "EUR", 1200)       → 1200
{{withdraw}}(5, "ana", "USD", 1500)      → 3500
{{withdraw}}(6, "ana", "EUR", 2000)      → -1      (only 1200 EUR)
{{balance}}(7, "ana", "GBP")             → 0
{{holdings}}(8, "ana")                   → ["EUR:1200", "USD:3500"]
{{balance}}(9, "bob", "USD")             → -1
```

## Checking your work

- **Run** checks your code against one example test per unlocked level and shows which fail and why.
- **Submit** runs the full hidden tests for every level you've unlocked. Passing them all opens the next level.
