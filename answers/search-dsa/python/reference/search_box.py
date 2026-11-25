from collections import Counter, deque


def fewest_keystrokes(log, target):
    """Fewest keystrokes (letter, Backspace, Tab) to make an empty search box show `target`."""
    count = Counter(log)
    kids, parent = [{}], [-1]  # trie over the logged queries and the target; node 0 is the empty box

    def insert(word):
        node = 0
        for ch in word:
            nxt = kids[node].get(ch)
            if nxt is None:
                nxt = len(kids)
                kids[node][ch] = nxt
                kids.append({})
                parent.append(node)
            node = nxt
        return node

    end = {q: insert(q) for q in count}
    goal = insert(target)

    # Tab jumps to the most popular logged query under the node (ties: alphabetically first).
    # Visiting queries best-first, the first one to pass through a node is that node's suggestion.
    tab = [-1] * len(kids)
    for q in sorted(count, key=lambda q: (-count[q], q)):
        node = 0
        for ch in q:
            if tab[node] == -1:
                tab[node] = end[q]
            node = kids[node][ch]
        if tab[node] == -1:
            tab[node] = end[q]

    # Every keystroke costs 1, so BFS over trie nodes. Strings off the trie are dead ends.
    dist = [-1] * len(kids)
    dist[0] = 0
    todo = deque([0])
    while todo:
        node = todo.popleft()
        if node == goal:
            return dist[node]
        nexts = list(kids[node].values())
        if parent[node] != -1:
            nexts.append(parent[node])
        if tab[node] != -1:
            nexts.append(tab[node])
        for nxt in nexts:
            if dist[nxt] == -1:
                dist[nxt] = dist[node] + 1
                todo.append(nxt)
    return dist[goal]
