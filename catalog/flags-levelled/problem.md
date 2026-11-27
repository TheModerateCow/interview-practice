# Feature flags

You're building the in-memory feature-flag service a product team uses to ship safely: flags switched on or off per environment, specific users targeted, and later gradual rollouts, scheduled launches and an audit trail with rollback. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Everything lives in the `{{FlagService}}` type. Keep building on it: later levels add methods to it.

**Timestamps.** Every method takes `{{ts}}` as its first argument: the time of the call, an integer. Timestamps strictly increase from one call to the next. Level 1 doesn't use them yet, but keep them in the signatures.

**Environments** are plain strings (`"prod"`, `"staging"`, …). Any environment name is valid; a flag starts **off** in every environment, with nobody targeted.

## Level 1: flags, environments and targeting

| Method | Behaviour |
|---|---|
| `{{create_flag}}({{ts}}, {{flag_id}})` | Adds a flag, off in every environment. Returns `false` if `{{flag_id}}` already exists. |
| `{{set_enabled}}({{ts}}, {{flag_id}}, {{env}}, {{on}})` | Switches the flag on (`true`) or off (`false`) in `{{env}}`, for everyone. Returns `false` if the flag doesn't exist. Setting the value it already has still returns `true`. |
| `{{add_target}}({{ts}}, {{flag_id}}, {{env}}, {{user_id}})` | From now on `{{user_id}}` sees the flag **on** in `{{env}}`, even while the flag is off there. Returns `false` if the flag doesn't exist or the user is already targeted in `{{env}}`. |
| `{{remove_target}}({{ts}}, {{flag_id}}, {{env}}, {{user_id}})` | Undoes `{{add_target}}`. Returns `false` if the flag doesn't exist or the user isn't targeted in `{{env}}`. |
| `{{is_enabled}}({{ts}}, {{flag_id}}, {{env}}, {{user_id}})` | Whether `{{user_id}}` sees the flag on in `{{env}}`: `true` if they are targeted in `{{env}}` or the flag is on in `{{env}}`. `false` for an unknown flag. |

Targets belong to one flag in one environment: targeting `ana` on `"dark-mode"` in `"staging"` changes nothing in `"prod"`.

### Example

```
{{create_flag}}(1, "dark-mode")                       -> true
{{set_enabled}}(2, "dark-mode", "prod", true)         -> true
{{is_enabled}}(3, "dark-mode", "prod", "ana")         -> true
{{is_enabled}}(4, "dark-mode", "staging", "ana")      -> false
{{add_target}}(5, "dark-mode", "staging", "ana")      -> true
{{is_enabled}}(6, "dark-mode", "staging", "ana")      -> true    (targeted)
```

## Checking your work

- **Run** checks your code against one example test per unlocked level and shows which fail and why.
- **Submit** runs the full hidden tests for every level you've unlocked. Passing them all opens the next level.

Standard library only.
