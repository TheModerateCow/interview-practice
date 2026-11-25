"""Drives the flag service from stdin, one command per line, and prints each result:

    create <ts> <flag>
    set <ts> <flag> <env> on|off
    target <ts> <flag> <env> <user>
    untarget <ts> <flag> <env> <user>
    check <ts> <flag> <env> <user>

Add your own commands here as you build later levels.
"""
import sys

from flags import FlagService

svc = FlagService()
for line in sys.stdin:
    f = line.split()
    if not f:
        continue
    cmd, args = f[0], f[1:]
    if cmd == "create" and len(args) == 2:
        print(svc.create_flag(int(args[0]), args[1]))
    elif cmd == "set" and len(args) == 4:
        print(svc.set_enabled(int(args[0]), args[1], args[2], args[3] == "on"))
    elif cmd == "target" and len(args) == 4:
        print(svc.add_target(int(args[0]), args[1], args[2], args[3]))
    elif cmd == "untarget" and len(args) == 4:
        print(svc.remove_target(int(args[0]), args[1], args[2], args[3]))
    elif cmd == "check" and len(args) == 4:
        print(svc.is_enabled(int(args[0]), args[1], args[2], args[3]))
    else:
        print("unknown command:", line.strip())
