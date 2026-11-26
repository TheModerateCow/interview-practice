"""store clock rules: minutes left freeze at the close; "after time" is judged against the close (or the deadline).
Run: python3 tests/unit/test_clock.py"""
import os, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ILAB_DATA"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.join(ROOT, "backend"))
from lab.store import clock, closed, cutoff, late, log  # noqa: E402

now = time.time()
running = {"start": now - 10 * 60, "minutes": 30, "ended": None, "events": []}
used, left, expired = clock(running)
assert abs(used - 10) < 0.01 and abs(left - 20) < 0.01 and not expired and not closed(running)

overdue = {"start": now - 40 * 60, "minutes": 30, "ended": None}
assert clock(overdue)[1:] == (0, True) and closed(overdue)          # left never goes negative

ended = {"start": now - 25 * 60, "minutes": 30, "ended": now - 20 * 60, "events": []}
assert abs(clock(ended)[1] - 25) < 0.01 and not clock(ended)[2] and closed(ended)   # frozen at the End press
print("PASS clock: used/left/expired, frozen at the close")

assert cutoff(running) == running["start"] + 30 * 60 and cutoff(ended) == ended["ended"]
assert not late(ended, ended["ended"]) and late(ended, ended["ended"] + 1)
log(ended, "submit", now); log(running, "run", now)
assert ended["events"][-1] == [25.0, "submit (after time)"] and running["events"][-1] == [10.0, "run"]
print("PASS late: judged against the close; the event log marks it")
