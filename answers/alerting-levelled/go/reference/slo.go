// Package slo is an SLO monitor for API services: per-minute samples, error budgets, compliance stretches and
// burn-rate alerts.
package slo

import (
	"fmt"
	"sort"
)

const ppm = 1_000_000

type service struct {
	req, err  []int // per minute, index = minute; gaps hold 0
	budget    int
	hasBudget bool
	longW     int
	shortW    int
	burn      int
	hasAlert  bool
}

// SloMonitor holds services by name.
type SloMonitor struct {
	svc map[string]*service
}

// NewSloMonitor returns a monitor with no services.
func NewSloMonitor() *SloMonitor {
	return &SloMonitor{svc: map[string]*service{}}
}

// ---- level 1 ----

func (m *SloMonitor) AddService(name string) bool {
	if _, ok := m.svc[name]; ok {
		return false
	}
	m.svc[name] = &service{}
	return true
}

func (m *SloMonitor) Ingest(name string, firstMinute int, requests []int, errors []int) bool {
	s, ok := m.svc[name]
	if !ok || len(requests) == 0 || len(requests) != len(errors) || firstMinute < len(s.req) {
		return false
	}
	for i := range requests {
		if errors[i] > requests[i] {
			return false
		}
	}
	for len(s.req) < firstMinute {
		s.req = append(s.req, 0)
		s.err = append(s.err, 0)
	}
	s.req = append(s.req, requests...)
	s.err = append(s.err, errors...)
	return true
}

func (s *service) sums(start, end int) (int, int) {
	r, e := 0, 0
	if start < 0 {
		start = 0
	}
	for t := start; t <= end && t < len(s.req); t++ {
		r += s.req[t]
		e += s.err[t]
	}
	return r, e
}

func (m *SloMonitor) ErrorRate(name string, start int, end int) (int, bool) {
	s, ok := m.svc[name]
	if !ok {
		return 0, false
	}
	r, e := s.sums(start, end)
	if r == 0 {
		return 0, false
	}
	return e * ppm / r, true
}

func (m *SloMonitor) LatestMinute(name string) (int, bool) {
	s, ok := m.svc[name]
	if !ok || len(s.req) == 0 {
		return 0, false
	}
	return len(s.req) - 1, true
}

// ---- level 2 ----

func (m *SloMonitor) SetBudget(name string, budgetPpm int) bool {
	s, ok := m.svc[name]
	if !ok {
		return false
	}
	s.budget, s.hasBudget = budgetPpm, true
	return true
}

func (m *SloMonitor) BudgetLeft(name string, start int, end int) (int, bool) {
	s, ok := m.svc[name]
	if !ok || !s.hasBudget {
		return 0, false
	}
	r, e := s.sums(start, end)
	return r*s.budget/ppm - e, true
}

func (m *SloMonitor) OverBudget(end int, window int) []string {
	type hit struct {
		rate int
		name string
	}
	var hits []hit
	for name, s := range m.svc {
		if !s.hasBudget {
			continue
		}
		r, e := s.sums(end-window+1, end)
		if r > 0 && e*ppm > r*s.budget {
			hits = append(hits, hit{e * ppm / r, name})
		}
	}
	sort.Slice(hits, func(i, j int) bool {
		if hits[i].rate != hits[j].rate {
			return hits[i].rate > hits[j].rate
		}
		return hits[i].name < hits[j].name
	})
	out := []string{}
	for _, h := range hits {
		out = append(out, fmt.Sprintf("%s:%d", h.name, h.rate))
	}
	return out
}

// ---- level 3 ----

func (m *SloMonitor) LongestWithinBudget(name string, start int, end int) (string, bool) {
	s, ok := m.svc[name]
	if !ok || !s.hasBudget {
		return "", false
	}
	n := end - start + 1
	// prefix[k]: errors*1e6 - requests*budget over minutes start..start+k-1 (minutes past the data are empty)
	prefix := make([]int, n+1)
	acc := 0
	for k := 0; k < n; k++ {
		if t := start + k; t < len(s.req) {
			acc += s.err[t]*ppm - s.req[t]*s.budget
		}
		prefix[k+1] = acc
	}
	// Stretch i..j-1 is within budget when prefix[j] <= prefix[i]. Only a strict running maximum can be the
	// best start: an earlier start that is at least as high reaches every end it reaches, and is longer.
	starts := []int{}
	for i := 0; i <= n; i++ {
		if len(starts) == 0 || prefix[i] > prefix[starts[len(starts)-1]] {
			starts = append(starts, i)
		}
	}
	bestLen, bestStart := 0, 0
	for j := n; j >= 0 && len(starts) > 0; j-- {
		for len(starts) > 0 && prefix[starts[len(starts)-1]] >= prefix[j] {
			i := starts[len(starts)-1]
			starts = starts[:len(starts)-1]
			if j-i >= bestLen { // starts pop latest first, so >= keeps the earliest of equal lengths
				bestLen, bestStart = j-i, i
			}
		}
	}
	if bestLen == 0 {
		return "", true
	}
	return fmt.Sprintf("%d-%d", start+bestStart, start+bestStart+bestLen-1), true
}

// ---- level 4 ----

func (m *SloMonitor) Amend(name string, minute int, requests int, errors int) bool {
	s, ok := m.svc[name]
	if !ok || minute >= len(s.req) || errors > requests {
		return false
	}
	s.req[minute], s.err[minute] = requests, errors
	return true
}

func (m *SloMonitor) SetAlert(name string, longWindow int, shortWindow int, burn int) bool {
	s, ok := m.svc[name]
	if !ok || !s.hasBudget {
		return false
	}
	s.longW, s.shortW, s.burn, s.hasAlert = longWindow, shortWindow, burn, true
	return true
}

func (m *SloMonitor) AlertTimeline(name string, start int, end int) []string {
	out := []string{}
	s, ok := m.svc[name]
	if !ok || !s.hasAlert {
		return out
	}
	limit := s.budget * s.burn
	lo := start - s.longW + 1
	if lo < 0 {
		lo = 0
	}
	// R[k], E[k]: requests and errors over minutes lo..lo+k-1
	R := make([]int, end-lo+2)
	E := make([]int, end-lo+2)
	for t := lo; t <= end; t++ {
		r, e := 0, 0
		if t < len(s.req) {
			r, e = s.req[t], s.err[t]
		}
		R[t-lo+1] = R[t-lo] + r
		E[t-lo+1] = E[t-lo] + e
	}
	burning := func(t, w int) bool {
		a := t - w + 1
		if a < lo {
			a = lo
		}
		a, b := a-lo, t+1-lo
		return (E[b]-E[a])*ppm > (R[b]-R[a])*limit
	}
	run := -1
	for t := start; t <= end; t++ {
		if burning(t, s.longW) && burning(t, s.shortW) {
			if run < 0 {
				run = t
			}
		} else if run >= 0 {
			out = append(out, fmt.Sprintf("%d-%d", run, t-1))
			run = -1
		}
	}
	if run >= 0 {
		out = append(out, fmt.Sprintf("%d-%d", run, end))
	}
	return out
}
