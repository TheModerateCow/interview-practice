// Drives the notification service from stdin, one command per line, and
// prints each result (or "error: ..."):
//
//	user <id> <offsetMinutes>
//	channels <id> [<channel> ...]        email, push, sms; none = digest only
//	quiet <id> <fromHour> <toHour>
//	send <user> <at> <topic> <key> <title> [urgent]
//	                                     prints "sent <ch,ch>", "held" or "duplicate"
//	digest <user> <now>                  prints one "<topic> <count> <latest>" line per topic
//
// Add your own commands here if they help.
package main

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"

	"notify"
)

func main() {
	s := notify.New()
	sc := bufio.NewScanner(os.Stdin)
	for sc.Scan() {
		f := strings.Fields(sc.Text())
		if len(f) == 0 {
			continue
		}
		num := func(i int) int64 { n, _ := strconv.ParseInt(f[i], 10, 64); return n }
		switch {
		case f[0] == "user" && len(f) == 3:
			report("ok", s.AddUser(f[1], int(num(2))))
		case f[0] == "channels" && len(f) >= 2:
			var chans []notify.Channel
			for _, c := range f[2:] {
				chans = append(chans, notify.Channel(c))
			}
			report("ok", s.SetChannels(f[1], chans))
		case f[0] == "quiet" && len(f) == 4:
			report("ok", s.SetQuietHours(f[1], int(num(2)), int(num(3))))
		case f[0] == "send" && (len(f) == 6 || len(f) == 7 && f[6] == "urgent"):
			res, err := s.Send(notify.Notification{User: f[1], At: num(2), Topic: f[3], Key: f[4], Title: f[5], Urgent: len(f) == 7})
			out := string(res.Status)
			if res.Status == notify.Sent {
				var names []string
				for _, ch := range res.Channels {
					names = append(names, string(ch))
				}
				out += " " + strings.Join(names, ",")
			}
			report(out, err)
		case f[0] == "digest" && len(f) == 3:
			lines, err := s.Digest(f[1], num(2))
			if err != nil {
				report("", err)
				continue
			}
			for _, l := range lines {
				fmt.Println(l.Topic, l.Count, l.Latest)
			}
		default:
			fmt.Println("unknown command:", sc.Text())
		}
	}
}

func report(out string, err error) {
	if err != nil {
		fmt.Println("error:", err)
		return
	}
	fmt.Println(out)
}
