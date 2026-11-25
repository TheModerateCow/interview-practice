package search_box

import "sort"

// FewestKeystrokes returns the fewest keystrokes (letter, Backspace, Tab) that make an empty search box show target.
func FewestKeystrokes(log []string, target string) int {
	count := map[string]int{}
	for _, q := range log {
		count[q]++
	}
	kids := []map[byte]int{{}} // trie over the logged queries and the target; node 0 is the empty box
	parent := []int{-1}
	insert := func(word string) int {
		node := 0
		for i := 0; i < len(word); i++ {
			nxt, ok := kids[node][word[i]]
			if !ok {
				nxt = len(kids)
				kids[node][word[i]] = nxt
				kids = append(kids, map[byte]int{})
				parent = append(parent, node)
			}
			node = nxt
		}
		return node
	}
	end := map[string]int{}
	queries := make([]string, 0, len(count))
	for q := range count {
		end[q] = insert(q)
		queries = append(queries, q)
	}
	goal := insert(target)

	// Tab jumps to the most popular logged query under the node (ties: alphabetically first).
	// Visiting queries best-first, the first one to pass through a node is that node's suggestion.
	sort.Slice(queries, func(a, b int) bool {
		if count[queries[a]] != count[queries[b]] {
			return count[queries[a]] > count[queries[b]]
		}
		return queries[a] < queries[b]
	})
	tab := make([]int, len(kids))
	for i := range tab {
		tab[i] = -1
	}
	for _, q := range queries {
		node := 0
		for i := 0; i < len(q); i++ {
			if tab[node] == -1 {
				tab[node] = end[q]
			}
			node = kids[node][q[i]]
		}
		if tab[node] == -1 {
			tab[node] = end[q]
		}
	}

	// Every keystroke costs 1, so BFS over trie nodes. Strings off the trie are dead ends.
	dist := make([]int, len(kids))
	for i := range dist {
		dist[i] = -1
	}
	dist[0] = 0
	todo := []int{0}
	for len(todo) > 0 {
		node := todo[0]
		todo = todo[1:]
		if node == goal {
			return dist[node]
		}
		nexts := []int{}
		for _, nxt := range kids[node] {
			nexts = append(nexts, nxt)
		}
		if parent[node] != -1 {
			nexts = append(nexts, parent[node])
		}
		if tab[node] != -1 {
			nexts = append(nexts, tab[node])
		}
		for _, nxt := range nexts {
			if dist[nxt] == -1 {
				dist[nxt] = dist[node] + 1
				todo = append(todo, nxt)
			}
		}
	}
	return dist[goal]
}
