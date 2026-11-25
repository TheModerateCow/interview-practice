# Dispatch radius on the corridor

You run dispatch for a ride-sharing service along a single highway corridor. Every waiting rider and every idle
driver sits at an integer kilometre marker on the corridor. Operations sets one **dispatch radius** `R` for the whole
corridor: a driver may be sent to a rider only if they are at most `R` km apart (`|rider - driver| <= R`).
Each driver picks up **at most one** rider, and each rider is picked up by at most one driver.

In `dispatch.go`, implement:

```go
func MinDispatchRadius(riders, drivers []int, need int) int
```

Return the smallest integer `R >= 0` that lets at least `need` riders be picked up at the same time.
If `need <= 0`, return `0`. If no radius can serve `need` riders (there are fewer than `need` riders or fewer
than `need` drivers), return `-1`. Positions may repeat and are not sorted.

### Example

```
riders  = [2, 9, 15]
drivers = [4, 10, 30]
MinDispatchRadius(riders, drivers, 2) -> 2    (2 with 4, 9 with 10)
MinDispatchRadius(riders, drivers, 3) -> 15   (everyone served: 2-4, 9-10, 15-30)
```

### Constraints

- `0 <= len(riders), len(drivers) <= 200000`
- `-10^9 <= position <= 10^9`
- `0 <= need <= 200000`
- Large inputs must finish well within 2 seconds, so a pairwise O(n * m) approach is too slow.

## Checking your work

- **Run** runs `cmd/run/main.go`: stdin is `n m need`, then `n` rider positions, then `m` driver positions
  (any whitespace); it prints the answer.
- **My tests** runs your own `*_test.go` files. `dispatch_example_test.go` is an example to copy.
- **Submit** runs the hidden tests.
