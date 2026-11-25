"""Drives the notification service from stdin, one command per line, and prints
each result (or "error: ..."):

    user <id> <offsetMinutes>
    channels <id> [<channel> ...]        email, push, sms; none = digest only
    quiet <id> <fromHour> <toHour>
    send <user> <at> <topic> <key> <title> [urgent]
                                         prints "sent <ch,ch>", "held" or "duplicate"
    digest <user> <now>                  prints one "<topic> <count> <latest>" line per topic

Add your own commands here if they help.
"""

import sys

from notify import SENT, Notification, NotifyError, Service


def handle(s: Service, f: list[str]) -> list[str]:
    cmd, a = f[0], f[1:]
    if cmd == "user" and len(a) == 2:
        s.add_user(a[0], int(a[1]))
    elif cmd == "channels" and len(a) >= 1:
        s.set_channels(a[0], a[1:])
    elif cmd == "quiet" and len(a) == 3:
        s.set_quiet_hours(a[0], int(a[1]), int(a[2]))
    elif cmd == "send" and (len(a) == 5 or len(a) == 6 and a[5] == "urgent"):
        res = s.send(Notification(user=a[0], at=int(a[1]), topic=a[2], key=a[3], title=a[4], urgent=len(a) == 6))
        return [res.status + (" " + ",".join(res.channels) if res.status == SENT else "")]
    elif cmd == "digest" and len(a) == 2:
        return [f"{ln.topic} {ln.count} {ln.latest}" for ln in s.digest(a[0], int(a[1]))]
    else:
        return ["unknown command: " + " ".join(f)]
    return ["ok"]


def main() -> None:
    s = Service()
    for line in sys.stdin:
        f = line.split()
        if not f:
            continue
        try:
            out = handle(s, f)
        except (NotifyError, ValueError) as e:
            out = [f"error: {e}"]
        for ln in out:
            print(ln)


if __name__ == "__main__":
    main()
