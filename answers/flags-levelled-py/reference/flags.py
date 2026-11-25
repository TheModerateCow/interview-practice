"""A feature-flag service: flags switched on or off per environment, user targeting,
percentage rollouts, scheduled changes and an audit history with rollback."""


def _bucket(flag_id: str, user_id: str) -> int:
    """Stable bucket in [0, 100) for a user of a flag."""
    h = 0
    for ch in flag_id + ":" + user_id:
        h = (h * 31 + ord(ch)) % 1000000007
    return h % 100


class _Env:
    def __init__(self):
        self.on = False
        self.rollout = 100
        self.targets = set()
        self.evals = 0
        self.state_log = []  # (time, on) after each on/off change
        self.rollout_log = []  # (time, percent) after each rollout change


class FlagService:
    """Every flag and its environments. Timestamps passed to its methods only ever increase."""

    def __init__(self):
        self.flags = {}  # flag_id -> {env: _Env}
        self.schedules = {}  # schedule id -> dict
        self.next_seq = 1

    # ------------------------------------------------------------ level 1

    def create_flag(self, ts: int, flag_id: str) -> bool:
        """Adds a flag, off in every environment. False if the id already exists."""
        self._advance(ts)
        if flag_id in self.flags:
            return False
        self.flags[flag_id] = {}
        return True

    def set_enabled(self, ts: int, flag_id: str, env: str, on: bool) -> bool:
        """Switches the flag on or off in env. False if the flag doesn't exist."""
        self._advance(ts)
        e = self._env(flag_id, env)
        if e is None:
            return False
        self._apply(e, ts, on)
        return True

    def add_target(self, ts: int, flag_id: str, env: str, user_id: str) -> bool:
        """user_id always sees the flag on in env. False if unknown flag or already targeted."""
        self._advance(ts)
        e = self._env(flag_id, env)
        if e is None or user_id in e.targets:
            return False
        e.targets.add(user_id)
        return True

    def remove_target(self, ts: int, flag_id: str, env: str, user_id: str) -> bool:
        """Undoes add_target. False if unknown flag or the user isn't targeted in env."""
        self._advance(ts)
        e = self._env(flag_id, env)
        if e is None or user_id not in e.targets:
            return False
        e.targets.remove(user_id)
        return True

    def is_enabled(self, ts: int, flag_id: str, env: str, user_id: str) -> bool:
        """Whether user_id sees the flag on in env. False for an unknown flag."""
        self._advance(ts)
        e = self._env(flag_id, env)
        if e is None:
            return False
        e.evals += 1
        return self._sees(flag_id, e, user_id)

    # ------------------------------------------------------------ level 2

    def set_rollout(self, ts: int, flag_id: str, env: str, percent: int) -> bool:
        """Only percent% of non-targeted users see the flag when on. False if unknown flag or percent outside 0..100."""
        self._advance(ts)
        e = self._env(flag_id, env)
        if e is None or type(percent) is not int or not 0 <= percent <= 100:
            return False
        e.rollout = percent
        e.rollout_log.append((ts, percent))
        return True

    def enabled_flags(self, ts: int, env: str, user_id: str) -> list:
        """Ids of every flag user_id sees on in env, ascending."""
        self._advance(ts)
        return sorted(f for f in self.flags if self._sees(f, self._env(f, env), user_id))

    def most_evaluated(self, ts: int, env: str, n: int) -> list:
        """Up to n flags as "flag(count)" by is_enabled calls in env: most first, ties by id ascending."""
        self._advance(ts)
        rows = [(f, envs[env].evals) for f, envs in self.flags.items() if env in envs and envs[env].evals > 0]
        rows.sort(key=lambda r: (-r[1], r[0]))
        return [f"{f}({c})" for f, c in rows[:max(0, n)]]

    # ------------------------------------------------------------ level 3

    def schedule_change(self, ts: int, flag_id: str, env: str, on: bool, at_ts: int) -> str:
        """Schedules set_enabled(at_ts, flag_id, env, on). Returns "s1", "s2", ...; "" if unknown flag or at_ts <= ts."""
        self._advance(ts)
        if flag_id not in self.flags or at_ts <= ts:
            return ""
        seq = self.next_seq
        self.next_seq += 1
        sid = f"s{seq}"
        self.schedules[sid] = {"id": sid, "seq": seq, "flag": flag_id, "env": env, "on": on, "at": at_ts, "done": False}
        return sid

    def cancel_schedule(self, ts: int, schedule_id: str) -> bool:
        """Cancels a pending scheduled change. False if unknown, already applied or already cancelled."""
        self._advance(ts)
        s = self.schedules.get(schedule_id)
        if s is None or s["done"]:
            return False
        del self.schedules[schedule_id]
        return True

    def pending(self, ts: int, flag_id: str) -> list:
        """Ids of the flag's pending scheduled changes, by at_ts, ties in the order scheduled."""
        self._advance(ts)
        return [s["id"] for s in self._due(float("inf")) if s["flag"] == flag_id]

    # ------------------------------------------------------------ level 4

    def history(self, ts: int, flag_id: str, env: str) -> list:
        """Every on/off change of the flag in env as "time:on" / "time:off", oldest first."""
        self._advance(ts)
        e = self._env(flag_id, env)
        if e is None:
            return []
        return [f"{t}:{'on' if on else 'off'}" for t, on in e.state_log]

    def rollback(self, ts: int, flag_id: str, env: str, to_ts: int) -> bool:
        """Restores on/off and rollout in env to what they were after every change at or before to_ts."""
        self._advance(ts)
        e = self._env(flag_id, env)
        if e is None:
            return False
        on, percent = False, 100
        for t, v in e.state_log:
            if t <= to_ts:
                on = v
        for t, v in e.rollout_log:
            if t <= to_ts:
                percent = v
        self._apply(e, ts, on)
        e.rollout = percent
        e.rollout_log.append((ts, percent))
        return True

    # ------------------------------------------------------------ internals

    def _env(self, flag_id, env):
        envs = self.flags.get(flag_id)
        if envs is None:
            return None
        return envs.setdefault(env, _Env())

    def _sees(self, flag_id, e, user_id):
        if user_id in e.targets:
            return True
        return e.on and _bucket(flag_id, user_id) < e.rollout

    def _apply(self, e, time, on):
        e.on = on
        e.state_log.append((time, on))

    def _due(self, ts):
        """Pending scheduled changes due at or before ts, by at_ts then scheduling order."""
        due = [s for s in self.schedules.values() if not s["done"] and s["at"] <= ts]
        return sorted(due, key=lambda s: (s["at"], s["seq"]))

    def _advance(self, ts):
        """Applies every scheduled change due at or before ts, before the call at ts runs."""
        for s in self._due(ts):
            s["done"] = True
            self._apply(self._env(s["flag"], s["env"]), s["at"], s["on"])
