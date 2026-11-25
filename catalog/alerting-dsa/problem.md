# Longest stretch within the error budget

You own the SLO alerting for an API. Its metrics pipeline gives you one sample per minute: `requests[i]` requests
served in minute `i`, of which `errors[i]` failed. The error budget is `budget_ppm` failed requests per million.
A stretch of **consecutive** minutes is *within budget* when its combined error rate is at most the budget:
`(total errors) * 1_000_000 <= (total requests) * budget_ppm`. Minutes are pooled, not averaged: a noisy minute
with little traffic can sit inside a stretch that is within budget overall. Minutes with no traffic count too.

Implement `{{longest_compliant_window}}(requests, errors, budget_ppm)`. Return the number of minutes in the longest
stretch that is within budget, or `0` if no minute is.

### Example

```
requests   = [120, 80, 200, 40, 160, 100]
errors     = [  2,  6,   1,  5,   0,   9]
budget_ppm = 20000   (2%)
longest_compliant_window(requests, errors, budget_ppm) -> 3
```

Minutes 2-4 hold 6 errors in 400 requests (1.5%), even though minute 3 alone runs at 12.5%.
Minutes 0-2 hold 9 errors in 400 requests (2.25%), and every longer stretch is over 2% as well.

### Constraints

- `len(requests) == len(errors)`, `0 <= n <= 200000`
- `0 <= errors[i] <= requests[i] <= 10^6`, `0 <= budget_ppm <= 10^6`
- Large inputs must finish well within 2 seconds, so checking every stretch (O(n^2)) is too slow.

## Checking your work

- **Run** runs the run program: stdin is `n budget_ppm`, then `n` request counts, then `n` error counts
  (any whitespace); it prints the answer.
- **My tests** runs your own test files; the example test is one to copy.
- **Submit** runs the hidden tests.
