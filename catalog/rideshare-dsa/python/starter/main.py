# Reads "n m need", then n rider positions, then m driver positions (any whitespace),
# and prints min_dispatch_radius.
import sys

from dispatch import min_dispatch_radius

tokens = sys.stdin.read().split()
n, m, need = int(tokens[0]), int(tokens[1]), int(tokens[2])
riders = [int(t) for t in tokens[3:3 + n]]
drivers = [int(t) for t in tokens[3 + n:3 + n + m]]
print(min_dispatch_radius(riders, drivers, need))
