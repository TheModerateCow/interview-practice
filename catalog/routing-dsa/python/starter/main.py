# Reads one network from stdin and prints fastest_delivery's answer:
#   n m capacity charge
#   rate_0 rate_1 ... rate_{n-1}
#   a b minutes energy      (m lines, one per road)
import sys

from route import Road, fastest_delivery

tokens = sys.stdin.read().split()
n, m, capacity, charge = (int(t) for t in tokens[:4])
rate = [int(t) for t in tokens[4:4 + n]]
p = 4 + n
roads = []
for _ in range(m):
    a, b, minutes, energy = (int(t) for t in tokens[p:p + 4])
    roads.append(Road(a, b, minutes, energy))
    p += 4
print(fastest_delivery(n, capacity, charge, rate, roads))
