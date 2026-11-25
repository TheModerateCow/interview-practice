"""Drives the hotel from stdin, one command per line, and prints each result:

    room <day> <room_id> <room_type> <rate>
    book <day> <guest> <room_id> <check_in> <check_out>
    cancel <day> <booking_id>
    cost <day> <booking_id>

A failed book prints an empty line. Add your own commands here as you build later levels.
"""
import sys

from hotel import Hotel

h = Hotel()
for line in sys.stdin:
    f = line.split()
    if not f:
        continue
    cmd, args = f[0], f[1:]
    if cmd == "room" and len(args) == 4:
        print(h.add_room(int(args[0]), args[1], args[2], int(args[3])))
    elif cmd == "book" and len(args) == 5:
        print(h.book(int(args[0]), args[1], args[2], int(args[3]), int(args[4])))
    elif cmd == "cancel" and len(args) == 2:
        print(h.cancel(int(args[0]), args[1]))
    elif cmd == "cost" and len(args) == 2:
        print(h.cost(int(args[0]), args[1]))
    else:
        print("unknown command:", line.strip())
