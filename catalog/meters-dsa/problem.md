# Home battery arbitrage

Your smart-meter platform schedules customers' home batteries. Tomorrow's half-hourly tariff is published
in advance: `{{prices}}[i]` is the price in pence per kWh for slot `i`, the same for buying from and selling
to the grid. Prices can be negative when there is surplus wind: then charging earns money.

The battery starts empty and holds at most `{{capacity}}` kWh. In each slot it does exactly one of:
- **charge** 1 kWh: pay `{{prices}}[i]` (needs room in the battery);
- **discharge** 1 kWh: earn `{{prices}}[i] - {{wear}}` (needs stored energy; `{{wear}}` is the per-kWh cost of cycling);
- **idle**.

Energy still stored at the end of the day is worth nothing. 
Implement `{{best_battery_profit}}({{prices}}, {{capacity}}, {{wear}})`.

Return the largest total profit any schedule makes (idling all day makes `0`).

### Example

```
prices = [12, 9, 25, 14, 30, 8, 11, 27], capacity = 2, wear = 3
best_battery_profit(prices, 2, 3) -> 44
```

Charge at 12 and 9, discharge at 25, idle at 14, discharge at 30, charge at 8, idle at 11, discharge at 27:
`-12 - 9 + (25-3) + (30-3) - 8 + (27-3) = 44`. Charging again at 14 earns less.

### Constraints

- `0 <= len({{prices}}) <= 100000`, `-1000 <= {{prices}}[i] <= 1000`
- `0 <= {{capacity}} <= 100`, `0 <= {{wear}} <= 1000`
- Large inputs must finish well within 2 seconds; trying every schedule is far too slow.

## Checking your work

- **Run** runs `{{run_entry}}`: stdin is `n capacity wear`, then `n` prices (any whitespace); it prints the answer.
- **My tests** runs your own `{{your_tests}}` files. The example test is one to copy.
- **Submit** runs the hidden tests.
