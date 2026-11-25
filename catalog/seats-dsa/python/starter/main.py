# Reads "n m", then the n capacities, then m lines "board alight" (any whitespace),
# and prints max_upgrades.
import sys

from upgrades import max_upgrades

tokens = sys.stdin.read().split()
n, m = int(tokens[0]), int(tokens[1])
cap = [int(t) for t in tokens[2:2 + n]]
flat = [int(t) for t in tokens[2 + n:2 + n + 2 * m]]
requests = [[flat[2 * i], flat[2 * i + 1]] for i in range(m)]
print(max_upgrades(cap, requests))
