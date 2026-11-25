"""Drives the inventory service from stdin, one command per line, and prints each
result (or "error: ..."):

    warehouse <id>
    rule <warehouse> <sku> <min> <max> <pack>
    receive <ts> <warehouse> <bin> <sku> <qty>
    reserve <ts> <id> <warehouse> <sku> <qty> <ttl>
    release <ts> <id>
    commit <ts> <id>
    transfer <ts> <id> <from> <to> <sku> <qty>
    arrive <ts> <transfer> <bin>
    available <ts> <warehouse> <sku>
    onhand <warehouse> <sku>
    bin <warehouse> <bin> <sku>
    replenish <ts> <warehouse>

Times are Unix seconds; ttl is in seconds. Add your own commands as you need them.
"""

import sys

from inventory import InventoryError, Rule, Service


def handle(s: Service, f: list[str]) -> str:
    cmd, a = f[0], f[1:]
    if cmd == "warehouse" and len(a) == 1:
        s.add_warehouse(a[0])
    elif cmd == "rule" and len(a) == 5:
        s.set_rule(a[0], a[1], Rule(int(a[2]), int(a[3]), int(a[4])))
    elif cmd == "receive" and len(a) == 5:
        s.receive(a[1], a[2], a[3], int(a[4]), int(a[0]))
    elif cmd == "reserve" and len(a) == 6:
        s.reserve(a[1], a[2], a[3], int(a[4]), int(a[5]), int(a[0]))
    elif cmd == "release" and len(a) == 2:
        s.release(a[1], int(a[0]))
    elif cmd == "commit" and len(a) == 2:
        s.commit(a[1], int(a[0]))
    elif cmd == "transfer" and len(a) == 6:
        s.start_transfer(a[1], a[2], a[3], a[4], int(a[5]), int(a[0]))
    elif cmd == "arrive" and len(a) == 3:
        s.receive_transfer(a[1], a[2], int(a[0]))
    elif cmd == "available" and len(a) == 3:
        return str(s.available(a[1], a[2], int(a[0])))
    elif cmd == "onhand" and len(a) == 2:
        return str(s.on_hand(a[0], a[1]))
    elif cmd == "bin" and len(a) == 3:
        return str(s.bin_qty(a[0], a[1], a[2]))
    elif cmd == "replenish" and len(a) == 2:
        plan = s.replenishment(a[1], int(a[0]))
        if not plan:
            return "nothing to replenish"
        return "\n".join(f"{g.sku} position={g.position} qty={g.qty} from={g.source or 'supplier'}" for g in plan)
    else:
        return "unknown command: " + " ".join(f)
    return "ok"


def main() -> None:
    s = Service()
    for line in sys.stdin:
        f = line.split()
        if not f:
            continue
        try:
            print(handle(s, f))
        except (InventoryError, ValueError) as e:
            print("error:", e)


if __name__ == "__main__":
    main()
