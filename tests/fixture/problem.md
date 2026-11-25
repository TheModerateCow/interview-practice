# Harness fixture

Not a real round: it exercises every feature of the shared-case format.

- `{{net_by_account}}` sums each {{Entry}}'s `{{amount_cents}}` per `{{account_id}}`, sorted by account id; zero sums stay.
- `{{max_window}}` is the largest sum of `k` consecutive values; `k` outside `1..len(values)` fails with {{invalid_window}}.
- `{{first_negative}}` is the index of the first negative value, or nothing.
- `{{grid}}` is an `n`×`n` grid holding 1..n² row by row.
- `{{new Wallet}}` starts empty. `{{deposit}}` and `{{withdraw}}` fail with {{invalid_amount}} for amounts ≤ 0;
  `{{withdraw}}` fails with {{insufficient_funds}} beyond the balance and returns the new balance. `{{owner_name}}`, `{{balance}}`.
- Level 2: `{{history}}` lists `+<cents>` / `-<cents>` per successful deposit/withdrawal; `{{freeze}}` makes later
  deposits and withdrawals fail with {{wallet_frozen}}; `{{frozen}}` says whether it is frozen.
