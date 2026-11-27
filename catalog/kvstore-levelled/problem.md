# Config store

You're building the in-memory configuration store a cloud platform team uses to hold settings for its services. Each **record** has a key (like `svc-api`) and a set of named **fields** (like `replicas` or `env.PORT`), each holding a string value. The store later grows scans, expiring fields, and backups. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Everything lives in the `{{Store}}` type (created with `{{new Store}}`). Keep building on it: later levels add methods to it.

**Timestamps.** Every method takes `{{ts}}`, an integer, as its first argument: the time of the call. Timestamps strictly increase from one call to the next. Level 1 doesn't use them yet, but keep them in the signatures.

## Level 1: records and fields

| Method | Behaviour |
|---|---|
| `{{set}}({{ts}}, {{key}}, {{field}}, {{value}}) → bool` | Stores `{{value}}` in `{{key}}`'s `{{field}}`, creating the record if needed. Returns `true` if the field had no value before, `false` if an existing value was replaced. |
| `{{get}}({{ts}}, {{key}}, {{field}}) → optional string` | The field's value, or nothing if the record or field doesn't exist. |
| `{{delete}}({{ts}}, {{key}}, {{field}}) → bool` | Removes the field. Returns `true` if it existed, `false` otherwise. A record whose last field is deleted no longer exists. |
| `{{compare_and_set}}({{ts}}, {{key}}, {{field}}, {{expected}}, {{value}}) → bool` | Sets the field to `{{value}}` only if it currently exists and holds exactly `{{expected}}`. Returns whether it changed the field. |

The empty string is a valid value: a field set to `""` exists.

### Example

```
{{set}}(1, "svc-api", "replicas", "3")                → true
{{set}}(2, "svc-api", "replicas", "5")                → false
{{get}}(3, "svc-api", "replicas")                     → "5"
{{compare_and_set}}(4, "svc-api", "replicas", "3", "7") → false   (it holds "5")
{{compare_and_set}}(5, "svc-api", "replicas", "5", "7") → true
{{delete}}(6, "svc-api", "image")                     → false
{{get}}(7, "svc-api", "image")                        → nothing
```

## Checking your work

- **Run** checks your code against one example test per unlocked level and shows which fail and why.
- **Submit** runs the full hidden tests for every level you've unlocked. Passing them all opens the next level.
