# Toast

A short, temporary message at the bottom right for events the candidate should notice without stopping: a new part unlocked, an import that failed.

- Provide: `.toast` with one sentence; add `bad` for failures. It disappears after 5 seconds and has `role="status"`.
- Use it for news, never for results: results go to the results pane.
