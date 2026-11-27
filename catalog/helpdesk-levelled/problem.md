# Support desk

You're building the in-memory ticket desk for a customer-support team. It opens tickets, hands them to agents and tracks their status, and later grows agent queues, response-time targets and shift changes. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Everything lives in the `{{Desk}}` type. Keep building on it: later levels add methods to it. Standard library only.

**Timestamps.** Every method takes `ts` as its first argument: the time of the call, in minutes. Timestamps never decrease from one call to the next (several calls can share one). Level 1 doesn't use `ts` yet, but keep it in the signatures.

**Priorities** are exactly `"high"`, `"normal"` and `"low"` (lower case).

## Level 1: tickets, agents and status

| Method | Behaviour |
|---|---|
| `{{add_agent}}(ts, agent) → bool` | Adds a support agent. Returns `false` if `agent` already exists. |
| `{{open_ticket}}(ts, customer, priority) → string` | Opens a ticket for `customer` and returns its id. Ids are `"t1"`, `"t2"`, `"t3"`, … in order; a failed call uses no id. A new ticket is `"open"` with no agent. Returns `""` if `priority` isn't one of the three priorities. |
| `{{assign}}(ts, ticket_id, agent) → bool` | Gives the ticket to `agent`, replacing any previous agent; its status doesn't change. Returns `false`, changing nothing, if the ticket or the agent doesn't exist, the ticket is `"resolved"`, or it's already `agent`'s. |
| `{{set_status}}(ts, ticket_id, status) → bool` | Moves the ticket to `status`. Only these moves are allowed: `"open"` → `"in_progress"` (the ticket must have an agent), `"in_progress"` → `"open"`, `"in_progress"` → `"resolved"`, and `"resolved"` → `"open"` (reopening; the agent stays). Returns `false`, changing nothing, for anything else: an unknown ticket or status, the status it already has, or a move not in the list (`"open"` can't jump straight to `"resolved"`). |
| `{{get_ticket}}(ts, ticket_id) → string` | `"customer:priority:status:agent"`, with `-` as the agent while there is none. `""` if the ticket doesn't exist. |

### Example

```
{{add_agent}}(1, "maya")                    → true
{{open_ticket}}(2, "acme", "high")          → "t1"
{{open_ticket}}(3, "globex", "urgent")      → ""      (not a priority)
{{set_status}}(4, "t1", "in_progress")      → false   (nobody assigned)
{{assign}}(5, "t1", "maya")                 → true
{{set_status}}(6, "t1", "in_progress")      → true
{{open_ticket}}(7, "initech", "low")        → "t2"
{{set_status}}(8, "t2", "resolved")         → false   (open can't jump to resolved)
{{set_status}}(9, "t1", "resolved")         → true
{{get_ticket}}(10, "t1")                    → "acme:high:resolved:maya"
```

## Checking your work

- **Run** checks your code against one example test per unlocked level and shows which fail and why.
- **Submit** runs the full hidden tests for every level you've unlocked. Passing them all opens the next level.
