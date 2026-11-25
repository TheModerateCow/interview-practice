"""In-memory storage: users, posts, the follow graph, mutes and likes."""

from __future__ import annotations

import bisect
from collections import defaultdict

from .models import DuplicatePost, Mute, Post, UnknownPost, UnknownUser


def _post_order(post: Post) -> tuple[int, str]:
    return (post.created_at, post.id)


def _created(post: Post) -> int:
    return post.created_at


class MemoryStore:
    """Everything one feed region knows, held in memory."""

    def __init__(self) -> None:
        self._users: set[str] = set()
        self._posts: dict[str, Post] = {}
        # Each author's posts, oldest first (by created_at, then id).
        self._by_author: dict[str, list[Post]] = defaultdict(list)
        self._following: dict[str, set[str]] = defaultdict(set)
        self._mutes: dict[str, dict[str, Mute]] = defaultdict(dict)
        self._likes: set[tuple[str, str]] = set()

    # users ---------------------------------------------------------------

    def add_user(self, user_id: str) -> None:
        self._users.add(user_id)

    def require_user(self, user_id: str) -> None:
        if user_id not in self._users:
            raise UnknownUser(f"no such user: {user_id}")

    # posts ---------------------------------------------------------------

    def add_post(self, post: Post) -> None:
        if post.id in self._posts:
            raise DuplicatePost(f"post already exists: {post.id}")
        self._posts[post.id] = post
        bisect.insort(self._by_author[post.author], post, key=_post_order)

    def get_post(self, post_id: str) -> Post:
        try:
            return self._posts[post_id]
        except KeyError:
            raise UnknownPost(f"no such post: {post_id}") from None

    def posts_by(self, author: str, start: int, end: int) -> list[Post]:
        """The author's posts with start <= created_at <= end, oldest first."""
        posts = self._by_author.get(author, [])
        lo = bisect.bisect_left(posts, start, key=_created)
        hi = bisect.bisect_right(posts, end, key=_created)
        return posts[lo:hi]

    # likes ---------------------------------------------------------------

    def add_like(self, post_id: str, user_id: str) -> bool:
        """Record user_id liking post_id. Returns False if it was already recorded."""
        post = self.get_post(post_id)
        if (post_id, user_id) in self._likes:
            return False
        self._likes.add((post_id, user_id))
        post.likes += 1
        return True

    # follows and mutes ---------------------------------------------------

    def follow(self, follower: str, followee: str) -> None:
        self._following[follower].add(followee)

    def unfollow(self, follower: str, followee: str) -> None:
        self._following[follower].discard(followee)

    def following(self, user_id: str) -> set[str]:
        return set(self._following.get(user_id, ()))

    def set_mute(self, viewer: str, mute: Mute) -> None:
        """Store a mute, replacing any earlier mute of the same account."""
        self._mutes[viewer][mute.target] = mute

    def mutes(self, viewer: str) -> list[Mute]:
        return list(self._mutes.get(viewer, {}).values())
