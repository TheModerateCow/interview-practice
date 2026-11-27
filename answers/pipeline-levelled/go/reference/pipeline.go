// Package pipeline is the in-memory core of a monorepo's release pipeline: jobs linked to the one job that consumes
// their artifact, a run tracker, cycle checks, finish-time estimates and choosing which caches to pre-warm.
package pipeline

import (
	"container/heap"
	"sort"
)

type job struct {
	minutes, warm int
	hasWarm       bool
	consumer      string
	hasConsumer   bool
	inputs        map[string]bool
	done          bool
}

// Pipeline holds jobs by name and the consumer link of each job.
type Pipeline struct {
	jobs map[string]*job
}

// NewPipeline returns a pipeline with no jobs.
func NewPipeline() *Pipeline {
	return &Pipeline{jobs: map[string]*job{}}
}

func (p *Pipeline) AddJob(name string, minutes int) bool {
	if _, ok := p.jobs[name]; ok {
		return false
	}
	p.jobs[name] = &job{minutes: minutes, inputs: map[string]bool{}}
	return true
}

func (p *Pipeline) SetConsumer(name string, consumer string) bool {
	j, ok := p.jobs[name]
	c, ok2 := p.jobs[consumer]
	if !ok || !ok2 || c.done {
		return false
	}
	if j.hasConsumer {
		delete(p.jobs[j.consumer].inputs, name)
	}
	j.consumer, j.hasConsumer = consumer, true
	c.inputs[name] = true
	return true
}

