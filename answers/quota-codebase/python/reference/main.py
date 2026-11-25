"""Drives the quota service from stdin, one command per line, and prints each
result (or "error: ..."):

    plan <name> <limit> <windowSeconds> <burst>
    key <id> <org> <plan>
    allow <key> <now> <cost>     prints "allowed <remaining>" or "denied <remaining> retry <seconds>"
    usage <key> <now>            prints "<used>/<limit>"
    revoke <key>
    setplan <key> <plan>
    report <org> <from> <to>     prints one "<key> <plan> <requests> <units> <denied>" line per key

Add your own commands here if they help.
"""

import sys

from quota import Plan, QuotaError, Service


def handle(s: Service, f: list[str]) -> list[str]:
    cmd, a = f[0], f[1:]
    if cmd == "plan" and len(a) == 4:
        s.add_plan(Plan(a[0], int(a[1]), int(a[2]), int(a[3])))
    elif cmd == "key" and len(a) == 3:
        s.issue_key(*a)
    elif cmd == "allow" and len(a) == 3:
        d = s.allow(a[0], int(a[1]), int(a[2]))
        if d.allowed:
            return [f"allowed {d.remaining}"]
        return [f"denied {d.remaining} retry {d.retry_after}"]
    elif cmd == "usage" and len(a) == 2:
        used, limit = s.usage(a[0], int(a[1]))
        return [f"{used}/{limit}"]
    elif cmd == "revoke" and len(a) == 1:
        s.revoke(a[0])
    elif cmd == "setplan" and len(a) == 2:
        s.change_plan(a[0], a[1])
    elif cmd == "report" and len(a) == 3:
        return [f"{l.key_id} {l.plan} {l.requests} {l.units} {l.denied}" for l in s.report(a[0], int(a[1]), int(a[2]))]
    else:
        return ["unknown command: " + " ".join(f)]
    return ["ok"]


def main() -> None:
    s = Service()
    for line in sys.stdin:
        f = line.split()
        if not f:
            continue
        try:
            out = handle(s, f)
        except (QuotaError, ValueError) as e:
            out = [f"error: {e}"]
        for o in out:
            print(o)


if __name__ == "__main__":
    main()
