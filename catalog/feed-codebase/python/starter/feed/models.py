"""Feed entities and the errors the service raises."""

from __future__ import annotations

from dataclasses import dataclass


class FeedError(Exception):
    """Base class for every error the feed service raises."""


class UnknownUser(FeedError):
    """The user id has never been registered."""


class UnknownPost(FeedError):
    """The post id does not exist."""


class DuplicatePost(FeedError):
    """A post with this id was already published."""


class BadCursor(FeedError):
    """The pagination cursor was not produced by this service."""


@dataclass
class Post:
    """One published post. Times are whole seconds since the epoch."""

    id: str
    author: str
    created_at: int
    text: str = ""
    likes: int = 0


@dataclass(frozen=True)
class Mute:
    """A viewer's mute of one account. ``until`` is None for a permanent mute."""

    target: str
    until: int | None = None

    @classmethod
    def starting(cls, target: str, now: int, hours: float | None) -> Mute:
        """A mute set at ``now`` lasting ``hours`` hours (forever if None)."""
        if hours is None:
            return cls(target)
        return cls(target, now + round(hours * 60))

    def active(self, now: int) -> bool:
        return self.until is None or now < self.until


@dataclass(frozen=True)
class Page:
    """One page of a feed: post ids in order, and the cursor for the next page."""

    post_ids: list[str]
    next_cursor: str | None
