"""Drives the store from stdin, one command per line, and prints each result:

    set <ts> <key> <field> <value>
    get <ts> <key> <field>                 prints the value, or (none)
    delete <ts> <key> <field>
    cas <ts> <key> <field> <expected> <value>

Values are single words here. Add your own commands as you build later levels.
"""

import sys

from configstore import Store


def main() -> None:
    s = Store()
    for line in sys.stdin:
        f = line.split()
        if len(f) < 2:
            continue
        cmd, ts = f[0], int(f[1])
        if cmd == "set" and len(f) == 5:
            out = s.set(ts, f[2], f[3], f[4])
        elif cmd == "get" and len(f) == 4:
            v = s.get(ts, f[2], f[3])
            out = "(none)" if v is None else v
        elif cmd == "delete" and len(f) == 4:
            out = s.delete(ts, f[2], f[3])
        elif cmd == "cas" and len(f) == 6:
            out = s.compare_and_set(ts, f[2], f[3], f[4], f[5])
        else:
            out = "unknown command: " + line.rstrip("\n")
        print(str(out).lower() if isinstance(out, bool) else out)


if __name__ == "__main__":
    main()
