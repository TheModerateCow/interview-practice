// Drives the clinic from stdin, one command per line, and prints each result:
//
//	clinician <ts> <id>                              prints true or false
//	room <ts> <id>                                   prints true or false
//	type <ts> <name> <minutes>                       prints true or false
//	book <ts> <clinician> <patient> <type> <start>   prints the appointment id, or (failed)
//	cancel <ts> <id>                                 prints true or false
//	show <ts> <id>                                   prints the appointment, or (none)
//
// Add your own commands as you build later levels.
package main

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"

	"clinic"
)

func main() {
	c := clinic.NewClinic()
	sc := bufio.NewScanner(os.Stdin)
	for sc.Scan() {
		f := strings.Fields(sc.Text())
		if len(f) < 3 {
			continue
		}
		ts, _ := strconv.Atoi(f[1])
		n, _ := strconv.Atoi(f[len(f)-1])
		switch {
		case f[0] == "clinician" && len(f) == 3:
			fmt.Println(c.AddClinician(ts, f[2]))
		case f[0] == "room" && len(f) == 3:
			fmt.Println(c.AddRoom(ts, f[2]))
		case f[0] == "type" && len(f) == 4:
			fmt.Println(c.AddType(ts, f[2], n))
		case f[0] == "book" && len(f) == 6:
			if id, ok := c.Book(ts, f[2], f[3], f[4], n); ok {
				fmt.Println(id)
			} else {
				fmt.Println("(failed)")
			}
		case f[0] == "cancel" && len(f) == 3:
			fmt.Println(c.Cancel(ts, f[2]))
		case f[0] == "show" && len(f) == 3:
			if s, ok := c.Appointment(ts, f[2]); ok {
				fmt.Println(s)
			} else {
				fmt.Println("(none)")
			}
		default:
			fmt.Println("unknown command:", sc.Text())
		}
	}
}
