"""Drives the dispatcher from stdin, one command per line, and prints each result (or "error: ..."):

    courier <id> <x> <y> <capacity>
    order <id> <restaurantX> <restaurantY> <customerX> <customerY> <placedAt> <prepMinutes>
    assign <order>
    advance <order> <picked_up|delivered|cancelled>
    eta <order> <now>
    dispatch <now>
    bag <courier>

Add your own commands here if they help.
"""

import sys

from dispatch import DispatchError, Dispatcher, Point, State


def handle(d: Dispatcher, f: list[str]) -> str:
    cmd, a = f[0], f[1:]
    if cmd == "courier" and len(a) == 4:
        d.add_courier(a[0], Point(int(a[1]), int(a[2])), int(a[3]))
    elif cmd == "order" and len(a) == 7:
        d.place_order(a[0], Point(int(a[1]), int(a[2])), Point(int(a[3]), int(a[4])), int(a[5]), int(a[6]))
    elif cmd == "assign" and len(a) == 1:
        return d.assign(a[0])
    elif cmd == "advance" and len(a) == 2:
        try:
            to = State(a[1])
        except ValueError:
            return f"error: unknown state {a[1]}"
        d.advance(a[0], to)
    elif cmd == "eta" and len(a) == 2:
        return str(d.eta(a[0], int(a[1])))
    elif cmd == "dispatch" and len(a) == 1:
        return "[" + " ".join(f"{x.order_id}->{x.courier_id}" for x in d.dispatch_pending(int(a[0]))) + "]"
    elif cmd == "bag" and len(a) == 1:
        return "[" + " ".join(d.courier_orders(a[0])) + "]"
    else:
        return "unknown command: " + " ".join(f)
    return "ok"


def main() -> None:
    d = Dispatcher()
    for line in sys.stdin:
        f = line.split()
        if not f:
            continue
        try:
            print(handle(d, f))
        except (DispatchError, ValueError) as e:
            print("error:", e)


if __name__ == "__main__":
    main()
