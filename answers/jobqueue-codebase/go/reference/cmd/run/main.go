// Drives the job queue from stdin, one command per line, and prints each result
// (or "error: ..."):
//
//	enqueue <ts> <queue> <payload> [priority=N] [runAt=N] [attempts=N] [key=K]
//	lease <ts> <queue> [visibility]
//	ack <ts> <job> <token>
//	fail <ts> <job> <token> <error>
//	extend <ts> <job> <token> <seconds>
//	cancel <ts> <job>
//	redrive <ts> <job>
//	job <job>
//	dead <queue>
//	stats <ts> <queue>
//
// Times are Unix seconds. The queue uses the default options. Add your own
// commands as you need them.
package main

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"

	"jobqueue"
)

func main() {
	q := jobqueue.New()
	sc := bufio.NewScanner(os.Stdin)
	for sc.Scan() {
		f := strings.Fields(sc.Text())
		if len(f) == 0 {
			continue
		}
		out, err := run(q, f)
		if err != nil {
			fmt.Println("error:", err)
		} else {
			fmt.Println(out)
		}
	}
}

func run(q *jobqueue.JobQueue, f []string) (string, error) {
	need := func(n int) error {
		if len(f) < n {
			return fmt.Errorf("%s needs %d arguments", f[0], n-1)
		}
		return nil
	}
	num := func(i int) int64 { n, _ := strconv.ParseInt(f[i], 10, 64); return n }
	switch f[0] {
	case "enqueue":
		if err := need(4); err != nil {
			return "", err
		}
		var o jobqueue.EnqueueOptions
		for _, opt := range f[4:] {
			k, v, _ := strings.Cut(opt, "=")
			n, _ := strconv.ParseInt(v, 10, 64)
			switch k {
			case "priority":
				o.Priority = int(n)
			case "runAt":
				o.RunAt = n
			case "attempts":
				o.MaxAttempts = int(n)
			case "key":
				o.Key = v
			default:
				return "", fmt.Errorf("unknown option %s", k)
			}
		}
		return q.Enqueue(f[2], f[3], num(1), o)
	case "lease":
		if err := need(3); err != nil {
			return "", err
		}
		var l *jobqueue.Lease
		var err error
		if len(f) > 3 {
			l, err = q.LeaseFor(f[2], num(1), num(3))
		} else {
			l, err = q.Lease(f[2], num(1))
		}
		if err != nil {
			return "", err
		}
		if l == nil {
			return "empty", nil
		}
		return fmt.Sprintf("%s %s attempt=%d until=%d %s", l.JobID, l.Token, l.Attempt, l.Until, l.Payload), nil
	case "ack", "fail", "extend", "cancel", "redrive":
		min := map[string]int{"ack": 4, "fail": 5, "extend": 5, "cancel": 3, "redrive": 3}[f[0]]
		if err := need(min); err != nil {
			return "", err
		}
		var err error
		switch f[0] {
		case "ack":
			err = q.Ack(f[2], f[3], num(1))
		case "fail":
			err = q.Fail(f[2], f[3], f[4], num(1))
		case "extend":
			err = q.Extend(f[2], f[3], num(4), num(1))
		case "cancel":
			err = q.Cancel(f[2], num(1))
		case "redrive":
			err = q.Redrive(f[2], num(1))
		}
		return "ok", err
	case "job":
		if err := need(2); err != nil {
			return "", err
		}
		if j, ok := q.Job(f[1]); ok {
			return j.String(), nil
		}
		return "none", nil
	case "dead":
		if err := need(2); err != nil {
			return "", err
		}
		var parts []string
		for _, j := range q.DeadLetters(f[1]) {
			parts = append(parts, j.String())
		}
		return "[" + strings.Join(parts, ", ") + "]", nil
	case "stats":
		if err := need(3); err != nil {
			return "", err
		}
		s, err := q.Stats(f[2], num(1))
		return s.String(), err
	}
	return "", fmt.Errorf("unknown command %s", f[0])
}
