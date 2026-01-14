import asyncio
from arq import create_pool
from arq.connections import RedisSettings

from app.workers.worker_settings import WorkerSettings

async def main() -> None:
    redis = await create_pool(RedisSettings.from_dsn(WorkerSettings.redis_dsn()))
    # Fica executando jobs. Em dev, este processo roda como service "worker".
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
