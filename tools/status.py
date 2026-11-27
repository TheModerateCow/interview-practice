"""status.py <set_dir | session.json> — time left in an Interview Lab round, clock.py style. Never guess; run this."""

import json
import os
import sys
import time
from pathlib import Path

p = sys.argv[1]
s = json.loads(Path(os.path.join(p, "session.json") if os.path.isdir(p) else p).read_text())
if not s.get("start"):
    sys.exit('{"started": false}')
now = s["ended"] or time.time()
used = (now - s["start"]) / 60
left = s["minutes"] - used
print(
    json.dumps(
        {
            "used_min": round(used, 1),
            "left_min": round(max(left, 0), 1),
            "expired": left <= 0,
            "ended": bool(s.get("ended")),
            "unlocked": s.get("unlocked"),
            "events": s["events"],
        }
    )
)
