def run_book(events):
    """Replays ask-book events; returns one number per "quote" and "buy" event, in order."""
    prices = sorted({e[1] for e in events if e[0] in ("add", "cancel")})
    n = len(prices)
    level = {p: i + 1 for i, p in enumerate(prices)}
    shares = [0] * (n + 1)    # Fenwick tree: shares resting per level
    notional = [0] * (n + 1)  # Fenwick tree: price * shares per level
    resting = [0] * (n + 1)   # plain shares per level
    top = 1 << n.bit_length()
    total = 0
    out = []

    def change(i, dq):
        resting[i] += dq
        dn = dq * prices[i - 1]
        while i <= n:
            shares[i] += dq
            notional[i] += dn
            i += i & -i

    def sweep(q):
        # 0 < q <= total: the level holding the q-th cheapest share, the cost of
        # all shares on cheaper levels, and how many shares come from that level.
        pos, got, cost, step = 0, 0, 0, top
        while step:
            nxt = pos + step
            if nxt <= n and got + shares[nxt] < q:
                pos = nxt
                got += shares[nxt]
                cost += notional[nxt]
            step >>= 1
        return pos + 1, cost, q - got

    for e in events:
        kind = e[0]
        if kind == "add":
            change(level[e[1]], e[2])
            total += e[2]
        elif kind == "cancel":
            change(level[e[1]], -e[2])
            total -= e[2]
        elif kind == "quote":
            if e[1] > total:
                out.append(-1)
            else:
                k, cost, part = sweep(e[1])
                out.append(cost + part * prices[k - 1])
        else:  # buy: fill what is there, the rest is cancelled
            q = min(e[1], total)
            if q == 0:
                out.append(0)
                continue
            k, cost, part = sweep(q)
            out.append(cost + part * prices[k - 1])
            while True:  # empty every cheaper level; each emptied level was paid for by an add
                j = sweep(1)[0]
                if j == k:
                    break
                change(j, -resting[j])
            change(k, -part)
            total -= q
    return out
