package jobqueue

import "testing"

// An example to copy. Run your tests with the My tests button.
func TestExampleEnqueueThenLeaseThenAck(t *testing.T) {
	q := New()
	id, _ := q.Enqueue("thumbnails", "photo-7781", 1000, EnqueueOptions{})
	l, err := q.Lease("thumbnails", 1001)
	if err != nil || l == nil || l.JobID != id || l.Until != 1031 { // the default lease is 30 seconds
		t.Fatalf("Lease: got %+v, %v; want %s until 1031", l, err, id)
	}
	if err := q.Ack(id, l.Token, 1010); err != nil {
		t.Fatal(err)
	}
	if _, ok := q.Job(id); ok { // completed jobs are dropped
		t.Fatal("job still live after ack")
	}
	if l, _ := q.Lease("thumbnails", 1011); l != nil {
		t.Fatalf("queue should be empty, got %+v", l)
	}
}
