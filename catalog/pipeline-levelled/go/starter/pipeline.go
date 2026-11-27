// Package pipeline is the in-memory core of a monorepo's release pipeline.
package pipeline

// Pipeline holds jobs by name and the consumer link of each job.
type Pipeline struct {
	// your state here
}

// NewPipeline returns a pipeline with no jobs.
func NewPipeline() *Pipeline {
	return &Pipeline{}
}

// AddJob adds a job that takes minutes to run. False if the name is taken.
func (p *Pipeline) AddJob(job string, minutes int) bool {
	panic("not implemented")
}

// SetConsumer makes job's artifact feed consumer, replacing job's previous consumer.
func (p *Pipeline) SetConsumer(job string, consumer string) bool {
	panic("not implemented")
}

// Inputs returns the jobs whose artifact feeds job, sorted by name.
func (p *Pipeline) Inputs(job string) []string {
	panic("not implemented")
}

// Ready returns the unfinished jobs whose inputs have all finished, sorted by name.
func (p *Pipeline) Ready() []string {
	panic("not implemented")
}

// Finish marks a ready job finished.
func (p *Pipeline) Finish(job string) bool {
	panic("not implemented")
}
