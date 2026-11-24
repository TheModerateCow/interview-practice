# Verdict

A Run verdict: a dot plus the judge's exact words, tinted by outcome.

- Provide: `<span class="badge pass|fail|warn">` with one of the six verdicts. Accepted is `pass`; Time Limit Exceeded and Memory Limit Exceeded are `warn`; Wrong Answer, Compile Error and Runtime Error are `fail`.
- Follow it with a `meta` line in mono: runtime, memory, exit code ("12 ms · 9.2 MB · exit 1").
- Never shorten to AC/WA/TLE, never show it without the words.
