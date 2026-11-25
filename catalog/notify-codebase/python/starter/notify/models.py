"""Notification entities, constants and the errors the service raises."""

from __future__ import annotations

from dataclasses import dataclass, field

EMAIL = "email"
PUSH = "push"
SMS = "sms"

SENT = "sent"  # delivered on at least one channel
HELD = "held"  # kept for the user's daily digest
DUPLICATE = "duplicate"  # dropped: same key within DEDUPE_WINDOW

# How long, in seconds, a dedupe key blocks a repeat notification to the same user.
DEDUPE_WINDOW = 3600

# The rolling span, in seconds, that HOURLY_CAP counts over.
CAP_WINDOW = 3600

# The most deliveries a user may get on a channel in any CAP_WINDOW seconds.
HOURLY_CAP = {EMAIL: 6, PUSH: 4, SMS: 2}


class NotifyError(Exception):
    """Base class for every error the service raises."""


class UnknownUser(NotifyError):
    pass


class DuplicateUser(NotifyError):
    pass


class BadChannel(NotifyError):
    """Channels must be email, push or sms, each at most once."""


class BadQuietHours(NotifyError):
    """Quiet hours must be between 0 and 23."""


class BadOffset(NotifyError):
    """UTC offset must be between -720 and 840 minutes."""


class BadNotification(NotifyError):
    """A notification needs a topic and a dedupe key."""


@dataclass
class User:
    id: str
    offset_min: int  # minutes east of UTC; fixed, no daylight saving
    channels: list[str] = field(default_factory=lambda: [EMAIL])  # enabled, in the user's order
    quiet_from: int = 0  # local hour quiet hours start (0-23)
    quiet_to: int = 0  # local hour quiet hours end, exclusive; equal to quiet_from means none


@dataclass
class Notification:
    """One message a product team wants a user to get."""

    user: str
    topic: str  # e.g. "billing", "security"
    key: str  # dedupe key chosen by the sender
    title: str = ""
    at: int = 0  # seconds since the epoch, UTC
    urgent: bool = False  # ignores quiet hours (but not caps)


@dataclass
class Result:
    status: str
    channels: list[str] = field(default_factory=list)  # channels it went out on, in the user's order


@dataclass
class Record:
    """A notification together with what happened to it."""

    notification: Notification
    result: Result


@dataclass
class DigestLine:
    topic: str
    count: int  # held notifications on the topic
    latest: str  # title of the most recent one
