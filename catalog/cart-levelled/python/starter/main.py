"""Drives the shop from stdin, one command per line, and prints each result:

    product <ts> <sku> <price_cents> <stock>
    add <ts> <cart> <sku> <qty>
    remove <ts> <cart> <sku> <qty>
    total <ts> <cart>
    items <ts> <cart>

Add your own commands here as you build later levels.
"""

import sys

from shop import Shop


def main() -> None:
    s = Shop()
    for line in sys.stdin:
        f = line.split()
        if len(f) < 3:
            continue
        cmd, ts = f[0], int(f[1])
        if cmd == "product" and len(f) == 5:
            out = s.add_product(ts, f[2], int(f[3]), int(f[4]))
        elif cmd == "add" and len(f) == 5:
            out = s.add_to_cart(ts, f[2], f[3], int(f[4]))
        elif cmd == "remove" and len(f) == 5:
            out = s.remove_from_cart(ts, f[2], f[3], int(f[4]))
        elif cmd == "total" and len(f) == 3:
            out = s.cart_total(ts, f[2])
        elif cmd == "items" and len(f) == 3:
            out = "[" + ", ".join(s.items(ts, f[2])) + "]"
        else:
            out = "unknown command: " + line.rstrip("\n")
        print(str(out).lower() if isinstance(out, bool) else out)


if __name__ == "__main__":
    main()
