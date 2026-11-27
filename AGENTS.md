# Interview Lab: notes for agents (any tool)

## Issue → branch → PR (every change, in order)

1. **Issue first.** Find the open issue for the change or create one (`gh issue create --title … --body …`) before writing code. Its number is `<n>`.
2. **Branch** from fresh `origin/main`, named `<type>/<n>-<kebab-summary>`, with `<type>` one of `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `ci`. Example: `fix/81-runner-container-leak`. A tool-made name (`worktree-…`) gets renamed before the first push: `git branch -m <name>`.
3. **PR as draft** (`gh pr create --draft`), imperative title, body opening with `Closes #<n>`. Any PR that changes code gets the `full-suite` label (command below) so the API and e2e tests run; docs-only PRs skip it.
4. **Green, then ready.** `gh pr checks <pr> --watch` must end with every check passing, none failing or pending, all run on the PR's last commit. On red, fix the cause and push. `full.yml` fires only on the `labeled` event, so after any push remove `full-suite` (`gh api -X DELETE repos/TheModerateCow/interview-practice/issues/<pr>/labels/full-suite`) and add it again to re-run it on the new commit. Re-run a job only when it failed on infrastructure (runner, network), and say so in the PR. Workflows are path-filtered, so a docs-only PR may report no checks; that counts as green. Once green, `gh pr ready <pr>`.

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
