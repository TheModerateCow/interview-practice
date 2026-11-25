"""An example to copy. Run your tests with the My tests button."""

from jobqueue import JobQueue


def test_enqueue_then_lease_then_ack():
    q = JobQueue()
    job_id = q.enqueue("thumbnails", "photo-7781", 1000)
    lease = q.lease("thumbnails", 1001)
    assert lease.job_id == job_id
    assert lease.until == 1031  # the default lease is 30 seconds
    q.ack(job_id, lease.token, 1010)
    assert q.job(job_id) is None  # completed jobs are dropped
    assert q.lease("thumbnails", 1011) is None
