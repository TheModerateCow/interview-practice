# Reads one pipeline from stdin and prints fastest_release's answer:
#   n k
#   consumer cold warm      (n lines, one per job; consumer -1 is the release)
import sys

from pipeline import Job, fastest_release

vals = list(map(int, sys.stdin.read().split()))
n, k = vals[0], vals[1]
jobs = [Job(*vals[2 + 3 * i : 5 + 3 * i]) for i in range(n)]
print(fastest_release(jobs, k))
