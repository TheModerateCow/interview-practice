package main

import (
	"bufio"
	"fmt"
	"os"

	"mini"
)

func main() {
	var in []mini.Interval
	sc := bufio.NewScanner(os.Stdin)
	for sc.Scan() {
		var a, b int
		if n, _ := fmt.Sscan(sc.Text(), &a, &b); n == 2 {
			in = append(in, mini.Interval{Start: a, End: b})
		}
	}
	for _, v := range mini.Merge(in) {
		fmt.Println(v.Start, v.End)
	}
}
