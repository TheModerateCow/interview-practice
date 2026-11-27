# Merchant payouts

You're building the in-memory settlement service for an online marketplace. Merchants sell through the platform, the platform takes a fee on every sale, and the rest is owed to the merchant. Later the service grows refunds, scheduled payouts, a rolling reserve and chargebacks. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Everything lives in the `{{Payouts}}` type. Keep building on it: later levels add methods to it. Standard library only.

**Days.** Dates are integers. Every method takes `day` as its first argument: today, the day of the call. Days never decrease from one call to the next. Level 1 doesn't use `day` yet, but keep it in the signatures.

**Money** is in integer cents. Fee rates are in **basis points** (bps): 100 bps = 1%, 10000 bps = 100%.

## Level 1: merchants and sales

| Method | Behaviour |
|---|---|
| `{{add_merchant}}(day, {{merchant_id}}, {{fee_bps}})` | Signs up a merchant whose sales pay the platform `{{fee_bps}}`. Returns `false`, changing nothing, if `{{merchant_id}}` already exists or `{{fee_bps}}` is outside `0..10000`. |
| `{{record_sale}}(day, {{merchant_id}}, amount)` | Records a sale of `amount` and returns its id. Ids are `"s1"`, `"s2"`, `"s3"`, … in order, counted across the whole platform; a failed call uses no id. Returns `""` if the merchant doesn't exist or `amount <= 0`. |
| `{{fee}}(day, {{sale_id}})` | The platform's fee on the sale. `-1` if the sale doesn't exist. |
| `{{balance}}(day, {{merchant_id}})` | What the platform owes the merchant: the sum of every sale's **net** (amount minus fee). `0` for an unknown merchant. |

**The fee** is `amount × {{fee_bps}} / 10000`, rounded to a whole cent, **half a cent rounding up**: 7.5 → 8, 7.49 → 7.

### Example

```
add_merchant(1, "acme", 290)    -> true
add_merchant(1, "bolt", 250)    -> true
add_merchant(2, "acme", 100)    -> false
record_sale(3, "acme", 10000)   -> "s1"
record_sale(4, "zed", 500)      -> ""      (no such merchant)
record_sale(5, "bolt", 300)     -> "s2"
fee(6, "s1")                    -> 290
fee(6, "s2")                    -> 8       (7.5 rounds up)
balance(7, "acme")              -> 9710
balance(7, "bolt")              -> 292
```

## Checking your work

- **Run** checks your code against one example test per unlocked level and shows which fail and why.
- **Submit** runs the full hidden tests for every level you've unlocked. Passing them all opens the next level.
