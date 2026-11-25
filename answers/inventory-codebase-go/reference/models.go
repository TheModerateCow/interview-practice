// Package inventory tracks stock across an online retailer's warehouses: what sits in
// each bin, what is held for open orders, what is moving between warehouses, and what
// needs replenishing. Quantities are whole units; times are Unix seconds.
package inventory

import "errors"

var (
	ErrInvalid           = errors.New("invalid request")
	ErrDuplicate         = errors.New("duplicate id")
	ErrNotFound          = errors.New("not found")
	ErrUnknownWarehouse  = errors.New("unknown warehouse")
	ErrInsufficientStock = errors.New("insufficient available stock")
	ErrShortPick         = errors.New("short pick: bins hold less than requested")
	ErrNotActive         = errors.New("reservation is not active")
	ErrTransferState     = errors.New("transfer is not in transit")
	ErrBackdated         = errors.New("timestamp is older than the last operation")
)

// HoldStatus is where a reservation is in its life.
type HoldStatus string

const (
	Active    HoldStatus = "active"
	Released  HoldStatus = "released"
	Committed HoldStatus = "committed"
	Expired   HoldStatus = "expired"
)

// Reservation holds stock of one SKU in one warehouse for an order until it is committed
// (picked for shipping), released, or its hold runs out at ExpiresAt.
type Reservation struct {
	ID        string
	Warehouse string
	SKU       string
	Qty       int
	CreatedAt int64
	ExpiresAt int64
	Status    HoldStatus
	UpdatedAt int64 // when Status last changed; for an expired hold, ExpiresAt

	seq int // placement order, breaks ExpiresAt ties
}

// TransferStatus is where a transfer between warehouses is.
type TransferStatus string

const (
	InTransit TransferStatus = "in_transit"
	Received  TransferStatus = "received"
)

// Transfer moves stock of one SKU from one warehouse to another.
type Transfer struct {
	ID         string
	From, To   string
	SKU        string
	Qty        int
	Status     TransferStatus
	ShippedAt  int64
	ReceivedAt int64
	Bin        string // destination bin, once received
}

// Rule is a warehouse's replenishment rule for one SKU: when its stock position falls to
// Min or below, restock up to Max, ordering in multiples of Pack (0 or 1: single units).
type Rule struct {
	Min, Max, Pack int
}

// Suggestion is one line of a replenishment plan.
type Suggestion struct {
	SKU      string
	Position int    // available plus inbound when the plan was made
	Qty      int    // how much to bring in
	From     string // warehouse to transfer from, or "" to buy from the supplier
}
