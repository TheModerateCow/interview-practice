# Feature flags

You're building the in-memory feature-flag service a product team uses to ship safely: flags switched on or off per environment, specific users targeted, and later gradual rollouts, scheduled launches and an audit trail with rollback. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Everything lives in `flags.py`, in the class `FlagService`. Keep building on the same class: later levels add methods to it.

**Timestamps.** Every method takes `ts: int` as its first argument: the time of the call, an integer. Timestamps strictly increase from one call to the next. Level 1 doesn't use them yet, but keep them in the signatures.

**Environments** are plain strings (`"prod"`, `"staging"`, …). Any environment name is valid; a flag starts **off** in every environment, with nobody targeted.

## Level 1: flags, environments and targeting

| Method | Behaviour |
|---|---|
| `create_flag(ts, flag_id) -> bool` | Adds a flag, off in every environment. Returns `False` if `flag_id` already exists. |
| `set_enabled(ts, flag_id, env, on) -> bool` | Switches the flag on (`True`) or off (`False`) in `env`, for everyone. Returns `False` if the flag doesn't exist. Setting the value it already has still returns `True`. |
| `add_target(ts, flag_id, env, user_id) -> bool` | From now on `user_id` sees the flag **on** in `env`, even while the flag is off there. Returns `False` if the flag doesn't exist or the user is already targeted in `env`. |
| `remove_target(ts, flag_id, env, user_id) -> bool` | Undoes `add_target`. Returns `False` if the flag doesn't exist or the user isn't targeted in `env`. |
| `is_enabled(ts, flag_id, env, user_id) -> bool` | Whether `user_id` sees the flag on in `env`: `True` if they are targeted in `env` or the flag is on in `env`. `False` for an unknown flag. |

Targets belong to one flag in one environment: targeting `ana` on `"dark-mode"` in `"staging"` changes nothing in `"prod"`.

### Example

```
create_flag(1, "dark-mode")                       -> True
set_enabled(2, "dark-mode", "prod", True)         -> True
is_enabled(3, "dark-mode", "prod", "ana")         -> True
is_enabled(4, "dark-mode", "staging", "ana")      -> False
add_target(5, "dark-mode", "staging", "ana")      -> True
is_enabled(6, "dark-mode", "staging", "ana")      -> True    (targeted)
```

## Checking your work

- **Run** runs `main.py`, a small program that reads commands from stdin (`create`, `set`, `target`, `untarget`, `check`; see the top of the file). Extend it as you go.
- **My tests** runs your own `test_*.py` files with pytest. `test_example.py` is an example to copy.
- **Submit** runs the hidden tests for every level you've unlocked.

Python standard library only.
