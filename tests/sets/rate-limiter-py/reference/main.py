import sys
from limiter import RateLimiter

rl = RateLimiter(2, 10)
for line in sys.stdin:
    if line.strip():
        key, ts = line.split()
        print(rl.allow(key, int(ts)))
