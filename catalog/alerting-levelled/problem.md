# SLO monitor

You're building the in-memory core of an SLO monitor for a fleet of API **services**, each identified by a string name (like `checkout`). The metrics pipeline sends one **sample** per service per minute: how many requests the service served in that minute and how many of them failed. The monitor later grows error budgets, compliance reports and burn-rate alerts. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Keep building on the same `{{SloMonitor}}` type: later levels add methods to it.

**Minutes** are whole numbers from `0` up, on the services' own clock. Every range `{{start}}..{{end}}` is **inclusive** and has `0 <= {{start}} <= {{end}}`. A minute without a sample (never sent, or not sent yet) is a minute with **no traffic**: 0 requests, 0 errors.

**Rates** are in **ppm** (parts per million): the pooled rate of a set of minutes is `total errors * 1 000 000 / total requests`, rounded **down** to a whole number. So 5 errors in 300 requests is `16666`. Requests per minute are at most 100 000.

## Level 1: services and samples

| Method | Behaviour |
|---|---|
| `{{add_service}}(service) → bool` | Registers a service with no samples. Returns `false`, changing nothing, if the name is taken. Names are case-sensitive. |
| `{{ingest}}(service, first_minute, requests, errors) → bool` | Records a batch of consecutive minutes: `requests[i]` and `errors[i]` are the sample for minute `first_minute + i`. The pipeline only moves forward: `first_minute` must be **after** the latest minute already recorded for the service. Returns `false`, recording nothing of the batch, if the service doesn't exist, `first_minute` isn't after the latest recorded minute, the two lists are empty or of different lengths, or any minute has more errors than requests. Minutes skipped between batches have no traffic. |
| `{{error_rate}}(service, start, end) → ppm or none` | The pooled error rate of minutes `start..end`. *None* if the service doesn't exist or those minutes have no requests at all. |
| `{{latest_minute}}(service) → minute or none` | The last minute recorded for the service; *none* if the service doesn't exist or has no samples yet. |

### Example

```
{{add_service}}("checkout")                          → true
{{add_service}}("checkout")                          → false
{{ingest}}("checkout", 0, [100, 200, 50], [1, 4, 0]) → true
{{ingest}}("checkout", 2, [80], [2])                 → false   (minute 2 is already recorded)
{{ingest}}("checkout", 5, [100, 40], [3, 0])         → true    (minutes 3 and 4 had no traffic)
{{latest_minute}}("checkout")                        → 6
{{error_rate}}("checkout", 0, 1)                     → 16666   (5 errors in 300 requests)
{{error_rate}}("checkout", 3, 4)                     → none
{{error_rate}}("checkout", 0, 9)                     → 16326   (8 errors in 490 requests)
{{ingest}}("search", 0, [10], [0])                   → false
```

## Checking your work

- **Run** checks your code against one example test per unlocked level and shows which fail and why.
- **Submit** runs the full hidden tests for every level you've unlocked. Passing them all opens the next level.
