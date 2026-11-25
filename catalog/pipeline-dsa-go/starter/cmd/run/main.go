// Reads one pipeline from stdin and prints FastestRelease's answer:
//
//	n k
//	consumer cold warm      (n lines, one per job; consumer -1 is the release)
package main

import (
	"bufio"
	"fmt"
	"os"

	"pipeline"
)

func main() {
	in := bufio.NewReader(os.Stdin)
	var n, k int
	fmt.Fscan(in, &n, &k)
	jobs := make([]pipeline.Job, n)
	for i := range jobs {
		j := &jobs[i]
		fmt.Fscan(in, &j.Consumer, &j.Cold, &j.Warm)
	}
	fmt.Println(pipeline.FastestRelease(jobs, k))
}
