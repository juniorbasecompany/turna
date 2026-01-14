import os


def redis_dsn() -> str:
    return os.environ.get("REDIS_URL", "redis://localhost:6379/0")


class WorkerSettings:
    # Arq procura estes atributos na classe de settings
    from arq.connections import RedisSettings

    from app.worker.job import ping_job

    redis_settings = RedisSettings.from_dsn(redis_dsn())
    functions = [ping_job]

    @staticmethod
    def redis_dsn() -> str:
        # Mantém compatibilidade com o uso na API (enqueue)
        return redis_dsn()
