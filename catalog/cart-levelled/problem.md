# Shopping carts

You're building the in-memory service behind an online shop's checkout: a product catalog, the shoppers' carts, and later orders, promo codes, abandoned carts and what happens when a guest logs in. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Keep building on the same `{{Shop}}` type: later levels add methods to it.

**Timestamps.** Every method takes `{{ts}}` as its first argument: the time of the call, in minutes. Timestamps only ever increase from one call to the next. Level 1 doesn't use them yet, but keep them in the signatures.

**Money.** Prices and totals are integer amounts in cents.

## Level 1: catalog and carts

| Method | Behaviour |
|---|---|
| `{{add_product}}({{ts}}, {{sku}}, {{price_cents}}, {{stock}}) → bool` | Adds a product with `{{stock}}` units available. Returns `false`, changing nothing, if `{{sku}}` already exists, `{{price_cents}} <= 0` or `{{stock}} < 0`. A stock of 0 is allowed. |
| `{{add_to_cart}}({{ts}}, {{cart_id}}, {{sku}}, {{qty}}) → bool` | Adds `{{qty}}` units of `{{sku}}` to the cart, creating the cart on its first successful add. Returns `false`, changing nothing, if `{{sku}}` is unknown, `{{qty}} <= 0`, or the cart would then hold more units of `{{sku}}` than the product's stock. |
| `{{remove_from_cart}}({{ts}}, {{cart_id}}, {{sku}}, {{qty}}) → int` | Takes up to `{{qty}}` units of `{{sku}}` out of the cart and returns how many are left in that line. A line that reaches 0 is removed. Returns `-1` if the cart doesn't exist, the cart has no line for `{{sku}}`, or `{{qty}} <= 0`. |
| `{{cart_total}}({{ts}}, {{cart_id}}) → int` | The sum of price × quantity over the cart's lines. `0` for an unknown or empty cart. |
| `{{items}}({{ts}}, {{cart_id}}) → list of strings` | The cart's lines as `"sku:qty"`, sorted by sku (plain string order). An empty list for an unknown cart. |

Putting units in a cart doesn't take them out of stock: two carts can each hold every unit of the same product.

### Example

```
{{add_product}}(1, "mug", 1200, 5)      → true
{{add_product}}(2, "lamp", 4500, 2)     → true
{{add_product}}(3, "mug", 900, 9)       → false   (mug exists)
{{add_to_cart}}(4, "c1", "mug", 2)       → true
{{add_to_cart}}(5, "c1", "lamp", 3)      → false   (only 2 lamps)
{{add_to_cart}}(6, "c1", "lamp", 1)      → true
{{items}}(7, "c1")                     → ["lamp:1", "mug:2"]
{{cart_total}}(8, "c1")                 → 6900
{{remove_from_cart}}(9, "c1", "mug", 5)  → 0       (line removed)
{{cart_total}}(10, "c1")                → 4500
```

## Checking your work

- **Run** runs `{{run_entry}}`, a small program that reads commands from stdin (`product`, `add`, `remove`, `total`, `{{items}}`; see the top of the file). Extend it as you go.
- **My tests** runs your own test files (`{{your_tests}}`). The starter includes an example test to copy.
- **Submit** runs the hidden tests for every level you've unlocked.
