# Interview Lab: notes for agents (any tool)

## Testing a change

- Push the branch and open the PR as soon as the change is ready. GitHub CI runs the tests; a quick local check first is optional.
- On a PR, CI runs `catalog.yml` (catalog gates for the problems the diff affects) and `ci.yml` (UI build). The API tests and Playwright e2e (`full.yml` → `tests/run_all.sh`) run only on a PR labelled **`full-suite`**: `gh api -X POST repos/TheModerateCow/interview-practice/issues/<n>/labels -f "labels[]=full-suite"` (`gh pr edit --add-label` currently fails on a Projects-classic GraphQL error).
- Local runs go on the isolated test stack only (`tests/run_all.sh`, port 8766), under the shared lock so parallel sessions queue instead of tearing each other's stack down: `flock /home/ubuntu/.ilab-test.lock tests/run_all.sh`. The dev stack on :8765 and `data/` belong to the owner.
- The owner merges PRs. Leave them open once CI is green.

## Every PR needs snapshot evidence

No PR is ready for review without evidence that the change works, taken from the running app or the real command. Not a claim in words.
- **Frontend change:** screenshots of the app showing the change, before (`main`) and after (this branch). Include dark and light, and ~400 px wide when layout moves.
- **Backend, tooling, test or CI change:** the captured output that proves it, with the command that produced it. That can be an API response (`curl … → JSON`), a test or gate run (`PASS …` / `N passed`), a log line, or a link to the CI job and the lines that matter.
- **Docs-only change:** quote the changed section as it now reads.
- Take evidence on the isolated test stack (:8766) or from CI, never the owner's app on :8765. Look at every screenshot before you link it.
- Put images on the orphan `pr-evidence` branch, one folder per PR number. Link them as `https://github.com/TheModerateCow/interview-practice/blob/pr-evidence/<PR>/<file>?raw=true`, and paste output into the PR body as a code block.
- If something couldn't be captured, say so under "Not checked yet" with the reason. Don't leave it out.
