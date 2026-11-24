# GradeRow

One hidden-test result per unlocked part: the tag, the count, a meter and, when something fails, the last failing line.

- Provide: `.grade` with `.tag` (mono test tag), `.count` ("3/5"), `.meter` (add `full` at 100%) and optionally `.why` (the last failing assertion, in `fail`). For "did not finish" or "could not be graded" use `count warn` with "—" and a `.status` line.
- During the round show counts and the last failing line only. Add `.names` (failing test names) only after End or time up.
- Group rows under a `label` ("Hidden tests", "My tests").
