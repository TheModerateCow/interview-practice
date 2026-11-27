"""What the lab refuses, by kind; str(e) is shown to the user. server.py maps each kind to an HTTP status: nothing
under lab/ knows HTTP."""


class Refused(Exception): pass
class Invalid(Refused): pass      # can't be done as asked: a bad path, a bad zip, an unknown language
class NotFound(Refused): pass     # no such set, problem or file
class Conflict(Refused): pass     # not now: not started, already started, a Run/Submit in flight
