# Quota service

You've joined the team that runs the API platform's gateway. Every call a customer makes goes through this Java code (Java 21, default package, standard library only) before it reaches a backend: it looks up the caller's API key, checks the call against the key's plan, and logs the decision. Billing and the customer dashboard read their usage numbers from the same log.

A **plan** allows `limit` units per fixed window of `window` seconds. Windows are aligned to the epoch (with a 60 s window: `[0, 60)`, `[60, 120)`, ...), and timestamps are whole seconds that never go backwards for a key. Each call has a cost in units. A plan's **burst allowance** lets a key carry over what it left unused in the window just before, up to `burst` units, so a window's capacity is `limit + min(burst, max(0, limit - spent in the previous window))`. A call that doesn't fit is denied, spends nothing, and is told how many seconds remain until the window resets.

The round has three phases: fix the bugs, build the missing feature, then (revealed later) make the hot path fast. Read around before you change anything: the code is small, and causes are rarely in the file where the symptom shows.

## Phase 1: bug report

> **GW-1187: rate-limit escalations from this week**
>
> 1. **Throttled clients stay throttled.** A customer's nightly sync sends a large batch call, gets a 429, then falls back to small calls. Every small call that minute is rejected too, even though the dashboard said they had units left. Their next minute's burst is smaller than it should be as well.
> 2. **Bursty customers get less than they pay for.** Customers on plans with a burst allowance report that after a minute in which they used their burst, the following minute throttles them below their plan's limit.
> 3. **A revoked key came back.** Security revoked a leaked key on Monday. On Tuesday billing moved the customer to a bigger plan, and the leaked key started working again.
>
> Expected: a denied call spends nothing; a window's capacity is never below the plan's `limit`; a revoked key stays revoked whatever else changes on it.

This test reproduces item 3 and fails today. Paste it into a `*Test.java` file to use it:

```java
public class RevokedTest {
    static void testRevokedKeyStaysRevoked() {
        Service s = new Service();
        s.addPlan(new Plan("free", 10, 60, 0));
        s.addPlan(new Plan("team", 100, 60, 20));
        s.issueKey("leaked", "org-7", "free");
        s.revoke("leaked");
        s.changePlan("leaked", "team");
        Expect.raises(QuotaException.class, () -> s.allow("leaked", 30, 1));
    }
}
```

## Phase 2: usage report

`Service.report(org, start, end)` (returns a `List<UsageLine>`) in `Service.java` builds the usage table billing and the dashboard show. It is not implemented yet. It must:

1. Raise `BadRange` unless `end > start`.
2. Count every request logged with `start <= at < end` (allowed or denied) for each key that belongs to `org`, revoked keys included.
3. Produce one `UsageLine` per key that made at least one request in the range; keys with no requests in it get no line. `plan` is the key's plan now; `requests` and `units` count the allowed requests and the units they spent; `denied` counts the denied requests.
4. Order lines by `units`, most first; equal `units` go in key-id order.
5. Return an empty list when there are no lines (an org with no keys included).

Example:

```
plan basic 10 60 4      key a org-1 basic      key b org-1 basic
allow a 0 6   allow a 5 9 (denied)   allow b 10 6   allow b 70 2
report("org-1", 0, 60) -> [a basic 1 6 1, b basic 1 6 0]
```

## Checking your work

- **Run** runs `Main.java`, a small program that reads commands from stdin (`plan`, `key`, `allow`, `usage`, `revoke`, `setplan`, `report`; see the top of the file).
- **My tests** runs your own `*Test.java` files: every `static void` method whose name starts with `test`, checked with `Expect.eq`, `Expect.isTrue` and `Expect.raises` (no JUnit). `ExampleTest.java` is an example to copy; the test above is a good first one to add.
- **Submit** runs the hidden tests for the phases you've unlocked. Phase 3 opens once phase 2 passes, or with 15 minutes left.
