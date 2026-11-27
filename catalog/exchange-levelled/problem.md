# Order book

You're building the in-memory order book for one instrument on an exchange. Traders send **orders**, each identified by a string id (like `a1`) and carrying a **price** and a number of **shares**. Orders that don't trade straight away **rest** in the book until they're cancelled or filled. The book later grows queue priority, sweeping buys and full two-sided matching. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Keep building on the same `{{OrderBook}}` type: later levels add methods to it.

**Order of calls.** There is no clock: calls happen one after another, and "earlier" means an earlier call.

**Numbers.** Prices and share counts passed in are positive and below 10^9. Totals of shares and costs can exceed 32 bits; the signatures below use 64-bit integers for them where the language has a choice.

## Level 1: resting sell orders

For now every order is a **sell** order: it offers its shares at its price and rests on the **ask** side of the book.

| Method | Behaviour |
|---|---|
| `{{add_order}}(order_id, price, qty) → bool` | A sell order for `qty` shares at `price` joins the book. Returns `false`, changing nothing, if `order_id` has been used before, even by an order that is gone. Ids are case-sensitive. |
| `{{cancel_order}}(order_id) → bool` | Takes the order out of the book. Returns `false` if no order with that id is resting (it never existed, or it's already gone). |
| `{{best_ask}}() → price or none` | The lowest price at which any shares rest; *none* if the book is empty. |
| `{{depth_at}}(price) → shares` | The total shares resting at `price` across all orders; `0` if none. |

### Example

```
{{add_order}}("a1", 101, 5)        → true
{{add_order}}("a2", 100, 3)        → true
{{add_order}}("a3", 101, 2)        → true
{{add_order}}("a1", 99, 1)         → false   (a1 is taken)
{{best_ask}}()                     → 100
{{depth_at}}(101)                  → 7
{{cancel_order}}("a2")             → true
{{cancel_order}}("a2")             → false
{{best_ask}}()                     → 101
{{depth_at}}(100)                  → 0
```

## Checking your work

- **Run** checks your code against one example test per unlocked level and shows which fail and why.
- **Submit** runs the full hidden tests for every level you've unlocked. Passing them all opens the next level.
