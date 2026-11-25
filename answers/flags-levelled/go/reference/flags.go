// Package flags is a feature-flag service: flags switched on or off per environment, user targeting,
// percentage rollouts, scheduled changes and an audit history with rollback.
package flags

import (
	"fmt"
	"math"
	"sort"
	"strconv"
)

// bucket is the stable bucket in [0, 100) for a user of a flag.
func bucket(flagID, userID string) int {
	h := 0
	for _, c := range flagID + ":" + userID {
		h = (h*31 + int(c)) % 1000000007
	}
	return h % 100
}

type stamp struct {
	ts int
	v  int // 1/0 for on/off, or the percent
}

type env struct {
	on         bool
	rollout    int
	targets    map[string]bool
	evals      int
	stateLog   []stamp // (time, on) after each on/off change
	rolloutLog []stamp // (time, percent) after each rollout change
}

type schedule struct {
	id   string
	seq  int
	flag string
	env  string
	on   bool
	at   int
	done bool
}

// FlagService holds every flag and its environments. Timestamps passed to its methods only ever increase.
type FlagService struct {
	flags     map[string]map[string]*env
	schedules map[string]*schedule
	nextSeq   int
}

// NewFlagService returns an empty service.
func NewFlagService() *FlagService {
	return &FlagService{flags: map[string]map[string]*env{}, schedules: map[string]*schedule{}, nextSeq: 1}
}

// ---- level 1

func (f *FlagService) CreateFlag(ts int, flagID string) bool {
	f.advance(ts)
	if _, ok := f.flags[flagID]; ok {
		return false
	}
	f.flags[flagID] = map[string]*env{}
	return true
}

func (f *FlagService) SetEnabled(ts int, flagID string, envName string, on bool) bool {
	f.advance(ts)
	e := f.env(flagID, envName)
	if e == nil {
		return false
	}
	apply(e, ts, on)
	return true
}

func (f *FlagService) AddTarget(ts int, flagID string, envName string, userID string) bool {
	f.advance(ts)
	e := f.env(flagID, envName)
	if e == nil || e.targets[userID] {
		return false
	}
	e.targets[userID] = true
	return true
}

func (f *FlagService) RemoveTarget(ts int, flagID string, envName string, userID string) bool {
	f.advance(ts)
	e := f.env(flagID, envName)
	if e == nil || !e.targets[userID] {
		return false
	}
	delete(e.targets, userID)
	return true
}

func (f *FlagService) IsEnabled(ts int, flagID string, envName string, userID string) bool {
	f.advance(ts)
	e := f.env(flagID, envName)
	if e == nil {
		return false
	}
	e.evals++
	return sees(flagID, e, userID)
}

// ---- level 2

func (f *FlagService) SetRollout(ts int, flagID string, envName string, percent int) bool {
	f.advance(ts)
	e := f.env(flagID, envName)
	if e == nil || percent < 0 || percent > 100 {
		return false
	}
	e.rollout = percent
	e.rolloutLog = append(e.rolloutLog, stamp{ts, percent})
	return true
}

func (f *FlagService) EnabledFlags(ts int, envName string, userID string) []string {
	f.advance(ts)
	out := []string{}
	for id := range f.flags {
		if sees(id, f.env(id, envName), userID) {
			out = append(out, id)
		}
	}
	sort.Strings(out)
	return out
}

func (f *FlagService) MostEvaluated(ts int, envName string, n int) []string {
	f.advance(ts)
	type row struct {
		id    string
		count int
	}
	rows := []row{}
	for id, envs := range f.flags {
		if e, ok := envs[envName]; ok && e.evals > 0 {
			rows = append(rows, row{id, e.evals})
		}
	}
	sort.Slice(rows, func(i, j int) bool {
		if rows[i].count != rows[j].count {
			return rows[i].count > rows[j].count
		}
		return rows[i].id < rows[j].id
	})
	out := []string{}
	for i := 0; i < len(rows) && i < n; i++ {
		out = append(out, fmt.Sprintf("%s(%d)", rows[i].id, rows[i].count))
	}
	return out
}

// ---- level 3

func (f *FlagService) ScheduleChange(ts int, flagID string, envName string, on bool, atTs int) string {
	f.advance(ts)
	if _, ok := f.flags[flagID]; !ok || atTs <= ts {
		return ""
	}
	seq := f.nextSeq
	f.nextSeq++
	id := "s" + strconv.Itoa(seq)
	f.schedules[id] = &schedule{id: id, seq: seq, flag: flagID, env: envName, on: on, at: atTs}
	return id
}

func (f *FlagService) CancelSchedule(ts int, scheduleID string) bool {
	f.advance(ts)
	s, ok := f.schedules[scheduleID]
	if !ok || s.done {
		return false
	}
	delete(f.schedules, scheduleID)
	return true
}

func (f *FlagService) Pending(ts int, flagID string) []string {
	f.advance(ts)
	out := []string{}
	for _, s := range f.due(math.MaxInt) {
		if s.flag == flagID {
			out = append(out, s.id)
		}
	}
	return out
}

// ---- level 4

func (f *FlagService) History(ts int, flagID string, envName string) []string {
	f.advance(ts)
	out := []string{}
	e := f.env(flagID, envName)
	if e == nil {
		return out
	}
	for _, s := range e.stateLog {
		state := "off"
		if s.v == 1 {
			state = "on"
		}
		out = append(out, fmt.Sprintf("%d:%s", s.ts, state))
	}
	return out
}

func (f *FlagService) Rollback(ts int, flagID string, envName string, toTs int) bool {
	f.advance(ts)
	e := f.env(flagID, envName)
	if e == nil {
		return false
	}
	on, percent := false, 100
	for _, s := range e.stateLog {
		if s.ts <= toTs {
			on = s.v == 1
		}
	}
	for _, s := range e.rolloutLog {
		if s.ts <= toTs {
			percent = s.v
		}
	}
	apply(e, ts, on)
	e.rollout = percent
	e.rolloutLog = append(e.rolloutLog, stamp{ts, percent})
	return true
}

// ---- internals

func (f *FlagService) env(flagID, name string) *env {
	envs, ok := f.flags[flagID]
	if !ok {
		return nil
	}
	e, ok := envs[name]
	if !ok {
		e = &env{rollout: 100, targets: map[string]bool{}}
		envs[name] = e
	}
	return e
}

func sees(flagID string, e *env, userID string) bool {
	if e.targets[userID] {
		return true
	}
	return e.on && bucket(flagID, userID) < e.rollout
}

func apply(e *env, ts int, on bool) {
	e.on = on
	v := 0
	if on {
		v = 1
	}
	e.stateLog = append(e.stateLog, stamp{ts, v})
}

// due returns the pending scheduled changes due at or before ts, by at then scheduling order.
func (f *FlagService) due(ts int) []*schedule {
	out := []*schedule{}
	for _, s := range f.schedules {
		if !s.done && s.at <= ts {
			out = append(out, s)
		}
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].at != out[j].at {
			return out[i].at < out[j].at
		}
		return out[i].seq < out[j].seq
	})
	return out
}

// advance applies every scheduled change due at or before ts, before the call at ts runs.
func (f *FlagService) advance(ts int) {
	for _, s := range f.due(ts) {
		s.done = true
		apply(f.env(s.flag, s.env), s.at, s.on)
	}
}
