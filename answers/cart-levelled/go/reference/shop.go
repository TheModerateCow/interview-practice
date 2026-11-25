package shop

import (
	"sort"
	"strconv"
)

// cartTTL: a cart untouched for this many minutes is abandoned.
const cartTTL = 60

type product struct {
	price int
	stock int
	sold  int
}

type cart struct {
	lines   map[string]int
	touched int
	promo   string
}

type promo struct {
	percent   int
	minTotal  int
	expiresAt int
}

type order struct {
	ts        int
	total     int
	lines     map[string]int
	cancelled bool
}

// Shop is an online shop's catalog, shopping carts, promo codes and order history.
type Shop struct {
	products map[string]*product
	carts    map[string]*cart
	promos   map[string]*promo
	history  map[string][]*order
}

func NewShop() *Shop {
	return &Shop{
		products: map[string]*product{},
		carts:    map[string]*cart{},
		promos:   map[string]*promo{},
		history:  map[string][]*order{},
	}
}

func live(c *cart, ts int) bool { return ts < c.touched+cartTTL }

func sortedKeys(m map[string]int) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

// cart returns the cart if it exists and hasn't been abandoned; an abandoned cart is dropped.
func (s *Shop) cart(ts int, cartID string) *cart {
	c := s.carts[cartID]
	if c != nil && !live(c, ts) {
		delete(s.carts, cartID)
		c = nil
	}
	return c
}

// ---------------------------------------------------------------- level 1

func (s *Shop) AddProduct(ts int, sku string, priceCents int, stock int) bool {
	if _, ok := s.products[sku]; ok || priceCents <= 0 || stock < 0 {
		return false
	}
	s.products[sku] = &product{price: priceCents, stock: stock}
	return true
}

func (s *Shop) AddToCart(ts int, cartID string, sku string, qty int) bool {
	p := s.products[sku]
	if p == nil || qty <= 0 {
		return false
	}
	c := s.cart(ts, cartID)
	have := 0
	if c != nil {
		have = c.lines[sku]
	}
	if have+qty > p.stock {
		return false
	}
	if c == nil {
		c = &cart{lines: map[string]int{}}
		s.carts[cartID] = c
	}
	c.lines[sku] = have + qty
	c.touched = ts
	return true
}

func (s *Shop) RemoveFromCart(ts int, cartID string, sku string, qty int) int {
	c := s.cart(ts, cartID)
	if c == nil || qty <= 0 {
		return -1
	}
	have, ok := c.lines[sku]
	if !ok {
		return -1
	}
	left := max(0, have-qty)
	if left == 0 {
		delete(c.lines, sku)
	} else {
		c.lines[sku] = left
	}
	c.touched = ts
	return left
}

func (s *Shop) CartTotal(ts int, cartID string) int {
	c := s.cart(ts, cartID)
	if c == nil {
		return 0
	}
	sub := 0
	for sku, q := range c.lines {
		sub += s.products[sku].price * q
	}
	if pr := s.promos[c.promo]; c.promo != "" && pr != nil && ts < pr.expiresAt && sub >= pr.minTotal {
		sub -= sub * pr.percent / 100
	}
	return sub
}

func (s *Shop) Items(ts int, cartID string) []string {
	out := []string{}
	if c := s.cart(ts, cartID); c != nil {
		for _, sku := range sortedKeys(c.lines) {
			out = append(out, sku+":"+strconv.Itoa(c.lines[sku]))
		}
	}
	return out
}

// ---------------------------------------------------------------- level 2

func (s *Shop) Checkout(ts int, cartID string) int {
	c := s.cart(ts, cartID)
	if c == nil || len(c.lines) == 0 {
		return -1
	}
	for sku, q := range c.lines {
		if s.products[sku].stock < q {
			return -1
		}
	}
	total := s.CartTotal(ts, cartID)
	lines := map[string]int{}
	for sku, q := range c.lines {
		p := s.products[sku]
		p.stock -= q
		p.sold += q
		lines[sku] = q
	}
	s.history[cartID] = append(s.history[cartID], &order{ts: ts, total: total, lines: lines})
	delete(s.carts, cartID)
	return total
}

func (s *Shop) StockOf(ts int, sku string) int {
	if p := s.products[sku]; p != nil {
		return p.stock
	}
	return -1
}

func (s *Shop) TopSellers(ts int, n int) []string {
	skus := []string{}
	for sku, p := range s.products {
		if p.sold > 0 {
			skus = append(skus, sku)
		}
	}
	sort.Slice(skus, func(i, j int) bool {
		a, b := s.products[skus[i]].sold, s.products[skus[j]].sold
		if a != b {
			return a > b
		}
		return skus[i] < skus[j]
	})
	out := []string{}
	for _, sku := range skus {
		if len(out) < n {
			out = append(out, sku+"("+strconv.Itoa(s.products[sku].sold)+")")
		}
	}
	return out
}

// ---------------------------------------------------------------- level 3

func (s *Shop) AddPromo(ts int, code string, percentOff int, minTotalCents int, ttl int) bool {
	if _, ok := s.promos[code]; ok || percentOff < 1 || percentOff > 100 || minTotalCents < 0 || ttl <= 0 {
		return false
	}
	s.promos[code] = &promo{percent: percentOff, minTotal: minTotalCents, expiresAt: ts + ttl}
	return true
}

func (s *Shop) ApplyPromo(ts int, cartID string, code string) bool {
	c := s.cart(ts, cartID)
	pr := s.promos[code]
	if c == nil || len(c.lines) == 0 || pr == nil || ts >= pr.expiresAt {
		return false
	}
	c.promo = code
	c.touched = ts
	return true
}

func (s *Shop) ActiveCarts(ts int) int {
	n := 0
	for _, c := range s.carts {
		if live(c, ts) && len(c.lines) > 0 {
			n++
		}
	}
	return n
}

// ---------------------------------------------------------------- level 4

func (s *Shop) Merge(ts int, guestID string, userID string) bool {
	if guestID == userID {
		return false
	}
	g := s.cart(ts, guestID)
	if g == nil || len(g.lines) == 0 {
		return false
	}
	u := s.cart(ts, userID)
	if u == nil {
		u = &cart{lines: map[string]int{}}
		s.carts[userID] = u
	}
	for sku, add := range g.lines {
		have := u.lines[sku]
		q := max(have, min(have+add, s.products[sku].stock))
		if q > 0 {
			u.lines[sku] = q
		}
	}
	up := s.promos[u.promo]
	if u.promo == "" || up == nil || ts >= up.expiresAt {
		u.promo = g.promo
	}
	u.touched = ts
	delete(s.carts, guestID)
	if moved, ok := s.history[guestID]; ok {
		delete(s.history, guestID)
		h := append(s.history[userID], moved...)
		sort.SliceStable(h, func(i, j int) bool { return h[i].ts < h[j].ts })
		s.history[userID] = h
	}
	return true
}

func (s *Shop) OrderHistory(ts int, cartID string) []string {
	out := []string{}
	for _, o := range s.history[cartID] {
		if o.cancelled {
			out = append(out, strconv.Itoa(o.ts)+":cancelled")
		} else {
			out = append(out, strconv.Itoa(o.ts)+":"+strconv.Itoa(o.total))
		}
	}
	return out
}

func (s *Shop) CancelOrder(ts int, cartID string, orderTs int) bool {
	for _, o := range s.history[cartID] {
		if o.ts != orderTs || o.cancelled {
			continue
		}
		for sku, q := range o.lines {
			p := s.products[sku]
			p.stock += q
			p.sold -= q
		}
		o.cancelled = true
		return true
	}
	return false
}
