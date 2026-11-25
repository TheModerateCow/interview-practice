"""Plain data types and errors for the quota service."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Plan:
    """A pricing tier's rate limit: `limit` units per fixed window of `window`
    seconds, plus up to `burst` units the key left unused in the window before."""

    name: str
    limit: int
    window: int
    burst: int = 0


@dataclass(frozen=True)
class Key:
    """An API key issued to an organisation."""

    id: str
    org: str
    plan: str
    revoked: bool = False


@dataclass(frozen=True)
class Event:
    """One request the limiter decided on."""

    at: int  # seconds since the epoch
    cost: int  # units the request asked for
    allowed: bool = False


@dataclass(frozen=True)
class Decision:
    """The limiter's answer to one request."""

    allowed: bool
    remaining: int  # units left in the current window after this request
    retry_after: int = 0  # seconds until the window resets; 0 when allowed


@dataclass(frozen=True)
class UsageLine:
    """One key's row in an organisation's usage report."""

    key_id: str
    plan: str
    requests: int  # allowed requests
    units: int  # units spent by allowed requests
    denied: int  # requests the limiter rejected


class QuotaError(Exception):
    """Base class for every error the service raises."""


class UnknownKey(QuotaError):
    def __init__(self) -> None:
        super().__init__("unknown api key")


class DuplicateKey(QuotaError):
    def __init__(self) -> None:
        super().__init__("api key already exists")


class Revoked(QuotaError):
    def __init__(self) -> None:
        super().__init__("api key revoked")


class UnknownPlan(QuotaError):
    def __init__(self) -> None:
        super().__init__("unknown plan")


class DuplicatePlan(QuotaError):
    def __init__(self) -> None:
        super().__init__("plan already exists")


class InvalidPlan(QuotaError):
    def __init__(self) -> None:
        super().__init__("plan needs a positive limit and window and a non-negative burst")


class BadCost(QuotaError):
    def __init__(self) -> None:
        super().__init__("request cost must be positive")


class BadRange(QuotaError):
    def __init__(self) -> None:
        super().__init__("report range must end after it starts")
