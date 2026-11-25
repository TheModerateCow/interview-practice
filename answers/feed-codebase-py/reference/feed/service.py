"""The home-feed service: publishing, follows, mutes, likes and the ranked feed."""

from __future__ import annotations

from .models import FeedError, Mute, Page, Post
from .storage import MemoryStore
from .utils import FEED_WINDOW, decode_cursor, encode_cursor, hot_score, rank_key

#: Most posts one account may contribute to a catch-up list.
CATCH_UP_PER_AUTHOR = 2

_Ranked = list[tuple[tuple[float, str], Post]]


class FeedService:
    """Home feed for one region. Times are whole seconds since the epoch."""

    def __init__(self, store: MemoryStore | None = None) -> None:
        self._store = store if store is not None else MemoryStore()

    # accounts ------------------------------------------------------------

    def add_user(self, user_id: str) -> None:
        self._store.add_user(user_id)

    def follow(self, follower: str, followee: str) -> None:
        self._store.require_user(follower)
        self._store.require_user(followee)
        if follower == followee:
            raise FeedError("cannot follow yourself")
        self._store.follow(follower, followee)

    def unfollow(self, follower: str, followee: str) -> None:
        self._store.require_user(follower)
        self._store.unfollow(follower, followee)

    def mute(self, viewer: str, target: str, now: int, hours: float | None = None) -> None:
        """Hide target's posts from viewer, for ``hours`` hours or (None) for good."""
        self._store.require_user(viewer)
        self._store.require_user(target)
        self._store.set_mute(viewer, Mute.starting(target, now, hours))

    # posts ---------------------------------------------------------------

    def publish(self, post_id: str, author: str, created_at: int, text: str = "") -> Post:
        self._store.require_user(author)
        post = Post(post_id, author, created_at, text)
        self._store.add_post(post)
        return post

    def post(self, post_id: str) -> Post:
        return self._store.get_post(post_id)

    def like(self, post_id: str, user_id: str) -> int:
        """Record a like (idempotent per user) and return the post's like count."""
        self._store.require_user(user_id)
        self._store.add_like(post_id, user_id)
        return self._store.get_post(post_id).likes

    # feeds ---------------------------------------------------------------

    def home_feed(self, viewer: str, now: int, limit: int = 10, cursor: str | None = None) -> Page:
        """One page of the viewer's ranked home feed. See problem.md for the rules."""
        if limit < 1:
            raise ValueError("limit must be at least 1")
        self._store.require_user(viewer)
        ranked = self._ranked(self._sources(viewer, now) | {viewer}, now - FEED_WINDOW, now)
        if cursor is not None:
            after = rank_key(*decode_cursor(cursor))
            ranked = [r for r in ranked if r[0] > after]
        page = ranked[:limit]
        next_cursor = None
        if len(ranked) > limit:
            (neg_score, post_id), _ = page[-1]
            next_cursor = encode_cursor(-neg_score, post_id)
        return Page([post.id for _, post in page], next_cursor)

    def catch_up(self, viewer: str, since: int, now: int, limit: int = 5) -> list[str]:
        """The "while you were away" list. See problem.md for the rules."""
        if limit < 1:
            raise ValueError("limit must be at least 1")
        self._store.require_user(viewer)
        start = max(since + 1, now - FEED_WINDOW)
        picked: list[str] = []
        per_author: dict[str, int] = {}
        for _, post in self._ranked(self._sources(viewer, now), start, now):
            count = per_author.get(post.author, 0)
            if count < CATCH_UP_PER_AUTHOR:
                per_author[post.author] = count + 1
                picked.append(post.id)
                if len(picked) == limit:
                    break
        return picked

    # internals -----------------------------------------------------------

    def _sources(self, viewer: str, now: int) -> set[str]:
        """Accounts the viewer follows, minus those muted at ``now``."""
        muted = {m.target for m in self._store.mutes(viewer) if m.active(now)}
        return self._store.following(viewer) - muted

    def _ranked(self, authors: set[str], start: int, end: int) -> _Ranked:
        """Posts by these authors published in [start, end], in feed order."""
        ranked = [
            (rank_key(hot_score(p.likes, p.created_at), p.id), p)
            for author in authors
            for p in self._store.posts_by(author, start, end)
        ]
        ranked.sort(key=lambda r: r[0])
        return ranked
