"""Support desk for a customer-support team."""


class Desk:
    """Every method takes `ts` first: the time of the call in minutes. Timestamps never decrease."""

    def __init__(self):
        pass  # your state here

    def add_agent(self, ts: int, agent: str) -> bool:
        """Adds a support agent. False if the agent already exists."""
        raise NotImplementedError

    def open_ticket(self, ts: int, customer: str, priority: str) -> str:
        """Opens a ticket and returns "t1", "t2", ...; "" if priority isn't high, normal or low."""
        raise NotImplementedError

    def assign(self, ts: int, ticket_id: str, agent: str) -> bool:
        """Gives the ticket to agent. False if either is unknown, the ticket is resolved or already agent's."""
        raise NotImplementedError

    def set_status(self, ts: int, ticket_id: str, status: str) -> bool:
        """Moves the ticket to status if that move is allowed; False otherwise."""
        raise NotImplementedError

    def get_ticket(self, ts: int, ticket_id: str) -> str:
        """"customer:priority:status:agent" (agent "-" if none); "" if unknown."""
        raise NotImplementedError
