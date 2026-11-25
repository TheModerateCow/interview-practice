"""Inventory entities and the errors the service raises. Quantities are whole units;
times are Unix seconds."""

from __future__ import annotations

from dataclasses import dataclass


class InventoryError(Exception):
    """Base class for every error the inventory service raises."""


class Invalid(InventoryError):
    """invalid request"""


class Duplicate(InventoryError):
    """duplicate id"""


class NotFound(InventoryError):
    """not found"""


class UnknownWarehouse(InventoryError):
    """unknown warehouse"""


class InsufficientStock(InventoryError):
    """insufficient available stock"""


class ShortPick(InventoryError):
    """short pick: bins hold less than requested"""


class NotActive(InventoryError):
    """reservation is not active"""


class TransferState(InventoryError):
    """transfer is not in transit"""


class Backdated(InventoryError):
    """timestamp is older than the last operation"""


# Hold statuses.
ACTIVE = "active"
RELEASED = "released"
COMMITTED = "committed"
EXPIRED = "expired"

# Transfer statuses.
IN_TRANSIT = "in_transit"
RECEIVED = "received"


@dataclass
class Reservation:
    """Holds stock of one SKU in one warehouse for an order until it is committed (picked
    for shipping), released, or its hold runs out at ``expires_at``."""

    id: str
    warehouse: str
    sku: str
    qty: int
    created_at: int
    expires_at: int
    status: str
    updated_at: int  # when status last changed; for an expired hold, expires_at
    seq: int = 0  # placement order, breaks expires_at ties


@dataclass
class Transfer:
    """Moves stock of one SKU from one warehouse to another."""

    id: str
    from_wh: str
    to_wh: str
    sku: str
    qty: int
    status: str
    shipped_at: int
    received_at: int = 0
    bin: str = ""  # destination bin, once received


@dataclass
class Rule:
    """A warehouse's replenishment rule for one SKU: when its stock position falls to
    ``min`` or below, restock up to ``max``, ordering in multiples of ``pack`` (0 or 1:
    single units)."""

    min: int
    max: int
    pack: int = 0


@dataclass
class Suggestion:
    """One line of a replenishment plan."""

    sku: str
    position: int  # available plus inbound when the plan was made
    qty: int  # how much to bring in
    source: str  # warehouse to transfer from, or "" to buy from the supplier
