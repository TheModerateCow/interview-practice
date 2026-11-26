# ConfirmBar

An inline confirmation that replaces its trigger button in the toolbar; the app never uses browser dialogs.

- Provide: `<span class="confirm-inline">` with one sentence saying what will happen, the confirming button (same verb as the trigger) and a ghost cancel button. Add `danger` for End.
- Focus the cancel button when the bar opens, so Enter does not end the interview by accident.
- End: "End now? Hidden tests run one last time and the clock stops." with **End interview** / **Keep going**. Next part: "Show the next part now? This is logged as asked to move on." with **Show it** / **Cancel**.
- Motion: the bar rises in over `dur` when it replaces its trigger, and goes at once.
