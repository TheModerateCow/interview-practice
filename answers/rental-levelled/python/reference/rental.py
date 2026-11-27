"""Fleet desk for a car-rental company: cars by class and branch, rentals with daily rates and
late fees, one-way drop-offs, and reservations made ahead of time."""

RATES = {"economy": 3000, "compact": 4500, "suv": 7000}  # cents per day
DROP_FEE = 5000
DAY = 24  # hours


def _days(hours):
    """Whole days started: 1 to 24 hours is 1 day, 25 is 2."""
    return -(-hours // DAY)


class RentalDesk:
    """Every method takes `ts` first: the time of the call in hours. Timestamps only ever increase."""

    def __init__(self):
        self.cars = {}  # car_id -> {"class", "branch", "out": None | {"customer", "start", "due"}}
        self.branches = set()
        self.paid = {}  # customer -> cents
        self.reservations = {}  # reservation_id -> {"customer", "branch", "class", "start", "end", "used"}
        self.next_res = 0

    def _free(self, branch, car_class):
        """Ids of the cars of car_class parked at branch, lowest first."""
        return sorted(c for c, v in self.cars.items()
                      if v["out"] is None and v["branch"] == branch and v["class"] == car_class)

    def _has_car(self, customer):
        return any(v["out"] is not None and v["out"]["customer"] == customer for v in self.cars.values())

    def _pending(self, ts, branch, car_class, start, end):
        """Reservations not yet picked up that overlap [start, end); start >= ts, so a lapsed one never does."""
        return sum(1 for r in self.reservations.values()
                   if not r["used"] and r["branch"] == branch and r["class"] == car_class
                   and r["start"] < end and start < r["end"])

    # ---------------------------------------------------------------- level 1

    def add_car(self, ts: int, car_id: str, car_class: str, branch: str) -> bool:
        if car_id in self.cars or car_class not in RATES:
            return False
        self.cars[car_id] = {"class": car_class, "branch": branch, "out": None}
        self.branches.add(branch)
        return True

    def rent(self, ts: int, customer: str, branch: str, car_class: str, days: int) -> str:
        if car_class not in RATES or days <= 0 or self._has_car(customer):
            return ""
        due = ts + DAY * days
        free = self._free(branch, car_class)
        if len(free) <= self._pending(ts, branch, car_class, ts, due):
            return ""
        self.cars[free[0]]["out"] = {"customer": customer, "start": ts, "due": due}
        return free[0]

    def return_car(self, ts: int, car_id: str) -> bool:
        car = self.cars.get(car_id)
        if car is None or car["out"] is None:
            return False
        return self.drop_off(ts, car_id, car["branch"])

    def status(self, ts: int, car_id: str) -> str:
        car = self.cars.get(car_id)
        if car is None:
            return ""
        if car["out"] is not None:
            return f"rented:{car['out']['customer']}"
        return f"available:{car['branch']}"

    # ---------------------------------------------------------------- level 2

    def charges(self, ts: int, customer: str) -> int:
        return self.paid.get(customer, 0)

    def overdue(self, ts: int) -> list[str]:
        late = [(v["out"]["due"], c) for c, v in self.cars.items() if v["out"] is not None and v["out"]["due"] < ts]
        return [f"{c}({self.cars[c]['out']['customer']})" for _, c in sorted(late)]

    # ---------------------------------------------------------------- level 3

    def drop_off(self, ts: int, car_id: str, branch: str) -> bool:
        car = self.cars.get(car_id)
        if car is None or car["out"] is None or branch not in self.branches:
            return False
        out = car["out"]
        days = max(1, _days(ts - out["start"])) + _days(max(0, ts - out["due"]))
        fee = days * RATES[car["class"]] + (DROP_FEE if branch != car["branch"] else 0)
        self.paid[out["customer"]] = self.paid.get(out["customer"], 0) + fee
        car["branch"] = branch
        car["out"] = None
        return True

    def available(self, ts: int, branch: str) -> list[str]:
        counts = {}
        for v in self.cars.values():
            if v["out"] is None and v["branch"] == branch:
                counts[v["class"]] = counts.get(v["class"], 0) + 1
        return [f"{c}({n})" for c, n in sorted(counts.items())]

    # ---------------------------------------------------------------- level 4

    def reserve(self, ts: int, customer: str, branch: str, car_class: str, start: int, days: int) -> str:
        if car_class not in RATES or days <= 0 or start < ts:
            return ""
        end = start + DAY * days
        fleet = sum(1 for v in self.cars.values() if v["branch"] == branch and v["class"] == car_class)
        if self._pending(ts, branch, car_class, start, end) >= fleet:
            return ""
        self.next_res += 1
        rid = f"r{self.next_res}"
        self.reservations[rid] = {"customer": customer, "branch": branch, "class": car_class,
                                  "start": start, "end": end, "used": False}
        return rid

    def pick_up(self, ts: int, reservation_id: str) -> str:
        r = self.reservations.get(reservation_id)
        if r is None or r["used"] or not r["start"] <= ts < r["end"] or self._has_car(r["customer"]):
            return ""
        free = self._free(r["branch"], r["class"])
        if not free:
            return ""
        r["used"] = True
        self.cars[free[0]]["out"] = {"customer": r["customer"], "start": ts, "due": r["end"]}
        return free[0]
