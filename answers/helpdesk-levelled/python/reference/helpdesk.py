"""Support desk: tickets with priorities, agents and their queues, SLA due times that pause while
a ticket waits on the customer, shift changes and a history of every ticket."""

PRIORITY = {"high": 0, "normal": 1, "low": 2}
SLA = {"high": 60, "normal": 240, "low": 1440}  # minutes to resolve, per priority
MOVES = {("open", "in_progress"), ("in_progress", "open"), ("in_progress", "resolved"), ("resolved", "open"),
         ("in_progress", "waiting"), ("waiting", "in_progress")}


class Desk:
    """Every method takes `ts` first: the time of the call in minutes. Timestamps never decrease."""

    def __init__(self):
        self.agents = {}  # agent -> on shift
        self.tickets = {}  # ticket_id -> {"id", "num", "customer", "priority", "status", "agent", "opened", "paused", "wait_start", "history"}
        self.next_id = 0

    def _put(self, ts, t, agent):
        t["agent"] = agent
        t["history"].append(f"{ts}:assigned:{agent}")

    def _pick(self, ts):
        """The on-shift agent with the fewest unresolved tickets, ties by name; "" if nobody is on shift."""
        on = [a for a, on_shift in self.agents.items() if on_shift]
        return min(on, key=lambda a: (len(self.queue(ts, a)), a), default="")

    def _due(self, ts, t):
        paused = t["paused"] + (ts - t["wait_start"] if t["status"] == "waiting" else 0)
        return t["opened"] + SLA[t["priority"]] + paused

    # ---------------------------------------------------------------- level 1

    def add_agent(self, ts: int, agent: str) -> bool:
        if agent in self.agents:
            return False
        self.agents[agent] = True
        return True

    def open_ticket(self, ts: int, customer: str, priority: str) -> str:
        if priority not in PRIORITY:
            return ""
        self.next_id += 1
        tid = f"t{self.next_id}"
        self.tickets[tid] = {"id": tid, "num": self.next_id, "customer": customer, "priority": priority,
                             "status": "open", "agent": "", "opened": ts, "paused": 0, "wait_start": 0,
                             "history": [f"{ts}:opened"]}
        return tid

    def assign(self, ts: int, ticket_id: str, agent: str) -> bool:
        t = self.tickets.get(ticket_id)
        if t is None or not self.agents.get(agent) or t["status"] == "resolved" or t["agent"] == agent:
            return False
        self._put(ts, t, agent)
        return True

    def set_status(self, ts: int, ticket_id: str, status: str) -> bool:
        t = self.tickets.get(ticket_id)
        if t is None or (t["status"], status) not in MOVES:
            return False
        if status == "in_progress" and not t["agent"]:
            return False
        if status == "waiting":
            t["wait_start"] = ts
        if t["status"] == "waiting":
            t["paused"] += ts - t["wait_start"]
        t["status"] = status
        t["history"].append(f"{ts}:{status}")
        return True

    def get_ticket(self, ts: int, ticket_id: str) -> str:
        t = self.tickets.get(ticket_id)
        if t is None:
            return ""
        return f"{t['customer']}:{t['priority']}:{t['status']}:{t['agent'] or '-'}"

    # ---------------------------------------------------------------- level 2

    def queue(self, ts: int, agent: str) -> list[str]:
        mine = [t for t in self.tickets.values() if t["agent"] == agent and t["status"] != "resolved"]
        mine.sort(key=lambda t: (PRIORITY[t["priority"]], t["num"]))
        return [t["id"] for t in mine]

    def auto_assign(self, ts: int, ticket_id: str) -> str:
        t = self.tickets.get(ticket_id)
        if t is None or t["agent"]:
            return ""
        agent = self._pick(ts)
        if agent:
            self._put(ts, t, agent)
        return agent

    # ---------------------------------------------------------------- level 3

    def due_at(self, ts: int, ticket_id: str) -> int:
        t = self.tickets.get(ticket_id)
        return -1 if t is None else self._due(ts, t)

    def overdue(self, ts: int) -> list[str]:
        late = [t for t in self.tickets.values()
                if t["status"] in ("open", "in_progress") and ts > self._due(ts, t)]
        late.sort(key=lambda t: (self._due(ts, t), t["num"]))
        return [t["id"] for t in late]

    # ---------------------------------------------------------------- level 4

    def end_shift(self, ts: int, agent: str) -> list[str]:
        if not self.agents.get(agent) or not any(on for a, on in self.agents.items() if a != agent):
            return []
        self.agents[agent] = False
        moves = []
        for tid in self.queue(ts, agent):
            to = self._pick(ts)
            self._put(ts, self.tickets[tid], to)
            moves.append(f"{tid}:{to}")
        return moves

    def start_shift(self, ts: int, agent: str) -> bool:
        if agent not in self.agents or self.agents[agent]:
            return False
        self.agents[agent] = True
        return True

    def history(self, ts: int, ticket_id: str) -> list[str]:
        t = self.tickets.get(ticket_id)
        return [] if t is None else list(t["history"])
