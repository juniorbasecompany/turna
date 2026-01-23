import os


def redis_dsn() -> str:
    return os.environ.get("REDIS_URL", "redis://localhost:6379/0")


class WorkerSettings:
    # Arq procura estes atributos na classe de settings
    from arq.connections import RedisSettings
    from arq.cron import cron

    from app.worker.job import extract_demand_job, generate_schedule_job, generate_thumbnail_job, ping_job, reconcile_pending_orphans

    redis_settings = RedisSettings.from_dsn(redis_dsn())
    functions = [ping_job, extract_demand_job, generate_schedule_job, generate_thumbnail_job]
    cron_jobs = [
        cron(reconcile_pending_orphans, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),
    ]

    @staticmethod
    def redis_dsn() -> str:
        # Mantém compatibilidade com o uso na API (enqueue)
        return redis_dsn()
