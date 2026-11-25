# B2B invoice with discounts, tax and late fees (TDD)

You're building the invoice core for a wholesale supplier. An invoice collects line items, gives volume discounts on big orders, adds tax by product category, and then tracks what the customer still owes as payments and credit notes come in. Once the payment terms run out, a late fee applies.

**This is a TDD round.** Write your tests first, then the implementation:

1. Write tests for the rules below in `test_invoice.py` (pytest). `test_example.py` shows the style.
2. Run them with **My tests**. They should fail against the stub.
3. Implement `invoice.py` until your tests pass.
4. **Submit** runs the hidden tests against your implementation.

Your tests are scored too: afterwards they're run against a correct implementation (every test must pass) and against several subtly wrong ones (a good suite catches them). Cover the boundaries, the rounding, the error paths and the state.

Everything lives in `invoice.py`, class `Invoice`. Python 3 standard library only. All money is an `int` number of **cents**. A day is a day number (0, 1, 2, …). Every error is a `ValueError`, and a call that raises changes nothing.

## API

| Method | Behaviour |
|---|---|
| `Invoice(issue_day, terms)` | A new, empty invoice issued on `issue_day` with payment terms `terms`. |
| `add_line(unit_price, quantity, category)` | Adds a line item and returns its net amount (after discount, before tax). |
| `subtotal()` | Sum of the line nets. |
| `tax()` | Tax on the invoice (see the rounding rule). |
| `total()` | `subtotal() + tax()`. |
| `due_day()` | The last day the invoice can be paid without a late fee. |
| `pay(amount)` | Records a payment. |
| `credit_note(amount)` | Records a credit note (money taken off the invoice, e.g. for returned goods). |
| `balance()` | `total()` less every payment and credit note so far. |
| `amount_due(day)` | What the customer owes on `day`: `balance()` plus any late fee. |

## Rules

**Rounding.** Every rounding below is **to the nearest cent, an exact half rounding up** (2.5 → 3, 2.49 → 2). All amounts being rounded are zero or positive.

**Payment terms** are exactly `"net15"`, `"net30"` or `"net60"` (case-sensitive). `due_day()` is `issue_day` + 15, 30 or 60. Anything else raises.

**Line items.** `quantity` must be at least 1 and `unit_price` at least 0 (a free line is fine). `category` must be one of the tax categories below. The line's gross is `unit_price × quantity`. The volume discount depends on that line's quantity only:

| Quantity | Discount |
|---|---|
| 1 – 49 | none |
| 50 – 99 | 5% |
| 100 or more | 10% |

The discount is `gross × rate`, rounded; the line net is `gross − discount`. Lines can be added at any time, also after payments.

**Tax** depends on the line's category (exact, case-sensitive):

| Category | Rate |
|---|---|
| `"standard"` | 20% |
| `"reduced"` | 5% |
| `"zero"` | 0% |

Tax is rounded **once per category, not per line**: add up the nets of all lines in a category, apply that category's rate, round; `tax()` is the sum over the categories. (Two standard lines of 3 cents each are 6 cents at 20% = 1.2, so 1 cent of tax, not 1 + 1.)

**Payments and credit notes** both reduce `balance()`. Each `amount` must be at least 1 and at most the current `balance()`; otherwise it raises. Neither can push the balance below 0.

**Late fee.** On any day after `due_day()` (the due day itself is still on time), if `balance()` is above 0, `amount_due(day)` adds a one-off late fee of **1.5% of `balance()`**, rounded. It is the same on every later day (no compounding) and is reported only: it is not added to `balance()`, and `pay` and `credit_note` stay capped at `balance()`. On or before `due_day()`, or once the balance is 0, `amount_due(day)` is just `balance()`. A `day` before `issue_day` raises.

## Example

```python
inv = Invoice(12, "net30")                  # due_day() == 42
inv.add_line(2500, 60, "standard")   -> 142500   # 150000 less 5% (7500)
inv.add_line(15, 1, "standard")      -> 15
inv.add_line(899, 3, "reduced")      -> 2697
inv.subtotal()                       -> 145212
inv.tax()                            -> 28638    # 142515 x 20% = 28503, 2697 x 5% = 134.85 -> 135
inv.total()                          -> 173850
inv.credit_note(10000)
inv.balance()                        -> 163850
inv.pay(1_000_000_000)               -> ValueError   (more than the balance)
inv.amount_due(42)                   -> 163850   # due day: no fee
inv.amount_due(43)                   -> 166308   # 163850 x 1.5% = 2457.75 -> 2458
```

## Checking your work

- **My tests** runs your `test_*.py` files.
- **Submit** runs the hidden tests against `invoice.py`.
