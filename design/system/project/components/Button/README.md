# Button

Four button levels, ranked by how often and how carefully they are pressed: accent for Submit, outline for frequent actions, ghost for quiet ones, danger for End.

- Provide: a `<button type="button">` with `class="btn btn-<level>"`, a sentence-case verb label, and optionally a `<kbd>` shortcut hint inside it.
- `btn-accent`: Submit only, once per screen. `btn-outline`: Run, My tests. `btn-ghost`: Next part, Export in the toolbar, Cancel. `btn-danger`: End (red text, no fill until hover). `btn-solid`: Start interview and Export on the end card. Add `btn-lg` only to Start interview.
- Disable every action button while a run, submit or end is in progress; show the progress word ("Submitting…") next to them, not inside them.
- Don't add icons, don't make a second accent button, don't use the accent for links.
