"""Drives the ledger from stdin, one command per line, and prints each result:

    merchant <id> <bps> [<CUR>=<fixed fee> ...]
    capture <ts> <charge> <merchant> <cur> <amount> <card|bank>
    refund <ts> <charge> <amount>
    settle <ts> <merchant>
    post <ts> <account> <cur> <amount> [<account> <cur> <amount> ...]
    payout <ts> <payout> <merchant> <cur> <amount>
    paid <ts> <payout>
    failed <ts> <payout>
    balance <account> <cur>

Amounts are integer minor units. Accounts are names like merchant:m1:available or
platform:fees. Add your own commands as you need them.
"""

import sys

from ledger import Entry, Ledger, LedgerError, Posting, Pricing, format_amount


def handle(l: Ledger, f: list[str]) -> list[str]:
    cmd, a = f[0], f[1:]
    if cmd == "merchant" and len(a) >= 2:
        fixed = {cur: int(v) for cur, _, v in (kv.partition("=") for kv in a[2:])}
        l.add_merchant(a[0], Pricing(int(a[1]), fixed))
    elif cmd == "capture" and len(a) == 6:
        l.capture(a[1], a[2], a[3], int(a[4]), a[5], int(a[0]))
    elif cmd == "refund" and len(a) == 3:
        l.refund(a[1], int(a[2]), int(a[0]))
    elif cmd == "settle" and len(a) == 2:
        return [f"{b.id} {b.currency} gross={b.gross} fees={b.fees} net={b.net} charges={','.join(b.charges)}"
                for b in l.settle(a[1], int(a[0]))]
    elif cmd == "post" and len(a) >= 4 and (len(a) - 1) % 3 == 0:
        l.post(Entry(int(a[0]), [Posting(a[i], a[i + 1], int(a[i + 2])) for i in range(1, len(a), 3)]))
    elif cmd == "payout" and len(a) == 5:
        l.request_payout(a[1], a[2], a[3], int(a[4]), int(a[0]))
    elif cmd == "paid" and len(a) == 2:
        l.payout_paid(a[1], int(a[0]))
    elif cmd == "failed" and len(a) == 2:
        l.payout_failed(a[1], int(a[0]))
    elif cmd == "balance" and len(a) == 2:
        return [format_amount(l.balance(a[0], a[1]), a[1])]
    else:
        return ["unknown command: " + " ".join(f)]
    return ["ok"]


def main() -> None:
    l = Ledger()
    for line in sys.stdin:
        f = line.split()
        if not f:
            continue
        try:
            out = handle(l, f)
        except LedgerError as e:
            out = [f"error: {e}"]
        except ValueError as e:
            out = [f"error: {e}"]
        print("\n".join(out))


if __name__ == "__main__":
    main()
