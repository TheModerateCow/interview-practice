// Reads "n m need", then n rider positions, then m driver positions (any whitespace),
// and prints MinDispatchRadius.
package main

import (
	"bufio"
	"fmt"
	"os"

	"dispatch"
)

func main() {
	in := bufio.NewReader(os.Stdin)
	var n, m, need int
	fmt.Fscan(in, &n, &m, &need)
	riders, drivers := make([]int, n), make([]int, m)
	for i := range riders {
		fmt.Fscan(in, &riders[i])
	}
	for i := range drivers {
		fmt.Fscan(in, &drivers[i])
	}
	fmt.Println(dispatch.MinDispatchRadius(riders, drivers, need))
}
