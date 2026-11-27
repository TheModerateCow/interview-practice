// Package risk is the transaction risk screen of a payment provider: blocklists, velocity rules,
// rule priorities with an allowlist, and a manual review queue whose declines block the card for a while.
package risk

import "fmt"

var outcome = map[string]string{"block": "decline", "velocity": "review", "allow": "approve"}

// strictness breaks priority ties: the stricter outcome wins.
var strictness = map[string]int{"decline": 0, "review": 1, "approve": 2}

type rule struct {
	typ      string // block, allow, velocity
	priority int
	until    int // block only: expiry time, 0 = permanent
	metric   string
	limit    int
	window   int
}

type txn struct {
	ts, amount     int
	card           string
	decision, rule string
}

type hit struct {
	priority      int
	name, outcome string
}

// before reports whether hit a beats hit b.
func before(a, b hit) bool {
	if a.priority != b.priority {
		return a.priority > b.priority
	}
	if strictness[a.outcome] != strictness[b.outcome] {
		return strictness[a.outcome] < strictness[b.outcome]
	}
	return a.name < b.name
}

// RiskScreen: every method takes ts first, the time of the call. Timestamps never go down.
type RiskScreen struct {
	// names: "block:<kind>:<value>", "allow:<kind>:<value>", or the velocity rule's id (no colon)
	rules map[string]*rule
	txns  map[string]*txn
	order []string // txn ids in screen order
}

// NewRiskScreen returns an empty screen.
func NewRiskScreen() *RiskScreen {
	return &RiskScreen{rules: map[string]*rule{}, txns: map[string]*txn{}}
}

func validKind(kind string) bool {
	return kind == "card" || kind == "merchant" || kind == "country"
}

// get returns the rule called name, or nil if there is none or it is a temporary block that has expired.
func (r *RiskScreen) get(ts int, name string) *rule {
	x := r.rules[name]
	if x == nil || (x.until != 0 && ts >= x.until) {
		return nil
	}
	return x
}

// ---------------------------------------------------------------- level 1

func (r *RiskScreen) Block(ts int, kind string, value string) bool {
	name := fmt.Sprintf("block:%s:%s", kind, value)
	if !validKind(kind) || r.get(ts, name) != nil {
		return false
	}
	r.rules[name] = &rule{typ: "block"}
	return true
}

func (r *RiskScreen) Unblock(ts int, kind string, value string) bool {
	name := fmt.Sprintf("block:%s:%s", kind, value)
	if r.get(ts, name) == nil {
		return false
	}
	delete(r.rules, name)
	return true
}

func (r *RiskScreen) Screen(ts int, txnID string, card string, merchant string, amount int, country string) string {
	if _, ok := r.txns[txnID]; ok || amount <= 0 {
		return ""
	}
	t := &txn{ts: ts, amount: amount, card: card}
	r.txns[txnID] = t
	r.order = append(r.order, txnID)
	var hits []hit
	for _, kv := range [][2]string{{"card", card}, {"merchant", merchant}, {"country", country}} {
		for _, typ := range []string{"block", "allow"} {
			name := fmt.Sprintf("%s:%s:%s", typ, kv[0], kv[1])
			if x := r.get(ts, name); x != nil {
				hits = append(hits, hit{x.priority, name, outcome[typ]})
			}
		}
	}
	for name, x := range r.rules {
		if x.typ != "velocity" {
			continue
		}
		used := 0
		for _, o := range r.txns { // includes this one
			if o.card == card && o.ts > ts-x.window {
				if x.metric == "count" {
					used++
				} else {
					used += o.amount
				}
			}
		}
		if used > x.limit {
			hits = append(hits, hit{x.priority, name, "review"})
		}
	}
	t.decision = "approve"
	if len(hits) > 0 {
		best := hits[0]
		for _, h := range hits[1:] {
			if before(h, best) {
				best = h
			}
		}
		t.decision, t.rule = best.outcome, best.name
	}
	return t.decision
}

func (r *RiskScreen) Decision(ts int, txnID string) string {
	if t, ok := r.txns[txnID]; ok {
		return t.decision
	}
	return ""
}

// ---------------------------------------------------------------- level 2

func (r *RiskScreen) AddVelocityRule(ts int, ruleID string, metric string, limit int, window int) bool {
	if _, ok := r.rules[ruleID]; ok || (metric != "count" && metric != "amount") || limit <= 0 || window <= 0 {
		return false
	}
	r.rules[ruleID] = &rule{typ: "velocity", metric: metric, limit: limit, window: window}
	return true
}

func (r *RiskScreen) RemoveRule(ts int, ruleID string) bool {
	x := r.rules[ruleID]
	if x == nil || x.typ != "velocity" {
		return false
	}
	delete(r.rules, ruleID)
	return true
}

// ---------------------------------------------------------------- level 3

func (r *RiskScreen) Allow(ts int, kind string, value string, priority int) bool {
	name := fmt.Sprintf("allow:%s:%s", kind, value)
	if _, ok := r.rules[name]; !validKind(kind) || ok {
		return false
	}
	r.rules[name] = &rule{typ: "allow", priority: priority}
	return true
}

func (r *RiskScreen) SetPriority(ts int, rule string, priority int) bool {
	x := r.get(ts, rule)
	if x == nil {
		return false
	}
	x.priority = priority
	return true
}

func (r *RiskScreen) Explain(ts int, txnID string) string {
	if t, ok := r.txns[txnID]; ok {
		return t.rule
	}
	return ""
}

// ---------------------------------------------------------------- level 4

func (r *RiskScreen) PendingReviews(ts int) []string {
	out := []string{}
	for _, id := range r.order {
		if r.txns[id].decision == "review" {
			out = append(out, id)
		}
	}
	return out
}

func (r *RiskScreen) ApproveReview(ts int, txnID string) bool {
	t := r.txns[txnID]
	if t == nil || t.decision != "review" {
		return false
	}
	t.decision, t.rule = "approve", "analyst"
	return true
}

func (r *RiskScreen) DeclineReview(ts int, txnID string, blockFor int) bool {
	t := r.txns[txnID]
	if t == nil || t.decision != "review" || blockFor <= 0 {
		return false
	}
	t.decision, t.rule = "decline", "analyst"
	name := "block:card:" + t.card
	x := r.get(ts, name)
	if x == nil {
		r.rules[name] = &rule{typ: "block", until: ts + blockFor}
	} else if x.until != 0 {
		x.until = max(x.until, ts+blockFor)
	}
	return true
}
