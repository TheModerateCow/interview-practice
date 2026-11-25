// An example to copy. Run your tests with the My tests button: every static void method whose
// name starts with "test" runs; use Expect.eq, Expect.isTrue and Expect.raises to check things.
public class ExampleTest {
    static void testEnqueueThenLeaseThenAck() {
        JobQueue q = new JobQueue();
        String id = q.enqueue("thumbnails", "photo-7781", 1000);
        JobQueue.Lease lease = q.lease("thumbnails", 1001);
        Expect.eq(id, lease.jobId());
        Expect.eq(1031L, lease.until()); // the default lease is 30 seconds
        q.ack(id, lease.token(), 1010);
        Expect.eq(null, q.job(id));       // completed jobs are dropped
        Expect.eq(null, q.lease("thumbnails", 1011));
    }
}
