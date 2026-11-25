// Reads the number of logged searches n, then n queries (one per line), then the target, and
// prints FewestKeystrokes(log, target).
package main

import (
	"bufio"
	"fmt"
	"os"

	"search_box"
)

func main() {
	in := bufio.NewReader(os.Stdin)
	var n int
	fmt.Fscan(in, &n)
	log := make([]string, n)
	for i := range log {
		fmt.Fscan(in, &log[i])
	}
	var target string
	fmt.Fscan(in, &target)
	fmt.Println(search_box.FewestKeystrokes(log, target))
}
