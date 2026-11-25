# Reads "n budgetPPM", then n request counts, then n error counts (any whitespace),
# and prints longest_compliant_window.
import sys

from alerting import longest_compliant_window

tokens = sys.stdin.read().split()
n, budget = int(tokens[0]), int(tokens[1])
requests = [int(t) for t in tokens[2:2 + n]]
errors = [int(t) for t in tokens[2 + n:2 + 2 * n]]
print(longest_compliant_window(requests, errors, budget))
