# Interview Lab: notes for agents (any tool)

## Testing a change

- Push the branch and open the PR as soon as the change is ready. GitHub CI runs the tests; a quick local check first is optional.
- On a PR, CI runs `catalog.yml` (catalog gates for the problems the diff affects) and `ci.yml` (UI build). The API tests and Playwright e2e (`full.yml` → `tests/run_all.sh`) run only on a PR labelled **`full-suite`**: `gh api -X POST repos/TheModerateCow/interview-practice/issues/<n>/labels -f "labels[]=full-suite"` (`gh pr edit --add-label` currently fails on a Projects-classic GraphQL error).
- Local runs go on the isolated test stack only (`tests/run_all.sh`, port 8766), under the shared lock so parallel sessions queue instead of tearing each other's stack down: `flock /home/ubuntu/.ilab-test.lock tests/run_all.sh`. The dev stack on :8765 and `data/` belong to the owner.
- The owner merges PRs. Leave them open once CI is green.
