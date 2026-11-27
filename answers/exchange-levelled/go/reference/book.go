// Package book is the order book for one instrument: resting orders, queue priority, sweeps and limit orders
// matched by price and time.
package book

import (
	"container/list"
	"fmt"
	"sort"
)

type order struct {
	id     string
	sell   bool
	price  int
	left   int
	filled int
	state  string
	elem   *list.Element // its place in its level's queue while open
}

type level struct {
	q      *list.List // *order, first in line at the front
	shares int
}

// side is one side of the book. keys holds each level's sort key, best first (asks: price; bids: -price).
type side struct {
	desc   bool
	keys   []int
	levels map[int]*level
}

func newSide(desc bool) *side { return &side{desc: desc, levels: map[int]*level{}} }

func (s *side) key(p int) int {
	if s.desc {
		return -p
	}
	return p
}

func (s *side) add(o *order) {
	lv, ok := s.levels[o.price]
	if !ok {
		lv = &level{q: list.New()}
		s.levels[o.price] = lv
		k := s.key(o.price)
		i := sort.SearchInts(s.keys, k)
		s.keys = append(s.keys, 0)
		copy(s.keys[i+1:], s.keys[i:])
		s.keys[i] = k
	}
	o.elem = lv.q.PushBack(o)
	lv.shares += o.left
}

func (s *side) remove(o *order) {
	lv := s.levels[o.price]
	lv.q.Remove(o.elem)
	o.elem = nil
	lv.shares -= o.left
	if lv.q.Len() == 0 {
		s.drop(o.price)
	}
}

func (s *side) drop(p int) {
	delete(s.levels, p)
	i := sort.SearchInts(s.keys, s.key(p))
	s.keys = append(s.keys[:i], s.keys[i+1:]...)
}

// take fills up to qty from the best level on, stopping at levels worse than limit (if hasLimit).
func (s *side) take(qty int, limit int, hasLimit bool) (got, cost int) {
	for qty > 0 && len(s.keys) > 0 && (!hasLimit || s.keys[0] <= s.key(limit)) {
		p := s.key(s.keys[0])
		lv := s.levels[p]
		for qty > 0 && lv.q.Len() > 0 {
			o := lv.q.Front().Value.(*order)
			t := min(o.left, qty)
			o.left -= t
			o.filled += t
			lv.shares -= t
			qty -= t
			got += t
			cost += t * p
			if o.left == 0 {
				o.state = "filled"
				lv.q.Remove(o.elem)
				o.elem = nil
			}
		}
		if lv.q.Len() == 0 {
			s.drop(p)
		}
	}
	return got, cost
}

// OrderBook holds every order ever placed, by id, and the two sides of the book.
type OrderBook struct {
	orders map[string]*order
	asks   *side
	bids   *side
}

// NewOrderBook returns an empty book.
func NewOrderBook() *OrderBook {
	return &OrderBook{orders: map[string]*order{}, asks: newSide(false), bids: newSide(true)}
}

func (b *OrderBook) sideOf(o *order) *side {
	if o.sell {
		return b.asks
	}
	return b.bids
}

func (b *OrderBook) resting(id string) *order {
	o, ok := b.orders[id]
	if !ok || o.state != "open" {
		return nil
	}
	return o
}

// ---- level 1 ----

func (b *OrderBook) AddOrder(orderID string, price int, qty int) bool {
	_, ok := b.Submit(orderID, "sell", price, qty)
	return ok
}

func (b *OrderBook) CancelOrder(orderID string) bool {
	o := b.resting(orderID)
	if o == nil {
		return false
	}
	b.sideOf(o).remove(o)
	o.state = "cancelled"
	return true
}

func (b *OrderBook) BestAsk() (int, bool) {
	if len(b.asks.keys) == 0 {
		return 0, false
	}
	return b.asks.keys[0], true
}

func (b *OrderBook) DepthAt(price int) int {
	d := 0
	if lv, ok := b.asks.levels[price]; ok {
		d += lv.shares
	}
	if lv, ok := b.bids.levels[price]; ok {
		d += lv.shares
	}
	return d
}

// ---- level 2 ----

func (b *OrderBook) AmendOrder(orderID string, qty int) bool {
	o := b.resting(orderID)
	if o == nil {
		return false
	}
	s := b.sideOf(o)
	if qty > o.left { // more shares: back of the queue
		s.remove(o)
		o.left = qty
		s.add(o)
	} else {
		s.levels[o.price].shares -= o.left - qty
		o.left = qty
	}
	return true
}

func (b *OrderBook) QueueAt(price int) []string {
	out := []string{}
	lv, ok := b.asks.levels[price]
	if !ok {
		lv, ok = b.bids.levels[price]
	}
	if !ok {
		return out
	}
	for e := lv.q.Front(); e != nil; e = e.Next() {
		o := e.Value.(*order)
		out = append(out, fmt.Sprintf("%s:%d", o.id, o.left))
	}
	return out
}

func (b *OrderBook) TopLevels(n int) []string {
	out := []string{}
	for i := 0; i < n && i < len(b.asks.keys); i++ {
		p := b.asks.keys[i]
		lv := b.asks.levels[p]
		out = append(out, fmt.Sprintf("%d:%d:%d", p, lv.shares, lv.q.Len()))
	}
	return out
}

// ---- level 3 ----

func (b *OrderBook) QuoteBuy(qty int) (int, bool) {
	cost := 0
	for _, p := range b.asks.keys {
		t := min(qty, b.asks.levels[p].shares)
		cost += t * p
		qty -= t
		if qty == 0 {
			return cost, true
		}
	}
	return 0, false
}

func (b *OrderBook) MarketBuy(qty int) int {
	_, cost := b.asks.take(qty, 0, false)
	return cost
}

// ---- level 4 ----

func (b *OrderBook) Submit(orderID string, side string, price int, qty int) (int, bool) {
	if _, ok := b.orders[orderID]; ok {
		return 0, false
	}
	o := &order{id: orderID, sell: side == "sell", price: price, left: qty, state: "open"}
	b.orders[orderID] = o
	opp := b.asks
	if o.sell {
		opp = b.bids
	}
	got, _ := opp.take(qty, price, true)
	o.left -= got
	o.filled += got
	if o.left == 0 {
		o.state = "filled"
	} else {
		b.sideOf(o).add(o)
	}
	return got, true
}

func (b *OrderBook) BestBid() (int, bool) {
	if len(b.bids.keys) == 0 {
		return 0, false
	}
	return -b.bids.keys[0], true
}

func (b *OrderBook) OrderStatus(orderID string) string {
	o, ok := b.orders[orderID]
	if !ok {
		return ""
	}
	return fmt.Sprintf("%s:%d", o.state, o.filled)
}
