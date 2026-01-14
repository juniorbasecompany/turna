import os

class WorkerSettings:
    @staticmethod
    def redis_dsn() -> str:
        return os.environ.get("REDIS_URL", "redis://localhost:6379/0")
