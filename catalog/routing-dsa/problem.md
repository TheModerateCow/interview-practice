# Electric van: fastest delivery

An electric delivery van leaves the depot (junction `0`) for a customer at junction `n-1`. The road network has
`n` junctions. Each road joins two junctions, can be driven **both ways**, takes `{{minutes}}` and uses `{{energy}}`
battery units. The van can't drive a road it doesn't have the charge for, but it may arrive with exactly `0`.

The battery holds at most `capacity` units and starts with `charge`. Some junctions have a charger:
`rate[i]` is the minutes it takes to add **one** unit at junction `i` (`0` means no charger there). The van may
stop at any charger, any number of times, and charge any whole number of units, up to `capacity`.

Implement `{{fastest_delivery}}`: the fewest
minutes to reach the customer, or `-1` if the van can't get there.

### Example

```
n=5, capacity=10, charge=4, rate=[0, 5, 1, 0, 0]
roads: 0-1 (10 min, 2 units)  1-2 (10 min, 2)  2-4 (10 min, 6)  0-3 (5 min, 4)  3-4 (5 min, 6)
answer: 36
```

0→3→4 is quickest on paper, but junction 3 has no charger and the van can't finish it. Drive 0→1→2 (20 min,
arriving empty), add 6 units at the cheap charger at 2 (6 min), then 2→4 (10 min): 36. Charging at 1 costs more,
and filling up to 10 at junction 2 would waste 4 minutes.

### Constraints

- `1 <= n <= 1000`, `0 <= the number of roads <= 5000`, `0 <= charge <= capacity <= 100`
- `0 <= {{a}}, {{b}} < n` (a road may join a junction to itself; two junctions may have several roads)
- `1 <= {{minutes}} <= 10^4`, `0 <= {{energy}} <= 100`, `0 <= rate[i] <= 1000`
- If `n == 1` the van is already there: the answer is `0`.

## Checking your work

- **Run** runs the run entry. It reads `n m capacity charge`, then the `n` rates, then `m` lines `a b minutes energy`,
  and prints your answer.
- **My tests** runs your own test files. The starter includes an example test to copy.
- **Submit** runs the hidden tests, including one large network (1000 junctions, 5000 roads, capacity 100).
