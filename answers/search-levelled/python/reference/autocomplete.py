"""A site search box's autocomplete, built from the query log: popularity, suggestions, top-k lists and
the fewest keystrokes to reach a query."""

from bisect import bisect_left, insort
from collections import Counter, deque


class _Node:
    __slots__ = ("kids", "ranked")

    def __init__(self) -> None:
        self.kids: dict[str, "_Node"] = {}
        # every logged query under this prefix, as (-popularity, query): best suggestion first
        self.ranked: list[tuple[int, str]] = []


class SearchBox:
    """The query log, indexed by prefix."""

    def __init__(self) -> None:
        self._count: dict[str, int] = {}
        self._root = _Node()

    def _path(self, query: str) -> list[_Node]:
        node = self._root
        path = [node]
        for ch in query:
            nxt = node.kids.get(ch)
            if nxt is None:
                nxt = node.kids[ch] = _Node()
            node = nxt
            path.append(node)
        return path

    def _find(self, prefix: str) -> _Node | None:
        node = self._root
        for ch in prefix:
            node = node.kids.get(ch)
            if node is None:
                return None
        return node

    def _set(self, query: str, new: int) -> None:
        """Change query's popularity to new (0 removes it) in every prefix's ranking."""
        old = self._count.get(query, 0)
        for node in self._path(query):
            r = node.ranked
            if old:
                del r[bisect_left(r, (-old, query))]
            if new:
                insort(r, (-new, query))
        if new:
            self._count[query] = new
        else:
            self._count.pop(query, None)

    # level 1

    def log_query(self, query: str) -> int:
        n = self._count.get(query, 0) + 1
        self._set(query, n)
        return n

    def popularity(self, query: str) -> int:
        return self._count.get(query, 0)

    def suggest(self, prefix: str) -> str | None:
        node = self._find(prefix)
        if node is None or not node.ranked:
            return None
        return node.ranked[0][1]

    # level 2

    def delete_query(self, query: str) -> bool:
        if query not in self._count:
            return False
        self._set(query, 0)
        return True

    def merge_queries(self, from_: str, into: str) -> int | None:
        if from_ not in self._count or from_ == into:
            return None
        moved = self._count[from_]
        self._set(from_, 0)
        n = self._count.get(into, 0) + moved
        self._set(into, n)
        return n

    # level 3

    def import_log(self, log: list[str]) -> int:
        # One batch: take the old entries out while every ranking is still sorted, append the new
        # ones, then sort each touched ranking once instead of inserting one by one.
        batch = Counter(log)
        for query in batch:
            old = self._count.get(query, 0)
            if old:
                for node in self._path(query):
                    del node.ranked[bisect_left(node.ranked, (-old, query))]
        touched: dict[int, _Node] = {}
        for query, c in batch.items():
            n = self._count.get(query, 0) + c
            self._count[query] = n
            for node in self._path(query):
                node.ranked.append((-n, query))
                touched[id(node)] = node
        for node in touched.values():
            node.ranked.sort()
        return len(self._count)

    def top_suggestions(self, prefix: str, k: int) -> list[str]:
        node = self._find(prefix)
        if node is None:
            return []
        return ["%s:%d" % (q, -c) for c, q in node.ranked[:k]]

    # level 4

    def fewest_keystrokes(self, target: str) -> int:
        # Each keystroke costs 1: breadth-first over box texts. Only prefixes of logged queries
        # and of the target are worth visiting; any other text can only be backspaced away.
        dist = {"": 0}
        todo = deque([""])
        while todo:
            s = todo.popleft()
            d = dist[s]
            if s == target:
                return d
            nexts = [s[:-1]] if s else []
            node = self._find(s)
            if node is not None and node.ranked:
                nexts.append(node.ranked[0][1])  # Tab
                nexts.extend(s + ch for ch, kid in node.kids.items() if kid.ranked)
            if len(s) < len(target) and target.startswith(s):
                nexts.append(target[: len(s) + 1])
            for n in nexts:
                if n not in dist:
                    dist[n] = d + 1
                    todo.append(n)
        return -1
