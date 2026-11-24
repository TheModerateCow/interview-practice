# PartChip

One chip per unlocked part or level in the header, so the candidate sees where they are.

- Provide: `<span class="chip done|current">` named from the test tag: `test_p2_` → "Part 2", `test_l3_` → "Level 3". `done` adds a ✓ when every hidden test of that part passed; `current` is the first unfinished part.
- Show only unlocked parts: locked parts are secret, so never show "2 of 4" or a greyed future chip.
- Hide the row when there is one part that hasn't passed yet.
