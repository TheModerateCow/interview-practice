"""Drives the clinic from stdin, one command per line, and prints each result:

    clinician <ts> <id>                              prints true or false
    room <ts> <id>                                   prints true or false
    type <ts> <name> <minutes>                       prints true or false
    book <ts> <clinician> <patient> <type> <start>   prints the appointment id, or (failed)
    cancel <ts> <id>                                 prints true or false
    show <ts> <id>                                   prints the appointment, or (none)

Add your own commands as you build later levels.
"""

import sys

from clinic import Clinic


def main() -> None:
    c = Clinic()
    for line in sys.stdin:
        f = line.split()
        if len(f) < 3:
            continue
        cmd, ts = f[0], int(f[1])
        n = int(f[-1]) if f[-1].lstrip("-").isdigit() else 0
        if cmd == "clinician" and len(f) == 3:
            out = c.add_clinician(ts, f[2])
        elif cmd == "room" and len(f) == 3:
            out = c.add_room(ts, f[2])
        elif cmd == "type" and len(f) == 4:
            out = c.add_type(ts, f[2], n)
        elif cmd == "book" and len(f) == 6:
            out = c.book(ts, f[2], f[3], f[4], n)
            if out is None:
                out = "(failed)"
        elif cmd == "cancel" and len(f) == 3:
            out = c.cancel(ts, f[2])
        elif cmd == "show" and len(f) == 3:
            out = c.appointment(ts, f[2])
            if out is None:
                out = "(none)"
        else:
            out = "unknown command: " + line.rstrip("\n")
        print(str(out).lower() if isinstance(out, bool) else out)


if __name__ == "__main__":
    main()
