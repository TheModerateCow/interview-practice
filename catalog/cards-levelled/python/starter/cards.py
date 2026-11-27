"""A card issuer's authorisation service."""


class Issuer:
    """Every method takes `day` first: today's date as an integer. Days never decrease."""

    def __init__(self):
        pass  # your state here

    def issue_card(self, day: int, card_id: str, limit: int) -> bool:
        """Issues a card with a credit limit in cents. False if card_id exists or limit <= 0."""
        raise NotImplementedError

    def authorize(self, day: int, card_id: str, category: str, amount: int) -> str:
        """Places a hold and returns "a1", "a2", ...; "" if declined."""
        raise NotImplementedError

    def capture(self, day: int, auth_id: str, amount: int) -> bool:
        """Posts amount (up to the authorised amount) and releases the hold. False if it can't."""
        raise NotImplementedError

    def void_auth(self, day: int, auth_id: str) -> bool:
        """Cancels an open authorisation, releasing its hold. False if it isn't open."""
        raise NotImplementedError

    def available(self, day: int, card_id: str) -> int:
        """Limit minus posted minus open holds, in cents; -1 if the card doesn't exist."""
        raise NotImplementedError
