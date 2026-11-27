class Pipeline:
    def __init__(self):
        raise NotImplementedError

    def add_job(self, job: str, minutes: int) -> bool:
        raise NotImplementedError

    def set_consumer(self, job: str, consumer: str) -> bool:
        raise NotImplementedError

    def inputs(self, job: str) -> list[str]:
        raise NotImplementedError

    def ready(self) -> list[str]:
        raise NotImplementedError

    def finish(self, job: str) -> bool:
        raise NotImplementedError
