# Config store

You're building the in-memory configuration store a cloud platform team uses to hold settings for its services. Each **record** has a key (like `svc-api`) and a set of named **fields** (like `replicas` or `env.PORT`), each holding a string value. The store later grows scans, expiring fields, and backups. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Everything lives in package `configstore`, in `store.go`. Keep building on the same `Store` type: later levels add methods to it.

**Timestamps.** Every method takes `ts int` as its first argument: the time of the call. Timestamps strictly increase from one call to the next. Level 1 doesn't use them yet, but keep them in the signatures.

## Level 1: records and fields

| Method | Behaviour |
|---|---|
| `Set(ts int, key, field, value string) bool` | Stores `value` in `key`'s `field`, creating the record if needed. Returns `true` if the field had no value before, `false` if an existing value was replaced. |
| `Get(ts int, key, field string) (string, bool)` | The field's value and `true`, or `"", false` if the record or field doesn't exist. |
| `Delete(ts int, key, field string) bool` | Removes the field. Returns `true` if it existed, `false` otherwise. A record whose last field is deleted no longer exists. |
| `CompareAndSet(ts int, key, field, expected, value string) bool` | Sets the field to `value` only if it currently exists and holds exactly `expected`. Returns whether it changed the field. |

The empty string is a valid value: a field set to `""` exists.

### Example

```
Set(1, "svc-api", "replicas", "3")                -> true
Set(2, "svc-api", "replicas", "5")                -> false
Get(3, "svc-api", "replicas")                     -> "5", true
CompareAndSet(4, "svc-api", "replicas", "3", "7") -> false   (it holds "5")
CompareAndSet(5, "svc-api", "replicas", "5", "7") -> true
Delete(6, "svc-api", "image")                     -> false
Get(7, "svc-api", "image")                        -> "", false
```

## Checking your work

- **Run** runs `cmd/run/main.go`, a small program that reads commands from stdin (`set`, `get`, `delete`, `cas`; see the top of the file). Extend it as you go.
- **My tests** runs your own `*_test.go` files. `store_example_test.go` is an example to copy.
- **Submit** runs the hidden tests for every level you've unlocked.
