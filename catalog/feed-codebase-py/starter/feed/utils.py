"""Ranking and cursor helpers shared by the feed service."""

from __future__ import annotations

import base64
import binascii
import math

from .models import BadCursor

#: Recency worth one doubling of a post's likes, in seconds.
DECAY_SECONDS = 6 * 60 * 60

#: How far back the home feed looks, in seconds.
FEED_WINDOW = 7 * 24 * 60 * 60


def hot_score(likes: int, created_at: int) -> float:
    """Ranking score: each doubling of likes is worth DECAY_SECONDS of recency."""
    return math.log2(1 + likes) + created_at / DECAY_SECONDS


def rank_key(score: float, post_id: str) -> tuple[float, str]:
    """Sort key for feed order: highest score first, then lowest post id."""
    return (-score, post_id)


def encode_cursor(score: float, post_id: str) -> str:
    """Opaque token for the position just after the post with this score and id."""
    raw = f"{score:.4f}|{post_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(token: str) -> tuple[float, str]:
    """Inverse of encode_cursor. Raises BadCursor for anything it did not make."""
    try:
        score, post_id = base64.urlsafe_b64decode(token.encode()).decode().split("|", 1)
        return float(score), post_id
    except (binascii.Error, UnicodeDecodeError, ValueError) as e:
        raise BadCursor(f"bad cursor: {token!r}") from e
