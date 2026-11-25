"""A feature-flag service: flags switched on or off per environment, with user targeting."""


class FlagService:
    """Every method takes `ts` first: the time of the call. Timestamps only ever increase."""

    def __init__(self):
        pass  # your state here

    def create_flag(self, ts: int, flag_id: str) -> bool:
        """Adds a flag, off in every environment. False if the id already exists."""
        raise NotImplementedError

    def set_enabled(self, ts: int, flag_id: str, env: str, on: bool) -> bool:
        """Switches the flag on or off in env. False if the flag doesn't exist."""
        raise NotImplementedError

    def add_target(self, ts: int, flag_id: str, env: str, user_id: str) -> bool:
        """user_id always sees the flag on in env. False if unknown flag or already targeted there."""
        raise NotImplementedError

    def remove_target(self, ts: int, flag_id: str, env: str, user_id: str) -> bool:
        """Undoes add_target. False if unknown flag or the user isn't targeted in env."""
        raise NotImplementedError

    def is_enabled(self, ts: int, flag_id: str, env: str, user_id: str) -> bool:
        """Whether user_id sees the flag on in env. False for an unknown flag."""
        raise NotImplementedError
