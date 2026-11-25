"""Street geometry."""

from .models import Point

# Planning speed of a bike courier, in metres per minute (15 km/h).
COURIER_SPEED = 250


def distance(a: Point, b: Point) -> int:
    """Street distance: the zone is a street grid, so this is the Manhattan distance."""
    return abs(a.x - b.x) + abs(a.y - b.y)


def travel_minutes(metres: int) -> int:
    """Convert a street distance into whole minutes of riding."""
    return (metres + COURIER_SPEED - 1) // COURIER_SPEED
