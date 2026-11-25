// Reads "n days duration quorum", then for each attendee "offset workStart workEnd m" followed by m pairs
// "start end" (any whitespace), and prints EarliestQuorumSlot (or -1).
package main

import (
	"bufio"
	"fmt"
	"os"

	"scheduler"
)

func main() {
	in := bufio.NewReader(os.Stdin)
	var n, days, duration, quorum int
	fmt.Fscan(in, &n, &days, &duration, &quorum)
	attendees := make([]scheduler.Attendee, n)
	for i := range attendees {
		var m int
		a := &attendees[i]
		fmt.Fscan(in, &a.Offset, &a.WorkStart, &a.WorkEnd, &m)
		a.Busy = make([][]int, m)
		for j := range a.Busy {
			a.Busy[j] = make([]int, 2)
			fmt.Fscan(in, &a.Busy[j][0], &a.Busy[j][1])
		}
	}
	fmt.Println(scheduler.EarliestQuorumSlot(attendees, days, duration, quorum))
}
