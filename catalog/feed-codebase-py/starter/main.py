"""Drives the feed service from stdin, one command per line, and prints each
result (or "error: ..."):

    user <id>
    follow <follower> <followee>
    unfollow <follower> <followee>
    mute <viewer> <target> <now> [hours]
    post <id> <author> <created_at> [text ...]
    like <post> <user>                     prints the like count
    feed <viewer> <now> <limit>            first page: [ids] more|end
    more <viewer> <now> <limit>            the page after the viewer's last feed/more
    catchup <viewer> <since> <now> [limit]

Add your own commands here if they help.
"""

import sys

from feed import FeedError, FeedService


def handle(svc: FeedService, cursors: dict, f: list[str]) -> str:
    cmd, a = f[0], f[1:]
    if cmd == "user" and len(a) == 1:
        svc.add_user(a[0])
    elif cmd == "follow" and len(a) == 2:
        svc.follow(a[0], a[1])
    elif cmd == "unfollow" and len(a) == 2:
        svc.unfollow(a[0], a[1])
    elif cmd == "mute" and len(a) in (3, 4):
        svc.mute(a[0], a[1], int(a[2]), float(a[3]) if len(a) == 4 else None)
    elif cmd == "post" and len(a) >= 3:
        svc.publish(a[0], a[1], int(a[2]), " ".join(a[3:]))
    elif cmd == "like" and len(a) == 2:
        return str(svc.like(a[0], a[1]))
    elif cmd in ("feed", "more") and len(a) == 3:
        if cmd == "more" and cursors.get(a[0]) is None:
            return "[] end"
        page = svc.home_feed(a[0], int(a[1]), int(a[2]), cursors.get(a[0]) if cmd == "more" else None)
        cursors[a[0]] = page.next_cursor
        return "[" + " ".join(page.post_ids) + "] " + ("more" if page.next_cursor else "end")
    elif cmd == "catchup" and len(a) in (3, 4):
        ids = svc.catch_up(a[0], int(a[1]), int(a[2]), *([int(a[3])] if len(a) == 4 else []))
        return "[" + " ".join(ids) + "]"
    else:
        return "unknown command: " + " ".join(f)
    return "ok"


def main() -> None:
    svc = FeedService()
    cursors: dict[str, str | None] = {}
    for line in sys.stdin:
        f = line.split()
        if not f:
            continue
        try:
            print(handle(svc, cursors, f))
        except (FeedError, ValueError) as e:
            print("error:", e)


if __name__ == "__main__":
    main()
