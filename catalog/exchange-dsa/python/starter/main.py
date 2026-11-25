# Reads events from stdin and prints run_book's answers, one per line:
#   m                      (number of events)
#   add <price> <qty> | cancel <price> <qty> | quote <qty> | buy <qty>   (m lines)
import sys

from book import Event, run_book

lines = sys.stdin.read().split("\n")
m = int(lines[0])
events = []
for line in lines[1:m + 1]:
    w = line.split()
    if w[0] in ("add", "cancel"):
        events.append(Event(w[0], int(w[1]), int(w[2])))
    else:
        events.append(Event(w[0], 0, int(w[1])))
for v in run_book(events):
    print(v)
