# Reads events from stdin and prints run_book's answers, one per line:
#   m                      (number of events)
#   add <price> <qty> | cancel <price> <qty> | quote <qty> | buy <qty>   (m lines)
import sys

from book import run_book

lines = sys.stdin.read().split("\n")
m = int(lines[0])
events = []
for line in lines[1:m + 1]:
    w = line.split()
    events.append((w[0],) + tuple(int(x) for x in w[1:]))
for v in run_book(events):
    print(v)
