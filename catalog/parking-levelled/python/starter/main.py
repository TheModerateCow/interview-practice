"""Drives the garage from stdin, one command per line, and prints each result
(strings are printed quoted, so an empty result shows as ""):

    add <ts> <spot> <size>
    park <ts> <plate> <size>
    leave <ts> <plate>
    spot <ts> <plate>

Add your own commands here as you build later levels.
"""

import sys

from parking import Garage


def main() -> None:
    g = Garage()
    for line in sys.stdin:
        f = line.split()
        if len(f) < 3:
            continue
        cmd, ts = f[0], int(f[1])
        if cmd == "add" and len(f) == 4:
            out = str(g.add_spot(ts, f[2], f[3])).lower()
        elif cmd == "park" and len(f) == 4:
            out = '"' + g.park(ts, f[2], f[3]) + '"'
        elif cmd == "leave" and len(f) == 3:
            out = str(g.leave(ts, f[2])).lower()
        elif cmd == "spot" and len(f) == 3:
            out = '"' + g.spot_of(ts, f[2]) + '"'
        else:
            out = "unknown command: " + line.rstrip("\n")
        print(out)


if __name__ == "__main__":
    main()
