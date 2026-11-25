# Reads "n days duration quorum", then for each attendee "offset work_start work_end m" followed by m pairs
# "start end" (any whitespace), and prints earliest_quorum_slot (or -1).
import sys

from scheduler import Attendee, earliest_quorum_slot

tokens = iter(int(t) for t in sys.stdin.read().split())
n, days, duration, quorum = next(tokens), next(tokens), next(tokens), next(tokens)
attendees = []
for _ in range(n):
    offset, work_start, work_end, m = next(tokens), next(tokens), next(tokens), next(tokens)
    busy = [[next(tokens), next(tokens)] for _ in range(m)]
    attendees.append(Attendee(offset, work_start, work_end, busy))
print(earliest_quorum_slot(attendees, days, duration, quorum))
