# Timer

The round clock, the loudest number on screen: mm:ss in Geist Mono with tabular figures.

- Provide: `<span class="timer" role="timer">` with the time left; add `low` in the last 5 minutes (yellow `timer-low-bg` block) and `over` at 00:00 (`fail`).
- In the header it sits right of the part chips, preceded by a `label` reading "left", at 28px; 36px (`timer` style) elsewhere.
- It never starts by itself: only Start interview starts it. Never animate or blink it.
