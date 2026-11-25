"""Drives the box office from stdin, one command per line, and prints each result:

    create <ts> <event> <capacity>
    buy <ts> <event> <buyer> <qty>
    refund <ts> <event> <buyer> <qty>
    available <ts> <event>

Add your own commands here as you build later levels.
"""

import sys

from tickets import Office


def main() -> None:
    o = Office()
    for line in sys.stdin:
        f = line.split()
        if len(f) < 3:
            continue
        cmd, ts = f[0], int(f[1])
        if cmd == "create" and len(f) == 4:
            out = o.create_event(ts, f[2], int(f[3]))
        elif cmd == "buy" and len(f) == 5:
            out = o.buy(ts, f[2], f[3], int(f[4]))
        elif cmd == "refund" and len(f) == 5:
            out = o.refund(ts, f[2], f[3], int(f[4]))
        elif cmd == "available" and len(f) == 3:
            out = o.available(ts, f[2])
        else:
            out = "unknown command: " + line.rstrip("\n")
        print(str(out).lower() if isinstance(out, bool) else out)


if __name__ == "__main__":
    main()
