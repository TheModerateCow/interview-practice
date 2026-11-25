# Build pipeline: warm the right caches

A monorepo's release pipeline is a fan-in of `n` jobs: each job's artifact is used by exactly **one** downstream
job, `{{consumer}}`, except the release job, whose `{{consumer}}` is `-1`. A job starts as soon as every job that feeds it
has finished (runners are unlimited, so independent jobs run in parallel) and takes `{{cold}}` minutes.

Before the run you may pre-warm the build cache of **at most `{{k}}`** jobs. A warmed job takes `{{warm}}` minutes instead
(`{{warm}} <= {{cold}}`); it still waits for its inputs.

Implement `{{fastest_release}}`: the fewest minutes from the start until the
release job finishes. If the consumer links contain a cycle, the pipeline is invalid: return `-1`.

### Example

```
k=2   job: consumer cold warm
       0:  -1      5    2     (release)
       1:   0     10    3
       2:   0     10    4
       3:   1      2    2
answer: 10
```

Cold, the release waits for jobs 1 and 2 (3 then 1 takes 12; 2 takes 10) and finishes at 17. With one slot the
best is the release (12 + 2 = 14): warming job 1 alone still leaves job 2's 10 minutes in the way. With both slots
on jobs 1 and 2, the inputs are ready at max(2 + 3, 4) = 5 and the release finishes at 5 + 5 = 10.

### Constraints

- `1 <= n <= 5000`, `0 <= k <= 100` (`{{k}}` may exceed `n`), `0 <= {{warm}} <= {{cold}} <= 10^6`
- `{{consumer}}` is `-1` or a job index; at most one job has `{{consumer}} == -1`. A job may name itself (a cycle).
- If no job has `{{consumer}} == -1`, the links must contain a cycle: return `-1`.

## Checking your work

- **Run** runs `{{run_entry}}`. It reads `n k`, then `n` lines `consumer cold warm`, and prints your answer.
- **My tests** runs your own `{{your_tests}}` files. The starter includes an example test to copy.
- **Submit** runs the hidden tests, including one large pipeline (5000 jobs, `k = 100`).
