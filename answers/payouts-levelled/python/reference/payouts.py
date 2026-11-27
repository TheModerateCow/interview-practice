"""Settlement service for a marketplace: merchants, sales, refunds, payouts, reserves and chargebacks."""

SETTLE_DAYS = 3
CHARGEBACK_FEE = 1500


def _fee(amount, bps):
    return (amount * bps + 5000) // 10000  # basis points, half a cent rounds up


class Payouts:
    """Every method takes `day` first: today's date as an integer. Days never decrease."""

    def __init__(self):
        self.merchants = {}
        self.sales = {}
        self.next_sale = 0

    def _post(self, m, day, kind, amount):
        """A debit (refund, payout, chargeback): it counts at once."""
        m["entries"].append([day, amount, False])
        m["log"].append(f"{day}:{kind}:{amount}")

    # ---------------------------------------------------------------- level 1

    def add_merchant(self, day, merchant_id, fee_bps):
        if merchant_id in self.merchants or not 0 <= fee_bps <= 10000:
            return False
        # entries: [settle_day, amount, is_reserve]
        self.merchants[merchant_id] = {"bps": fee_bps, "reserve_bps": 0, "hold": 0, "entries": [], "log": [], "paid": []}
        return True

    def record_sale(self, day, merchant_id, amount):
        m = self.merchants.get(merchant_id)
        if m is None or amount <= 0:
            return ""
        self.next_sale += 1
        sale_id = f"s{self.next_sale}"
        fee = _fee(amount, m["bps"])
        net = amount - fee
        reserve = _fee(net, m["reserve_bps"])
        m["entries"].append([day + SETTLE_DAYS, net - reserve, False])
        if reserve:
            m["entries"].append([day + m["hold"], reserve, True])
        m["log"].append(f"{day}:sale:{net}")
        self.sales[sale_id] = {"merchant": merchant_id, "amount": amount, "refunded": 0, "fee": fee, "charged_back": False}
        return sale_id

    def fee(self, day, sale_id):
        s = self.sales.get(sale_id)
        return -1 if s is None else s["fee"]

    def balance(self, day, merchant_id):
        m = self.merchants.get(merchant_id)
        return 0 if m is None else sum(e[1] for e in m["entries"])

    # ---------------------------------------------------------------- level 2

    def refund(self, day, sale_id, amount):
        s = self.sales.get(sale_id)
        if s is None or s["charged_back"] or amount <= 0 or amount > s["amount"] - s["refunded"]:
            return -1
        m = self.merchants[s["merchant"]]
        s["refunded"] += amount
        new_fee = _fee(s["amount"] - s["refunded"], m["bps"])
        debit = amount - (s["fee"] - new_fee)
        s["fee"] = new_fee
        self._post(m, day, "refund", -debit)
        return debit

    def activity(self, day, merchant_id):
        m = self.merchants.get(merchant_id)
        return [] if m is None else list(m["log"])

    # ---------------------------------------------------------------- level 3

    def available(self, day, merchant_id):
        m = self.merchants.get(merchant_id)
        return 0 if m is None else sum(e[1] for e in m["entries"] if e[0] <= day)

    def run_payouts(self, day):
        out = []
        for mid in sorted(self.merchants):
            m = self.merchants[mid]
            a = self.available(day, mid)
            if a > 0:
                self._post(m, day, "payout", -a)
                m["paid"].append(f"{day}:{a}")
                out.append(f"{mid}:{a}")
        return out

    def payout_history(self, day, merchant_id):
        m = self.merchants.get(merchant_id)
        return [] if m is None else list(m["paid"])

    # ---------------------------------------------------------------- level 4

    def set_reserve(self, day, merchant_id, reserve_bps, hold_days):
        m = self.merchants.get(merchant_id)
        if m is None or not 0 <= reserve_bps <= 10000 or hold_days < 1:
            return False
        m["reserve_bps"], m["hold"] = reserve_bps, hold_days
        return True

    def reserve_held(self, day, merchant_id):
        m = self.merchants.get(merchant_id)
        return 0 if m is None else sum(e[1] for e in m["entries"] if e[2] and e[0] > day)

    def chargeback(self, day, sale_id):
        s = self.sales.get(sale_id)
        if s is None or s["charged_back"] or s["refunded"] == s["amount"]:
            return -1
        s["charged_back"] = True
        debit = s["amount"] - s["refunded"] + CHARGEBACK_FEE
        self._post(self.merchants[s["merchant"]], day, "chargeback", -debit)
        return debit
