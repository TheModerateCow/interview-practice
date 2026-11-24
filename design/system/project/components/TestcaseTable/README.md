# TestcaseTable

Run results against the set's sample testcases: ✓ or ✗, the input, the expected output and what the program printed.

- Provide: a `<table>` inside `.tbl-wrap` with columns blank · Input · Expected · Got; cells holding program text get `class="mono"` and keep line breaks.
- ✓ uses `ok` (pass), ✗ uses `no` (fail), each with an `aria-label`. Comparison ignores trailing whitespace; say "(output truncated)" when output hit 64 KB.
