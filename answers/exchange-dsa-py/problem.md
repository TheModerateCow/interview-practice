# Ask book: sweep quotes and market buys

You run the ask side of one instrument's order book. Each price level holds some resting shares. A buyer who
takes `q` shares **sweeps** the book: the cheapest shares first, level by level, paying each level's price.

In `book.py`, implement `run_book(events)`. Process the events in order and return a list with one int for
every `quote` and `buy` event:

- `("add", price, qty)`: `qty` shares join the level at `price` (a new level, or more at an existing one).
- `("cancel", price, qty)`: `qty` shares leave the level at `price`. There are always at least `qty` there.
- `("quote", qty)`: the total cost to buy `qty` shares right now, or `-1` if fewer than `qty` shares rest in
  the book. A quote does **not** change the book.
- `("buy", qty)`: a market buy. It sweeps up to `qty` shares, removing them from the book; whatever the book
  can't fill is dropped. Output the cost of the shares it did get (`0` if the book is empty).

### Example

```
add 101 5 · add 100 3 · add 103 4 · quote 6 · cancel 101 2 · quote 7 · buy 4 · quote 7 · buy 10
answer: [603, 706, 401, -1, 614]
```

`quote 6` takes 3 at 100 and 3 at 101: 603. After the cancel, 101 holds 3, so `quote 7` is 300 + 303 + 103 = 706.
`buy 4` takes 3 at 100 and 1 at 101 (401), leaving 2 at 101 and 4 at 103: only 6 shares, so `quote 7` is -1.
`buy 10` takes all 6 (202 + 412 = 614) and the rest is dropped.

### Constraints

- `1 <= len(events) <= 2 * 10^5`; every `price` and `qty` is an integer, `1 <= price, qty <= 10^9`
- Up to `10^5` distinct prices; a quote can reach deep into the book.

## Checking your work

- **Run** runs `main.py`. It reads the number of events, then one event per line (`add 101 5`, `quote 6`, ...),
  and prints your answers one per line.
- **My tests** runs your own `test_*.py` files. `test_example.py` is an example to copy.
- **Submit** runs the hidden tests, including one large stream (150,000 events on a deep book).
