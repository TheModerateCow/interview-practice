// Drives the feed service from stdin, one command per line, and prints each
// result (or "error: ..."):
//
//	user <id>
//	follow <follower> <followee>
//	unfollow <follower> <followee>
//	mute <viewer> <target> <now> [hours]
//	post <id> <author> <created_at> [text ...]
//	like <post> <user>                     prints the like count
//	feed <viewer> <now> <limit>            first page: [ids] more|end
//	more <viewer> <now> <limit>            the page after the viewer's last feed/more
//	catchup <viewer> <since> <now> [limit]
//
// Add your own commands here if they help.
package main

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"

	"feed"
)

func handle(s *feed.Service, cursors map[string]string, f []string) (string, error) {
	cmd, a := f[0], f[1:]
	num := func(i int) int64 { n, _ := strconv.ParseInt(a[i], 10, 64); return n }
	switch {
	case cmd == "user" && len(a) == 1:
		s.AddUser(a[0])
	case cmd == "follow" && len(a) == 2:
		return "ok", s.Follow(a[0], a[1])
	case cmd == "unfollow" && len(a) == 2:
		return "ok", s.Unfollow(a[0], a[1])
	case cmd == "mute" && len(a) == 3:
		return "ok", s.Mute(a[0], a[1], num(2))
	case cmd == "mute" && len(a) == 4:
		h, _ := strconv.ParseFloat(a[3], 64)
		return "ok", s.MuteFor(a[0], a[1], num(2), h)
	case cmd == "post" && len(a) >= 3:
		_, err := s.Publish(a[0], a[1], num(2), strings.Join(a[3:], " "))
		return "ok", err
	case cmd == "like" && len(a) == 2:
		n, err := s.Like(a[0], a[1])
		return strconv.Itoa(n), err
	case (cmd == "feed" || cmd == "more") && len(a) == 3:
		cursor := ""
		if cmd == "more" {
			if cursor = cursors[a[0]]; cursor == "" {
				return "[] end", nil
			}
		}
		page, err := s.HomeFeed(a[0], num(1), int(num(2)), cursor)
		if err != nil {
			return "", err
		}
		cursors[a[0]] = page.NextCursor
		end := "end"
		if page.NextCursor != "" {
			end = "more"
		}
		return "[" + strings.Join(page.PostIDs, " ") + "] " + end, nil
	case cmd == "catchup" && (len(a) == 3 || len(a) == 4):
		limit := int64(5)
		if len(a) == 4 {
			limit = num(3)
		}
		ids, err := s.CatchUp(a[0], num(1), num(2), int(limit))
		return "[" + strings.Join(ids, " ") + "]", err
	default:
		return "unknown command: " + strings.Join(f, " "), nil
	}
	return "ok", nil
}

func main() {
	s := feed.New()
	cursors := map[string]string{}
	sc := bufio.NewScanner(os.Stdin)
	for sc.Scan() {
		f := strings.Fields(sc.Text())
		if len(f) == 0 {
			continue
		}
		out, err := handle(s, cursors, f)
		if err != nil {
			fmt.Println("error:", err)
			continue
		}
		fmt.Println(out)
	}
}
