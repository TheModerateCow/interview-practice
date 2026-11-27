// Package helpdesk is a support desk: tickets with priorities, agents and their queues, SLA due
// times that pause while a ticket waits on the customer, shift changes and a history of every ticket.
package helpdesk

import (
	"fmt"
	"sort"
)

var priorityRank = map[string]int{"high": 0, "normal": 1, "low": 2}

// sla is the minutes to resolve, per priority.
var sla = map[string]int{"high": 60, "normal": 240, "low": 1440}

var moves = map[[2]string]bool{
	{"open", "in_progress"}: true, {"in_progress", "open"}: true, {"in_progress", "resolved"}: true, {"resolved", "open"}: true,
	{"in_progress", "waiting"}: true, {"waiting", "in_progress"}: true,
}

type ticket struct {
	id, customer, priority, status, agent string
	num, opened, paused, waitStart        int
	history                               []string
}

// Desk: every method takes ts first, the time of the call in minutes. Timestamps never decrease.
type Desk struct {
	agents  map[string]bool // agent -> on shift
	tickets map[string]*ticket
	nextID  int
}

// NewDesk returns an empty desk.
func NewDesk() *Desk {
	return &Desk{agents: map[string]bool{}, tickets: map[string]*ticket{}}
}

func (d *Desk) put(ts int, t *ticket, agent string) {
	t.agent = agent
	t.history = append(t.history, fmt.Sprintf("%d:assigned:%s", ts, agent))
}

// pick returns the on-shift agent with the fewest unresolved tickets, ties by name; "" if nobody is on shift.
func (d *Desk) pick(ts int) string {
	best, bestLoad := "", 0
	for a, on := range d.agents {
		if !on {
			continue
		}
		load := len(d.Queue(ts, a))
		if best == "" || load < bestLoad || (load == bestLoad && a < best) {
			best, bestLoad = a, load
		}
	}
	return best
}

func due(ts int, t *ticket) int {
	paused := t.paused
	if t.status == "waiting" {
		paused += ts - t.waitStart
	}
	return t.opened + sla[t.priority] + paused
}

// ---------------------------------------------------------------- level 1

func (d *Desk) AddAgent(ts int, agent string) bool {
	if _, ok := d.agents[agent]; ok {
		return false
	}
	d.agents[agent] = true
	return true
}

func (d *Desk) OpenTicket(ts int, customer string, priority string) string {
	if _, ok := priorityRank[priority]; !ok {
		return ""
	}
	d.nextID++
	id := fmt.Sprintf("t%d", d.nextID)
	d.tickets[id] = &ticket{id: id, num: d.nextID, customer: customer, priority: priority, status: "open",
		opened: ts, history: []string{fmt.Sprintf("%d:opened", ts)}}
	return id
}

func (d *Desk) Assign(ts int, ticketID string, agent string) bool {
	t := d.tickets[ticketID]
	if t == nil || !d.agents[agent] || t.status == "resolved" || t.agent == agent {
		return false
	}
	d.put(ts, t, agent)
	return true
}

func (d *Desk) SetStatus(ts int, ticketID string, status string) bool {
	t := d.tickets[ticketID]
	if t == nil || !moves[[2]string{t.status, status}] {
		return false
	}
	if status == "in_progress" && t.agent == "" {
		return false
	}
	if status == "waiting" {
		t.waitStart = ts
	}
	if t.status == "waiting" {
		t.paused += ts - t.waitStart
	}
	t.status = status
	t.history = append(t.history, fmt.Sprintf("%d:%s", ts, status))
	return true
}

func (d *Desk) GetTicket(ts int, ticketID string) string {
	t := d.tickets[ticketID]
	if t == nil {
		return ""
	}
	agent := t.agent
	if agent == "" {
		agent = "-"
	}
	return fmt.Sprintf("%s:%s:%s:%s", t.customer, t.priority, t.status, agent)
}

// ---------------------------------------------------------------- level 2

func (d *Desk) Queue(ts int, agent string) []string {
	mine := []*ticket{}
	for _, t := range d.tickets {
		if t.agent == agent && t.status != "resolved" {
			mine = append(mine, t)
		}
	}
	sort.Slice(mine, func(i, j int) bool {
		if pi, pj := priorityRank[mine[i].priority], priorityRank[mine[j].priority]; pi != pj {
			return pi < pj
		}
		return mine[i].num < mine[j].num
	})
	ids := make([]string, len(mine))
	for i, t := range mine {
		ids[i] = t.id
	}
	return ids
}

func (d *Desk) AutoAssign(ts int, ticketID string) string {
	t := d.tickets[ticketID]
	if t == nil || t.agent != "" {
		return ""
	}
	agent := d.pick(ts)
	if agent != "" {
		d.put(ts, t, agent)
	}
	return agent
}

// ---------------------------------------------------------------- level 3

func (d *Desk) DueAt(ts int, ticketID string) int {
	t := d.tickets[ticketID]
	if t == nil {
		return -1
	}
	return due(ts, t)
}

func (d *Desk) Overdue(ts int) []string {
	late := []*ticket{}
	for _, t := range d.tickets {
		if (t.status == "open" || t.status == "in_progress") && ts > due(ts, t) {
			late = append(late, t)
		}
	}
	sort.Slice(late, func(i, j int) bool {
		if di, dj := due(ts, late[i]), due(ts, late[j]); di != dj {
			return di < dj
		}
		return late[i].num < late[j].num
	})
	ids := make([]string, len(late))
	for i, t := range late {
		ids[i] = t.id
	}
	return ids
}

// ---------------------------------------------------------------- level 4

func (d *Desk) EndShift(ts int, agent string) []string {
	other := false
	for a, on := range d.agents {
		if on && a != agent {
			other = true
		}
	}
	if !d.agents[agent] || !other {
		return []string{}
	}
	d.agents[agent] = false
	out := []string{}
	for _, id := range d.Queue(ts, agent) {
		to := d.pick(ts)
		d.put(ts, d.tickets[id], to)
		out = append(out, id+":"+to)
	}
	return out
}

func (d *Desk) StartShift(ts int, agent string) bool {
	on, ok := d.agents[agent]
	if !ok || on {
		return false
	}
	d.agents[agent] = true
	return true
}

func (d *Desk) History(ts int, ticketID string) []string {
	t := d.tickets[ticketID]
	if t == nil {
		return []string{}
	}
	return append([]string{}, t.history...)
}
