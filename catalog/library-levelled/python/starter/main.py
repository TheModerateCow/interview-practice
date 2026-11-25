"""Drives the library from stdin, one command per line, and prints each result
(strings are printed quoted, so an empty result shows as ""; titles are one word here):

    member <ts> <member>
    copy <ts> <copy> <title>
    checkout <ts> <member> <title>
    return <ts> <copy>
    borrower <ts> <copy>

Add your own commands here as you build later levels.
"""

import sys

from library import Library


def main() -> None:
    lib = Library()
    for line in sys.stdin:
        f = line.split()
        if len(f) < 3:
            continue
        cmd, ts = f[0], int(f[1])
        if cmd == "member" and len(f) == 3:
            print(str(lib.add_member(ts, f[2])).lower())
        elif cmd == "copy" and len(f) == 4:
            print(str(lib.add_copy(ts, f[2], f[3])).lower())
        elif cmd == "checkout" and len(f) == 4:
            print(f'"{lib.checkout(ts, f[2], f[3])}"')
        elif cmd == "return" and len(f) == 3:
            print(str(lib.return_copy(ts, f[2])).lower())
        elif cmd == "borrower" and len(f) == 3:
            print(f'"{lib.borrower(ts, f[2])}"')
        else:
            print("unknown command: " + line.rstrip("\n"))


if __name__ == "__main__":
    main()
