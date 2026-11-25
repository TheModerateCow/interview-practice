# Business-class upgrades on a multi-stop flight

One aircraft flies a multi-stop route through stops `0, 1, …, n`. Leg `k` is the hop from stop `k` to stop
`k+1`. Because some passengers already paid for business, the number of **free business seats differs per leg**:
`{{cap}}[k]`.

Upgrade requests come from passengers already on the flight. Request `[board, alight]` covers legs
`board … alight-1`. The airline only upgrades a passenger for **every** leg they fly (no swapping cabins
mid-trip). A passenger who alights at stop `s` frees their seat for someone boarding at `s`.

Implement `{{max_upgrades}}({{cap}}, {{requests}})`: the largest number of
passengers that can be upgraded at the same time without going over any leg's free seats.

### Example

```
{{cap}} = [2, 1, 2, 1, 2]      (5 legs, stops 0..5)
{{requests}} = [2,4] [3,5] [2,3] [0,4] [4,5] [1,3]
answer: 4
```

Upgrade `[2,3]`, `[1,3]`, `[3,5]` and `[4,5]`: legs 1, 2 and 4 are then full and the others have room.
Taking `[0,4]` (or `[2,4]`) as well would overfill leg 1 or leg 2. Picking the earliest boarder first
(`[0,4]`) gets only 3, and so does shortest-trip-first: after the 1-leg trips it takes `[2,4]`, which blocks
both `[1,3]` and `[3,5]`.

### Constraints

- `1 <= n == len({{cap}}) <= 2 * 10^5`, `0 <= {{cap}}[k] <= 10^9`
- `0 <= len({{requests}}) <= 2 * 10^5`, `0 <= board < alight <= n`
- Requests come in any order; the same trip may be requested more than once.

## Checking your work

- **Run** runs `{{run_entry}}`. It reads `n m`, then the `n` capacities, then `m` lines `board alight`, and prints
  your answer.
- **My tests** runs your own `{{your_tests}}` files. The example test is an example to copy.
- **Submit** runs the hidden tests, including one large route (200000 legs, 200000 requests).
