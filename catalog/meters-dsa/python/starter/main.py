# Reads "n capacity wear", then n half-hourly prices (any whitespace), and prints best_battery_profit.
import sys

from meters import best_battery_profit

tokens = sys.stdin.read().split()
n, capacity, wear = int(tokens[0]), int(tokens[1]), int(tokens[2])
prices = [int(t) for t in tokens[3:3 + n]]
print(best_battery_profit(prices, capacity, wear))
