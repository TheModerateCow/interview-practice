# Search box: fewest keystrokes with autocomplete

The site's search box autocompletes from the query log. A query's **popularity** is how many times it appears in
the log. For the current box text `s`, the **suggestion** is the most popular logged query that starts with `s`
(`s` itself counts if it was logged; ties go to the alphabetically first query). The empty box starts with every
query, so its suggestion is the most popular query overall. If no logged query starts with `s`, there is none.

Implement `{{fewest_keystrokes}}({{log}}, {{target}})`: the box starts empty; return the fewest
keystrokes that make it show exactly `{{target}}`. Each keystroke costs 1 and is one of:

- **a letter**: appends that letter to the box;
- **Backspace**: removes the last letter (does nothing on an empty box);
- **Tab**: replaces the box text with its suggestion (does nothing if there is no suggestion).

### Example

```
log = ["shoes", "shirts", "shoes", "shirt", "shirts", "shorts", "shirts"], target = "shirtless"
answer: 6
```

`shirts` is searched 3 times, more than anything else, so Tab in the empty box gives `shirts` (1 keystroke).
Backspace leaves `shirt` (2), then type `l`, `e`, `s`, `s` (6). Typing all nine letters would take 9.

### Constraints

- `1 <= len(log) <= 10^5`; every query and `{{target}}` is 1 to 30 lowercase letters `a`-`z`
- The log holds at most `3 * 10^5` letters in total; `{{target}}` need not be in the log.

## Checking your work

- **Run** runs `{{run_entry}}`. It reads the number of logged searches `n`, then `n` queries one per line, then the
  target, and prints your answer.
- **My tests** runs your own `{{your_tests}}` files. The example test is one to copy.
- **Submit** runs the hidden tests, including one large log (13,500 searches of up to 30 letters).
