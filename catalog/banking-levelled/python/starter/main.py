"""Drives the bank from stdin, one command per line, and prints each result:

    open <ts> <id>
    deposit <ts> <id> <amount>          prints the new balance, or (failed)
    withdraw <ts> <id> <amount>         prints the new balance, or (failed)
    transfer <ts> <from> <to> <amount>  prints the sender's new balance, or (failed)
    balance <ts> <id>                   prints the balance, or (none)

Add your own commands as you build later levels.
"""

import sys

from bank import Bank


def show(v, none="(failed)") -> str:
    return none if v is None else str(v)


def main() -> None:
    b = Bank()
    for line in sys.stdin:
        f = line.split()
        if len(f) < 2:
            continue
        cmd, ts = f[0], int(f[1])
        if cmd == "open" and len(f) == 3:
            out = str(b.open_account(ts, f[2])).lower()
        elif cmd == "deposit" and len(f) == 4:
            out = show(b.deposit(ts, f[2], int(f[3])))
        elif cmd == "withdraw" and len(f) == 4:
            out = show(b.withdraw(ts, f[2], int(f[3])))
        elif cmd == "transfer" and len(f) == 5:
            out = show(b.transfer(ts, f[2], f[3], int(f[4])))
        elif cmd == "balance" and len(f) == 3:
            out = show(b.balance(ts, f[2]), "(none)")
        else:
            out = "unknown command: " + line.rstrip("\n")
        print(out)


if __name__ == "__main__":
    main()