func sortedKeys(m map[string]bool) []string {
	out := []string{}
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

func (p *Pipeline) Inputs(name string) []string {
	j, ok := p.jobs[name]
	if !ok {
		return []string{}
	}
	return sortedKeys(j.inputs)
}

func (p *Pipeline) isReady(j *job) bool {
	if j.done {
		return false
	}
	for i := range j.inputs {
		if !p.jobs[i].done {
			return false
		}
	}
	return true
}

func (p *Pipeline) Ready() []string {
	out := []string{}
	for name, j := range p.jobs {
		if p.isReady(j) {
			out = append(out, name)
		}
	}
	sort.Strings(out)
	return out
}

func (p *Pipeline) Finish(name string) bool {
	j, ok := p.jobs[name]
	if !ok || !p.isReady(j) {
		return false
	}
	j.done = true
	return true
}

func (p *Pipeline) Stuck() []string {
	// Each job has at most one consumer: follow the links from every job; a walk that meets itself found a cycle.
	state := map[string]int{} // 1 = on the current walk, 2 = settled
	out := []string{}
	for start := range p.jobs {
		var walk []string
		v, ok := start, true
		for ok && state[v] == 0 {
			state[v] = 1
			walk = append(walk, v)
			j := p.jobs[v]
			v, ok = j.consumer, j.hasConsumer
		}
		if ok && state[v] == 1 {
			for i, w := range walk {
				if w == v {
					out = append(out, walk[i:]...)
					break
				}
			}
		}
		for _, w := range walk {
			state[w] = 2
		}
	}
	sort.Strings(out)
	return out
}

type names []string

func (h names) Len() int           { return len(h) }
func (h names) Less(i, j int) bool { return h[i] < h[j] }
func (h names) Swap(i, j int)      { h[i], h[j] = h[j], h[i] }
func (h *names) Push(x any)        { *h = append(*h, x.(string)) }
func (h *names) Pop() any {
	old := *h
	x := old[len(old)-1]
	*h = old[:len(old)-1]
	return x
}

func (p *Pipeline) RunOrder() []string {
	waiting := map[string]int{}
	h := &names{}
	for name, j := range p.jobs {
		if j.done {
			continue
		}
		w := 0
		for i := range j.inputs {
			if !p.jobs[i].done {
				w++
			}
		}
		waiting[name] = w
		if w == 0 {
			*h = append(*h, name)
		}
	}
	heap.Init(h)
	out := []string{}
	for h.Len() > 0 {
		name := heap.Pop(h).(string)
		out = append(out, name)
		j := p.jobs[name]
		if w, ok := waiting[j.consumer]; ok && j.hasConsumer {
			waiting[j.consumer] = w - 1
			if w-1 == 0 {
				heap.Push(h, j.consumer)
			}
		}
	}
	return out
}

// upstream returns the unfinished jobs feeding name (name first, each before its inputs); false if name is on a cycle.
func (p *Pipeline) upstream(name string) ([]string, bool) {
	order := []string{name}
	for k := 0; k < len(order); k++ {
		for i := range p.jobs[order[k]].inputs {
			if p.jobs[i].done {
				continue
			}
			if i == name {
				return nil, false
			}
			order = append(order, i)
		}
	}
	return order, true
}

func (p *Pipeline) times(name string) (map[string]int, bool) {
	order, ok := p.upstream(name)
	if !ok {
		return nil, false
	}
	t := map[string]int{}
	for k := len(order) - 1; k >= 0; k-- {
		v := order[k]
		longest := 0
		for i := range p.jobs[v].inputs {
			if !p.jobs[i].done {
				longest = max(longest, t[i])
			}
		}
		t[v] = p.jobs[v].minutes + longest
	}
	return t, true
}

func (p *Pipeline) FinishTime(name string) (int, bool) {
	j, ok := p.jobs[name]
	if !ok {
		return 0, false
	}
	if j.done {
		return 0, true
	}
	t, ok := p.times(name)
	if !ok {
		return 0, false
	}
	return t[name], true
}

func (p *Pipeline) CriticalPath(name string) []string {
	j, ok := p.jobs[name]
	if !ok || j.done {
		return []string{}
	}
	t, ok := p.times(name)
	if !ok {
		return []string{}
	}
	path := []string{name}
	for {
		next := ""
		for i := range p.jobs[path[len(path)-1]].inputs {
			if p.jobs[i].done {
				continue
			}
			if next == "" || t[i] > t[next] || t[i] == t[next] && i < next {
				next = i
			}
		}
		if next == "" {
			break
		}
		path = append(path, next)
	}
	for a, b := 0, len(path)-1; a < b; a, b = a+1, b-1 {
		path[a], path[b] = path[b], path[a]
	}
	return path
}

func (p *Pipeline) SetWarm(name string, minutes int) bool {
	j, ok := p.jobs[name]
	if !ok || minutes > j.minutes {
		return false
	}
	j.warm, j.hasWarm = minutes, true
	return true
}

func (p *Pipeline) FastestFinish(name string, k int) (int, bool) {
	j, ok := p.jobs[name]
	if !ok {
		return 0, false
	}
	if j.done {
		return 0, true
	}
	order, ok := p.upstream(name)
	if !ok {
		return 0, false
	}
	k = min(k, len(order))
	// f[v][b]: fewest minutes to finish v with at most b of its upstream jobs warmed.
	f := map[string][]int{}
	for x := len(order) - 1; x >= 0; x-- {
		v := order[x]
		g := make([]int, k+1) // when v's inputs are all done, with at most b warmed among them
		for c := range p.jobs[v].inputs {
			if p.jobs[c].done {
				continue
			}
			fc := f[c]
			delete(f, c)
			ng := make([]int, k+1)
			for b := 0; b <= k; b++ {
				// inputs run in parallel: split b between those so far and c, and wait for the slower side
				best := -1
				for a := 0; a <= b; a++ {
					if m := max(g[a], fc[b-a]); best < 0 || m < best {
						best = m
					}
				}
				ng[b] = best
			}
			g = ng
		}
		jv := p.jobs[v]
		warm := jv.minutes
		if jv.hasWarm {
			warm = jv.warm
		}
		fv := make([]int, k+1)
		fv[0] = jv.minutes + g[0]
		for b := 1; b <= k; b++ {
			fv[b] = min(jv.minutes+g[b], warm+g[b-1])
		}
		f[v] = fv
	}
	return f[name][k], true
}
